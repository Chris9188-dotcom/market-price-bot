import json
import os
from datetime import datetime

# ---------- Price Database ----------
PRICES_FILE = 'prices.json'

def init_prices_db():
    """Create prices.json if it doesn't exist"""
    if not os.path.exists(PRICES_FILE):
        with open(PRICES_FILE, 'w') as f:
            json.dump([], f)

def add_price(commodity, location, price, phone):
    """Add a new price report and return the entry"""
    init_prices_db()
    with open(PRICES_FILE, 'r') as f:
        prices = json.load(f)
    
    new_entry = {
        'commodity': commodity.lower(),
        'location': location.lower(),
        'price': int(price),
        'reported_by': phone,
        'reported_at': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'verified': False
    }
    prices.append(new_entry)
    
    with open(PRICES_FILE, 'w') as f:
        json.dump(prices, f, indent=2)
    
    return new_entry

def get_price(commodity, location):
    """Get the most recent price for a commodity at a location"""
    init_prices_db()
    with open(PRICES_FILE, 'r') as f:
        prices = json.load(f)
    
    matching = [p for p in prices if p['commodity'] == commodity.lower() and p['location'] == location.lower()]
    if matching:
        # Return most recent
        return sorted(matching, key=lambda x: x['reported_at'], reverse=True)[0]
    return None

# ---------- Alert Database ----------
ALERTS_FILE = 'alerts.json'

def init_alerts_db():
    """Create alerts.json if it doesn't exist"""
    if not os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, 'w') as f:
            json.dump([], f)

def add_alert(commodity, location, condition, threshold, phone):
    """Store a new price alert for a user"""
    init_alerts_db()
    with open(ALERTS_FILE, 'r') as f:
        alerts = json.load(f)
    
    new_alert = {
        'commodity': commodity.lower(),
        'location': location.lower(),
        'condition': condition,      # 'below' or 'above'
        'threshold': int(threshold),
        'phone': phone,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M"),
        'triggered': False           # becomes True once sent
    }
    alerts.append(new_alert)
    
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)
    
    return new_alert

def get_active_alerts():
    """Return all alerts that haven't been triggered yet"""
    init_alerts_db()
    with open(ALERTS_FILE, 'r') as f:
        alerts = json.load(f)
    return [a for a in alerts if not a.get('triggered', False)]

def mark_alert_triggered(alert):
    """Mark an alert as triggered so it won't fire again"""
    init_alerts_db()
    with open(ALERTS_FILE, 'r') as f:
        alerts = json.load(f)
    
    for a in alerts:
        if (a['commodity'] == alert['commodity'] and
            a['location'] == alert['location'] and
            a['phone'] == alert['phone'] and
            a['created_at'] == alert['created_at']):
            a['triggered'] = True
            break
    
    with open(ALERTS_FILE, 'w') as f:
        json.dump(alerts, f, indent=2)