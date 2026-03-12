from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from parser import parse_message
from database import add_price, get_price, add_alert, get_active_alerts, mark_alert_triggered
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'  # Your sandbox number
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------- HDX Dataset Integration ----------
FOOD_PRICES_DF = None
MARKETS_DF = None

def load_hdx_data():
    global FOOD_PRICES_DF, MARKETS_DF
    try:
        base_dir = os.path.dirname(__file__)
        food_path = os.path.join(base_dir, 'food_prices.csv')
        markets_path = os.path.join(base_dir, 'markets.csv')
        
        FOOD_PRICES_DF = pd.read_csv(food_path)
        MARKETS_DF = pd.read_csv(markets_path)
        
        print(f"Loaded {len(FOOD_PRICES_DF)} food price records")
        print(f"Loaded {len(MARKETS_DF)} market records")
    except Exception as e:
        print(f"Error loading HDX datasets: {e}")

def get_hdx_price(commodity, location, max_age_days=90):
    """Return HDX price only if recent, with age info."""
    print(f"🔍 get_hdx_price called with commodity='{commodity}', location='{location}'")
    
    if FOOD_PRICES_DF is None or MARKETS_DF is None:
        print("📦 DataFrames are None, loading...")
        load_hdx_data()
        if FOOD_PRICES_DF is None or MARKETS_DF is None:
            print("❌ Failed to load data")
            return None
    
    commodity = commodity.lower()
    location = location.lower()
    print(f"🔤 Lowercased: commodity='{commodity}', location='{location}'")
    
    # Find markets matching the location
    matched_markets = MARKETS_DF[
        (MARKETS_DF['market'].str.lower().str.contains(location, na=False)) |
        (MARKETS_DF['admin1'].str.lower().str.contains(location, na=False)) |
        (MARKETS_DF['admin2'].str.lower().str.contains(location, na=False))
    ]
    print(f"🏪 Found {len(matched_markets)} markets matching location")
    if matched_markets.empty:
        print("❌ No markets found")
        return None
    
    market_ids = matched_markets['market_id'].tolist()
    print(f"🆔 Market IDs: {market_ids[:5]}... (total {len(market_ids)})")
    
    # Filter food prices by those market_ids and commodity
    matches = FOOD_PRICES_DF[
        (FOOD_PRICES_DF['market_id'].isin(market_ids)) &
        (FOOD_PRICES_DF['commodity'].str.lower().str.contains(commodity, na=False))
    ]
    print(f"📊 Found {len(matches)} total price entries")
    if matches.empty:
        print("❌ No price matches")
        return None
    
    # Convert date and filter recent
    matches = matches.copy()
    matches['date'] = pd.to_datetime(matches['date'])
    cutoff = datetime.now() - timedelta(days=max_age_days)
    recent = matches[matches['date'] >= cutoff]
    print(f"📅 Found {len(recent)} entries from last {max_age_days} days")
    
    if recent.empty:
        print("⚠️ No recent data – falling back to user reports")
        return None
    
    # Get most recent from filtered set
    latest = recent.sort_values('date', ascending=False).iloc[0]
    age_days = (datetime.now() - latest['date']).days
    print(f"✅ Most recent: date={latest['date']}, price={latest['price']}, market={latest['market']}, age={age_days} days")
    
    return {
        "price": latest['price'],
        "source": "HDX / WFP",
        "date": latest['date'].strftime("%Y-%m-%d"),
        "market": latest['market'],
        "age_days": age_days
    }

