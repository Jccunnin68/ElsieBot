"""
Date Conversion Service - Pythonic Date Handling
================================================

This service handles Earth to Star Trek date conversions with proper
encapsulation and state management. Refactored from standalone functions
to a proper service class.
"""

import re
from datetime import datetime
from typing import Optional


class DateConversionService:
    """
    Service for converting Earth dates to Star Trek era dates.
    
    This service provides a clean API for date conversion functionality while maintaining
    proper encapsulation and configuration management.
    """
    
    # Date conversion constants
    PRE_CUTOFF_OFFSET = 404   # Prior to June 2024: year + 404
    POST_CUTOFF_OFFSET = 430  # After June 2024: year + 430
    CUTOFF_DATE = datetime(2024, 6, 1)
    
    # Date pattern definitions
    DATE_PATTERNS = [
        r'\b(\d{4})\b',  # Just year
        r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',  # MM/DD/YYYY or MM-DD-YYYY
        r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b(\w+)\s+(\d{1,2}),?\s+(\d{4})\b',  # Month DD, YYYY
        r'\b(\d{1,2})\s+(\w+)\s+(\d{4})\b'  # DD Month YYYY
    ]
    
    # Month name mapping
    MONTH_NAMES = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }

    def convert_earth_date_to_star_trek(self, date_text: str) -> str:
        """
        Convert Earth dates in text to Star Trek era dates.
        Prior to June 2024: year + 404
        After June 2024: year + 430
        
        Args:
            date_text: Text containing Earth dates to convert
            
        Returns:
            Text with Earth dates converted to Star Trek dates
        """
        converted_text = date_text
        
        for pattern in self.DATE_PATTERNS:
            matches = re.finditer(pattern, date_text, re.IGNORECASE)
            for match in matches:
                original = match.group(0)
                groups = match.groups()
                
                if len(groups) == 1:  # Just year
                    year = int(groups[0])
                    if self._is_valid_year(year):
                        converted_year = self._convert_year(year)
                        converted_text = converted_text.replace(original, str(converted_year), 1)
                
                elif len(groups) == 3:  # Full date
                    try:
                        year, month, day = self._parse_date_groups(groups)
                        if self._is_valid_year(year):
                            converted_year = self._convert_year(year, month, day)
                            # Replace the year in the original date
                            new_date = original.replace(str(year), str(converted_year))
                            converted_text = converted_text.replace(original, new_date, 1)
                    
                    except (ValueError, KeyError):
                        continue  # Skip if date parsing fails
        
        return converted_text
    
    def _convert_year(self, year: int, month: int = 6, day: int = 1) -> int:
        """
        Convert a year based on the June 2024 cutoff.
        
        Args:
            year: Year to convert
            month: Month (default: 6)
            day: Day (default: 1)
            
        Returns:
            Converted Star Trek year
        """
        try:
            date_to_check = datetime(year, month, day)
            
            if date_to_check < self.CUTOFF_DATE:
                return year + self.PRE_CUTOFF_OFFSET
            else:
                return year + self.POST_CUTOFF_OFFSET
        except ValueError:
            # Invalid date, use default conversion
            return year + self.PRE_CUTOFF_OFFSET
    
    def _parse_date_groups(self, groups: tuple) -> tuple:
        """
        Parse date groups from regex match into (year, month, day).
        
        Args:
            groups: Regex match groups
            
        Returns:
            Tuple of (year, month, day)
        """
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
            month = self.MONTH_NAMES.get(month_name.lower(), 6)  # Default to June if unknown
        
        return year, month, day
    
    def _is_valid_year(self, year: int) -> bool:
        """
        Check if a year is within a reasonable range for conversion.
        
        Args:
            year: Year to validate
            
        Returns:
            True if year is valid for conversion
        """
        return 1900 <= year <= 2100
    
    def get_star_trek_year_for_earth_year(self, earth_year: int, month: int = 6, day: int = 1) -> Optional[int]:
        """
        Get the Star Trek equivalent year for a given Earth year.
        
        Args:
            earth_year: Earth year to convert
            month: Month (default: 6)
            day: Day (default: 1)
            
        Returns:
            Star Trek year or None if invalid
        """
        if not self._is_valid_year(earth_year):
            return None
        
        return self._convert_year(earth_year, month, day)
    
    def is_pre_cutoff_date(self, year: int, month: int = 6, day: int = 1) -> bool:
        """
        Check if a date is before the June 2024 cutoff.
        
        Args:
            year: Year to check
            month: Month (default: 6)
            day: Day (default: 1)
            
        Returns:
            True if date is before cutoff
        """
        try:
            date_to_check = datetime(year, month, day)
            return date_to_check < self.CUTOFF_DATE
        except ValueError:
            return True  # Default to pre-cutoff for invalid dates 