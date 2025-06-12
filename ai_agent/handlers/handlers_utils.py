"""Utility Functions for Handlers"""

import re
from datetime import datetime


from config import (
    estimate_token_count,
    MEETING_INFO_PATTERNS,
   
)


def convert_earth_date_to_star_trek(date_text: str) -> str:
    """
    Convert Earth dates in text to Star Trek era dates.
    Prior to June 2024: year + 404
    After June 2024: year + 430
    """
    # Pattern to match various date formats
    date_patterns = [
        r'\b(\d{4})\b',  # Just year
        r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',  # MM/DD/YYYY or MM-DD-YYYY
        r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b(\w+)\s+(\d{1,2}),?\s+(\d{4})\b',  # Month DD, YYYY
        r'\b(\d{1,2})\s+(\w+)\s+(\d{4})\b'  # DD Month YYYY
    ]
    
    def convert_year(year: int, month: int = 6, day: int = 1) -> int:
        """Convert a year based on the June 2024 cutoff"""
        cutoff_date = datetime(2024, 6, 1)
        date_to_check = datetime(year, month, day)
        
        if date_to_check < cutoff_date:
            return year + 404
        else:
            return year + 430
    
    converted_text = date_text
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, date_text, re.IGNORECASE)
        for match in matches:
            original = match.group(0)
            groups = match.groups()
            
            if len(groups) == 1:  # Just year
                year = int(groups[0])
                if 1900 <= year <= 2100:  # Reasonable year range
                    converted_year = convert_year(year)
                    converted_text = converted_text.replace(original, str(converted_year), 1)
            
            elif len(groups) == 3:  # Full date
                try:
                    if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                        # Numeric date
                        if len(groups[0]) == 4:  # YYYY/MM/DD
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # MM/DD/YYYY
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        # Text month format
                        if groups[0].isdigit():  # DD Month YYYY
                            day, month_name, year = int(groups[0]), groups[1], int(groups[2])
                        else:  # Month DD, YYYY
                            month_name, day, year = groups[0], int(groups[1]), int(groups[2])
                        
                        # Convert month name to number
                        month_names = {
                            'january': 1, 'february': 2, 'march': 3, 'april': 4,
                            'may': 5, 'june': 6, 'july': 7, 'august': 8,
                            'september': 9, 'october': 10, 'november': 11, 'december': 12,
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        month = month_names.get(month_name.lower(), 6)  # Default to June if unknown
                    
                    if 1900 <= year <= 2100:  # Reasonable year range
                        converted_year = convert_year(year, month, day)
                        # Replace the year in the original date
                        new_date = original.replace(str(year), str(converted_year))
                        converted_text = converted_text.replace(original, new_date, 1)
                
                except (ValueError, KeyError):
                    continue  # Skip if date parsing fails
    
    return converted_text


def chunk_prompt_for_tokens(prompt: str, max_tokens: int = 7192) -> list:
    """
    Break large prompts into manageable chunks that fit within token limits.
    Returns a list of prompt chunks.
    """
    estimated_tokens = estimate_token_count(prompt)
    
    if estimated_tokens <= max_tokens:
        return [prompt]
    
    # Split prompt into sections
    sections = prompt.split('\n\n')
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for section in sections:
        section_tokens = estimate_token_count(section)
        
        if current_tokens + section_tokens <= max_tokens:
            if current_chunk:
                current_chunk += '\n\n' + section
            else:
                current_chunk = section
            current_tokens += section_tokens
        else:
            # Finish current chunk
            if current_chunk:
                chunks.append(current_chunk)
            
            # Start new chunk
            if section_tokens <= max_tokens:
                current_chunk = section
                current_tokens = section_tokens
            else:
                # Section too large, split it further
                words = section.split()
                temp_section = ""
                for word in words:
                    test_section = temp_section + ' ' + word if temp_section else word
                    if estimate_token_count(test_section) <= max_tokens:
                        temp_section = test_section
                    else:
                        if temp_section:
                            chunks.append(temp_section)
                        temp_section = word
                
                if temp_section:
                    current_chunk = temp_section
                    current_tokens = estimate_token_count(temp_section)
    
   
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks



def filter_meeting_info(text: str) -> str:
    """Remove meeting schedule information from responses"""
    filtered_text = text
    for pattern in MEETING_INFO_PATTERNS:
        filtered_text = re.sub(pattern, "", filtered_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up any double newlines or spaces created by the filtering
    filtered_text = re.sub(r'\n\s*\n', '\n\n', filtered_text)
    filtered_text = re.sub(r' +', ' ', filtered_text)
    return filtered_text.strip()