# ---------- Alert Functions ----------
def send_whatsapp(to, body):
    """Send a WhatsApp message using Twilio"""
    try:
        message = client.messages.create(
            body=body,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f'whatsapp:{to}'
        )
        print(f"Message sent to {to}: {message.sid}")
        return True
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def check_alerts_for_price(price_entry):
    """Check if this new price triggers any active alerts"""
    alerts = get_active_alerts()
    for alert in alerts:
        if (alert['commodity'] == price_entry['commodity'] and
            alert['location'] == price_entry['location']):
            
            condition_met = False
            if alert['condition'] == 'below' and price_entry['price'] < alert['threshold']:
                condition_met = True
            elif alert['condition'] == 'above' and price_entry['price'] > alert['threshold']:
                condition_met = True
            
            if condition_met:
                body = (f"🔔 Alert! {price_entry['commodity'].title()} in {price_entry['location'].title()} "
                        f"is now ₦{price_entry['price']} ({alert['condition']} ₦{alert['threshold']}).")
                send_whatsapp(alert['phone'], body)
                mark_alert_triggered(alert)

# ---------- Webhook ----------
@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').lower().strip()
    sender = request.form.get('From', '')

    parsed = parse_message(incoming_msg)
    resp = MessagingResponse()
    msg = resp.message()

    if parsed['intent'] == 'price_inquiry':
        # First try HDX official data
        hdx_price = get_hdx_price(parsed['commodity'], parsed['location'])
        if hdx_price:
            reply = f"💰 {parsed['commodity'].title()} in {parsed['location'].title()}: ₦{hdx_price['price']:,}\n"
            reply += f"Source: {hdx_price['source']}\n"
            reply += f"Date: {hdx_price['date']}"
            if hdx_price['age_days'] > 30:
                reply += f"\n⚠️ This data is {hdx_price['age_days']} days old. To report a current price, use:\nupdate [item] [price] [location]"
            else:
                reply += f"\n📢 Prices from WFP data. To report a different price, use: update [item] [price] [location]"
        else:
            # Fallback to user-reported data
            result = get_price(parsed['commodity'], parsed['location'])
            if result:
                reply = f"💰 {parsed['commodity'].title()} in {parsed['location'].title()}: ₦{result['price']:,}\n"
                reply += f"Reported by user on: {result['reported_at']}\n\n"
                reply += "To update: update [item] [price] [location]"
            else:
                reply = f"❌ No price found for {parsed['commodity']} in {parsed['location']}.\n\n"
                reply += "Be the first to report it: update [item] [price] [location]"

    elif parsed['intent'] == 'price_update':
        phone = sender.replace('whatsapp:', '')
        new_price = add_price(
            parsed['commodity'],
            parsed['location'],
            parsed['price'],
            phone
        )
        check_alerts_for_price(new_price)
        reply = f"✅ Updated! {parsed['commodity'].title()} in {parsed['location'].title()} = ₦{int(parsed['price']):,}\nThanks for contributing! 🙏"

    elif parsed['intent'] == 'set_alert':
        phone = sender.replace('whatsapp:', '')
        add_alert(
            parsed['commodity'],
            parsed['location'],
            parsed['condition'],
            parsed['threshold'],
            phone
        )
        reply = (f"✅ Alert set! I'll notify you when {parsed['commodity'].title()} "
                 f"in {parsed['location'].title()} goes {parsed['condition']} ₦{parsed['threshold']}.")

    elif incoming_msg.startswith("privacy"):
        reply = ("🔐 *Privacy Policy*\n\n"
                 "We store your phone number and the prices you submit to provide alerts and improve our service. "
                 "Your data is never shared with third parties. For questions, contact support.")

    elif "hello" in incoming_msg or "hi" in incoming_msg:
        reply = "👋 Welcome to Market Price Bot!\n\n"
        reply += "📊 **To check a price**: tomato price mile 12\n"
        reply += "📝 **To update a price**: update tomato 500 mile 12\n"
        reply += "🔔 **To set a price alert**: alert me when tomato in mile 12 below 450\n\n"
        reply += "🔐 By using this bot, you agree we store your phone number and updates for alerts. We never share your data."

    else:
        reply = "🤔 Not sure what you mean.\n\nTry: 'tomato price mile 12' or 'update tomato 500 mile 12' or 'alert me when tomato in mile 12 below 450'"

    msg.body(reply)
    return str(resp)

# Load HDX data when the app starts
load_hdx_data()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)