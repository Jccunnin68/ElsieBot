"""Date conversion and masking utilities"""

import re
from datetime import datetime

def convert_to_universe_date(date_str: str) -> str:
    """Convert real-world dates to in-universe Star Trek dates"""
    
    # Extract year, month, day from various date formats
    date_patterns = [
        r'(\d{4})/(\d{1,2})/(\d{1,2})',  # YYYY/MM/DD
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY  
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            parts = match.groups()
            
            # Determine if it's YYYY/MM/DD or MM/DD/YYYY format
            if len(parts[0]) == 4:  # First part is year
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            elif len(parts[2]) == 4:  # Third part is year
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                continue  # Invalid format
            
            # Apply conversion rules
            if year < 2024 or (year == 2024 and month < 6):
                # Until June 2024: add 404 years
                universe_year = year + 404
            else:
                # After June 2024: add 430 years
                universe_year = year + 430
            
            # Replace the date in the original string with the converted date
            original_date = match.group(0)
            converted_date = f"{universe_year}/{month:02d}/{day:02d}"
            return date_str.replace(original_date, converted_date)
    
    # If no date pattern found, return original
    return date_str

def mask_log_title_dates(title: str) -> str:
    """Mask dates in log titles to show universe dates"""
    return convert_to_universe_date(title) 