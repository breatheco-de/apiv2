"""
Utility functions for obfuscating sensitive data in webhook sample data.

This module provides functions to obfuscate PII (Personally Identifiable Information)
and other sensitive data before storing it in the database.
"""
import re
from typing import Any, Dict, List, Union


def obfuscate_sensitive_data(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively obfuscate sensitive information in sample data.
    
    Obfuscates:
    - Emails: user@example.com -> u***@example.com
    - Phone numbers: +1234567890 -> +1***7890
    - Names: John -> J***, Smith -> S***
    - Addresses: 123 Main St -> 123*** St
    - Coordinates: 25.7617 -> 25.7***, -80.1918 -> -80.1***
    - URLs with usernames: https://github.com/username -> https://github.com/user***
    - IDs: 12345 -> 1***5
    - GCLID: EAIaIQobChMI... -> EAIaIQobChMI***
    - Custom fields: Recursively processed
    
    Args:
        data: The data structure to obfuscate (dict, list, or primitive)
    
    Returns:
        The obfuscated data structure with the same shape as input
    """
    if isinstance(data, list):
        return [obfuscate_sensitive_data(item) for item in data]
    
    if not isinstance(data, dict):
        return data
    
    obfuscated = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Skip if value is None
        if value is None:
            obfuscated[key] = value
            continue
        
        # Obfuscate emails
        if 'email' in key_lower and isinstance(value, str) and '@' in value:
            parts = value.split('@')
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                if len(username) > 2:
                    obfuscated[key] = f"{username[:1]}***@{domain}"
                else:
                    obfuscated[key] = f"***@{domain}"
            else:
                obfuscated[key] = "***@example.com"
        
        # Obfuscate phone numbers
        elif 'phone' in key_lower and isinstance(value, str):
            # Remove non-digits for processing
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                obfuscated[key] = f"{value[:2]}***{value[-4:]}"
            else:
                obfuscated[key] = "***"
        
        # Obfuscate names (first_name, last_name, full_name, etc.)
        elif any(name_field in key_lower for name_field in ['first_name', 'last_name', 'full_name', 'name']) and isinstance(value, str):
            if len(value) > 2:
                obfuscated[key] = f"{value[0]}***"
            else:
                obfuscated[key] = "***"
        
        # Obfuscate addresses
        elif any(addr_field in key_lower for addr_field in ['address', 'street', 'location']) and isinstance(value, str):
            words = value.split()
            if words:
                obfuscated[key] = f"{words[0]}*** {' '.join(words[1:])}" if len(words) > 1 else f"{words[0]}***"
            else:
                obfuscated[key] = "***"
        
        # Obfuscate city, state, zip
        elif key_lower in ['city', 'state', 'zip_code', 'zip'] and isinstance(value, str):
            if len(value) > 2:
                obfuscated[key] = f"{value[0]}***"
            else:
                obfuscated[key] = "***"
        
        # Obfuscate coordinates (latitude, longitude)
        elif key_lower in ['latitude', 'longitude'] and isinstance(value, (int, float, str)):
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    obfuscated[key] = "***"
                    continue
            # Round to 1 decimal and add ***
            obfuscated[key] = f"{value:.1f}***"
        
        # Obfuscate URLs that might contain usernames (github_url, live_url)
        elif 'url' in key_lower and isinstance(value, str) and value.startswith('http'):
            # Check if URL contains username pattern (github.com/username, etc.)
            if '/github.com/' in value or '/gitlab.com/' in value or 'github.io' in value:
                parts = value.split('/')
                if len(parts) >= 4:  # https://github.com/username/...
                    parts[3] = f"{parts[3][:3]}***" if len(parts[3]) > 3 else "***"
                    obfuscated[key] = '/'.join(parts)
                else:
                    obfuscated[key] = value.replace(value.split('/')[-1], '***') if '/' in value else "https://example.com/***"
            else:
                # Generic URL obfuscation
                obfuscated[key] = re.sub(r'[a-zA-Z0-9]{4,}', lambda m: f"{m.group()[:3]}***" if len(m.group()) > 3 else "***", value)
        
        # Obfuscate IDs (but keep structure for reference)
        elif key_lower.endswith('_id') or key_lower == 'id':
            if isinstance(value, (int, str)):
                value_str = str(value)
                if len(value_str) > 3:
                    obfuscated[key] = f"{value_str[0]}***{value_str[-1]}"
                else:
                    obfuscated[key] = "***"
            else:
                obfuscated[key] = value
        
        # Obfuscate GCLID and similar tracking IDs
        elif 'gclid' in key_lower or 'tracking' in key_lower and isinstance(value, str):
            if len(value) > 10:
                obfuscated[key] = f"{value[:10]}***"
            else:
                obfuscated[key] = "***"
        
        # Obfuscate client comments
        elif 'comment' in key_lower and isinstance(value, str):
            if len(value) > 20:
                obfuscated[key] = f"{value[:10]}***{value[-10:]}"
            else:
                obfuscated[key] = "***"
        
        # Obfuscate username
        elif key_lower == 'username' and isinstance(value, str):
            if len(value) > 2:
                obfuscated[key] = f"{value[0]}***"
            else:
                obfuscated[key] = "***"
        
        # Recursively process nested dictionaries and lists
        elif isinstance(value, (dict, list)):
            obfuscated[key] = obfuscate_sensitive_data(value)
        
        # Keep other values as-is
        else:
            obfuscated[key] = value
    
    return obfuscated

