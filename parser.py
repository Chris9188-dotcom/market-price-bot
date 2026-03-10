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
    # or "notify me if rice in ajah above 30000"
    alert_pattern = r'(?:alert|notify)\s+me\s+(?:when|if)\s+(\w+)\s+in\s+(.+?)\s+(below|above|under|over)\s+(\d+)'
    match = re.search(alert_pattern, text)
    if match:
        commodity = match.group(1)
        location = match.group(2).strip()
        direction = match.group(3)
        threshold = match.group(4)
        
        # Normalize direction
        if direction in ['below', 'under']:
            condition = 'below'
        else:
            condition = 'above'
        
        return {
            'intent': 'set_alert',
            'commodity': commodity,
            'location': location,
            'condition': condition,
            'threshold': threshold
        }
    
    return {'intent': 'unknown'}