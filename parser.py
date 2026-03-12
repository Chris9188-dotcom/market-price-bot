import re

def parse_message(text):
    text = text.lower().strip()
    
    # Price inquiry: "tomato price mile 12" or "price tomato mile 12"
    price_patterns = [
        r'(\w+)\s+price\s+(.+)',      # tomato price mile 12
        r'price\s+(\w+)\s+(.+)',      # price tomato mile 12
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, text)
        if match:
            return {
                'intent': 'price_inquiry',
                'commodity': match.group(1),
                'location': match.group(2).strip()
            }
    
    # Price update: "update tomato 500 mile 12"
    update_pattern = r'update\s+(\w+)\s+(\d+)\s+(.+)'
    match = re.search(update_pattern, text)
    if match:
        return {
            'intent': 'price_update',
            'commodity': match.group(1),
            'price': match.group(2),
            'location': match.group(3).strip()
        }
    
    # Alert pattern: "alert me when tomato in mile 12 below 400"
    alert_pattern = r'(?:alert|notify)\s+me\s+(?:when|if)\s+(\w+)\s+in\s+(.+?)\s+(below|above|under|over)\s+(\d+)'
    match = re.search(alert_pattern, text)
    if match:
        commodity = match.group(1)
        location = match.group(2).strip()
        direction = match.group(3)
        threshold = match.group(4)
        condition = 'below' if direction in ['below', 'under'] else 'above'
        return {
            'intent': 'set_alert',
            'commodity': commodity,
            'location': location,
            'condition': condition,
            'threshold': threshold
        }
    
    # Multi‑market comparison: "compare rice price in sokoto, kano, lagos"
    compare_pattern = r'compare\s+(\w+)\s+price\s+in\s+(.+)'
    match = re.search(compare_pattern, text)
    if match:
        commodity = match.group(1)
        locations = [loc.strip() for loc in match.group(2).split(',')]
        return {
            'intent': 'multi_compare',
            'commodity': commodity,
            'locations': locations
        }
    
    # Price trend: "trend rice in sokoto last 30 days"
    # also "trend rice in sokoto last 6 weeks" or "last 3 months"
    trend_pattern = r'trend\s+(\w+)\s+in\s+(.+?)\s+last\s+(\d+)\s+(day|week|month)s?'
    match = re.search(trend_pattern, text)
    if match:
        commodity = match.group(1)
        location = match.group(2).strip()
        amount = int(match.group(3))
        unit = match.group(4)
        return {
            'intent': 'price_trend',
            'commodity': commodity,
            'location': location,
            'amount': amount,
            'unit': unit
        }
    
    return {'intent': 'unknown'}