from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from parser import parse_message
from database import add_price, get_price, add_alert, get_active_alerts, mark_alert_triggered
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'  # Your sandbox number
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

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
                # Send WhatsApp notification
                body = (f"🔔 Alert! {price_entry['commodity'].title()} in {price_entry['location'].title()} "
                        f"is now ₦{price_entry['price']} ({alert['condition']} ₦{alert['threshold']}).")
                send_whatsapp(alert['phone'], body)
                mark_alert_triggered(alert)

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').lower().strip()
    sender = request.form.get('From', '')

    parsed = parse_message(incoming_msg)
    resp = MessagingResponse()
    msg = resp.message()

    if parsed['intent'] == 'price_inquiry':
        result = get_price(parsed['commodity'], parsed['location'])
        if result:
            reply = f"💰 {parsed['commodity'].title()} in {parsed['location'].title()}: ₦{result['price']:,}\n"
            reply += f"Reported: {result['reported_at']}\n\n"
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
        # Check if this new price triggers any alerts
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

    elif "hello" in incoming_msg or "hi" in incoming_msg:
        reply = "👋 Welcome to Market Price Bot!\n\n"
        reply += "📊 **To check a price**:\n"
        reply += "   tomato price mile 12\n"
        reply += "   or: price tomato mile 12\n\n"
        reply += "📝 **To update a price**:\n"
        reply += "   update tomato 500 mile 12\n\n"
        reply += "🔔 **To set a price alert**:\n"
        reply += "   alert me when tomato in mile 12 below 450"
    else:
        reply = "🤔 Not sure what you mean.\n\nTry: 'tomato price mile 12' or 'update tomato 500 mile 12' or 'alert me when tomato in mile 12 below 450'"

    msg.body(reply)
    return str(resp)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)