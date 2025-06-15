#!/usr/bin/env python3
"""
Enhanced Content Processor with improved mission log detection
"""

import re
from typing import Tuple, Optional

# Known ship names from the fleet
SHIP_NAMES = [
    'gigantes', 'sentinel', 'stardancer', 'banshee', 'protector', 'manta', 'pilgrim', 'adagio'
]

class EnhancedContentProcessor:
    """Enhanced version of ContentProcessor with better mission log detection"""
    
    def detect_mission_log_patterns(self, title: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Enhanced mission log detection supporting various patterns based on user examples:
        - 2019/4/22 Gigantes 
        - Gigantes 2024/04/01 
        - Gigantes 4/25/2022
        - Sentinel 1/17/2021   
        - 2024/09/21 Stardancer Log 
        - Banshee 10/24/2022 
        - Protector 11/4/2022 
        - Protector 2024/05/24 
        - Manta 2023/02/03 
        - 2022/3/2 Pilgrim 
        - Pilgrim 1/10/2023 
        - 2024/09/29 Adagio Log
        - Adagio 1/22/2022 
        - Adagio 2023/04/22
        
        Returns: (is_mission_log, ship_name, normalized_date)
        """
        title_lower = title.lower().strip()
        
        # Helper function to parse various date formats
        def parse_date_components(date_part):
            """Parse date string and return (year, month, day) as strings"""
            # Remove any extra whitespace
            date_part = date_part.strip()
            
            # Handle YYYY/M/D or YYYY/MM/DD format
            if re.match(r'\d{4}[/\-]\d{1,2}[/\-]\d{1,2}', date_part):
                parts = re.split('[/\-]', date_part)
                return parts[0], parts[1].zfill(2), parts[2].zfill(2)
            
            # Handle M/D/YYYY or MM/DD/YYYY format  
            elif re.match(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{4}', date_part):
                parts = re.split('[/\-]', date_part)
                return parts[2], parts[0].zfill(2), parts[1].zfill(2)
            
            # Handle YYYYMMDD format
            elif re.match(r'\d{8}', date_part):
                return date_part[:4], date_part[4:6], date_part[6:8]
            
            return None, None, None
        
        # Check each ship name
        for ship in SHIP_NAMES:
            ship_title = ship.title()  # Capitalize first letter
            
            # Pattern 1: YYYY/M/D Ship [Log] or YYYY/MM/DD Ship [Log]
            # Examples: "2019/4/22 Gigantes", "2024/09/21 Stardancer Log"
            pattern1 = rf'(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})\s+{re.escape(ship)}(?:\s+log)?'
            match = re.search(pattern1, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    normalized_date = f"{year}-{month}-{day}"
                    return True, ship, normalized_date
            
            # Pattern 2: Ship YYYY/MM/DD
            # Examples: "Gigantes 2024/04/01", "Protector 2024/05/24"
            pattern2 = rf'^{re.escape(ship)}\s+(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})$'
            match = re.search(pattern2, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    normalized_date = f"{year}-{month}-{day}"
                    return True, ship, normalized_date
            
            # Pattern 3: Ship M/DD/YYYY or Ship MM/DD/YYYY
            # Examples: "Gigantes 4/25/2022", "Banshee 10/24/2022", "Pilgrim 1/10/2023"
            pattern3 = rf'^{re.escape(ship)}\s+(\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{4}})$'
            match = re.search(pattern3, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    normalized_date = f"{year}-{month}-{day}"
                    return True, ship, normalized_date
            
            # Pattern 4: Ship M/DD/YYYY with trailing spaces
            # Examples: "Sentinel 1/17/2021   "
            pattern4 = rf'^{re.escape(ship)}\s+(\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{4}})\s*$'
            match = re.search(pattern4, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    normalized_date = f"{year}-{month}-{day}"
                    return True, ship, normalized_date
            
            # Pattern 5: YYYY/M/D Ship (date first, no "Log")
            # Examples: "2022/3/2 Pilgrim"
            pattern5 = rf'^(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})\s+{re.escape(ship)}$'
            match = re.search(pattern5, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    normalized_date = f"{year}-{month}-{day}"
                    return True, ship, normalized_date
            
            # Pattern 6: YYYY/MM/DD Ship Log
            # Examples: "2024/09/29 Adagio Log"
            pattern6 = rf'^(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})\s+{re.escape(ship)}\s+log$'
            match = re.search(pattern6, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    normalized_date = f"{year}-{month}-{day}"
                    return True, ship, normalized_date
            
            # Pattern 7: Ship YYYY/MM/DD (flexible spacing)
            # Examples: "Manta 2023/02/03", "Adagio 2023/04/22"
            pattern7 = rf'^{re.escape(ship)}\s+(\d{{4}}[/\-]\d{{2}}[/\-]\d{{2}})$'
            match = re.search(pattern7, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    normalized_date = f"{year}-{month}-{day}"
                    return True, ship, normalized_date
        
        # Fallback: General "log" detection with ship names (for entries that have "log" but don't match patterns)
        if 'log' in title_lower:
            for ship in SHIP_NAMES:
                if ship in title_lower:
                    # It's a log with a ship name, but no clear date pattern matched
                    # Mark it as a log but return None for date
                    return True, ship, None
        
        return False, None, None
    
    def classify_page_type_enhanced(self, title: str, content: str) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Enhanced page classification with improved mission log detection
        Returns: (page_type, ship_name, log_date)
        """
        title_lower = title.lower()
        content_lower = content.lower() if content else ""
        
        # Enhanced Mission Log Detection
        is_mission_log, ship_name, log_date = self.detect_mission_log_patterns(title)
        if is_mission_log:
            print(f"   🚢 Enhanced: Classified as mission_log: '{title}' -> ship: '{ship_name}', date: '{log_date}'")
            return "mission_log", ship_name, log_date
        
        # Check if it's a ship info page (USS patterns)
        ship_pattern = r'uss\s+(\w+)|(\w+)\s+\(ncc-\d+\)'
        if re.search(ship_pattern, title_lower):
            ship_name = self.extract_ship_name_from_title(title)
            print(f"   🚢 Classified as ship_info: '{title}' -> ship: '{ship_name}'")
            return "ship_info", ship_name, None
        
        # Character/Personnel detection (simplified)
        if self._detect_character_page(title, content_lower):
            print(f"   👤 Classified as personnel: '{title}'")
            return "personnel", None, None
        
        # Location detection
        if any(keyword in title_lower for keyword in ['system', 'planet', 'station', 'starbase']):
            print(f"   🌍 Classified as location: '{title}'")
            return "location", None, None
        
        # Technology detection
        if any(keyword in title_lower for keyword in ['class', 'drive', 'matrix', 'interface']) and 'system' not in title_lower:
            print(f"   🔧 Classified as technology: '{title}'")
            return "technology", None, None
        
        # Default to general
        print(f"   📄 Classified as general: '{title}'")
        return "general", None, None
    
    def extract_ship_name_from_title(self, title: str) -> Optional[str]:
        """Extract ship name from title"""
        title_lower = title.lower()
        
        # Check known ship names
        for ship in SHIP_NAMES:
            if ship in title_lower:
                return ship
        
        # Extract from USS patterns
        uss_pattern = r'uss\s+(\w+)'
        uss_match = re.search(uss_pattern, title_lower)
        if uss_match:
            return uss_match.group(1)
        
        return None
    
    def _detect_character_page(self, title: str, content_lower: str) -> bool:
        """Simplified character detection"""
        title_lower = title.lower()
        
        # Rank keywords
        rank_keywords = [
            'captain', 'commander', 'lieutenant', 'ensign', 'admiral', 
            'doctor', 'dr.', 'chief', 'sergeant', 'major', 'colonel'
        ]
        
        if any(keyword in title_lower for keyword in rank_keywords):
            return True
        
        # Name patterns (simplified)
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', title):  # First Last
            return True
        
        return False

# Test function
def test_log_detection():
    """Test the enhanced log detection"""
    processor = EnhancedContentProcessor()
    
    test_cases = [
        "2025/06/06 Stardancer Log",
        "2025/1/12 Stardancer log", 
        "Adagio 06232025",  # MMDDYYYY
        "20250623 Stardancer",  # YYYYMMDD Ship
        "Stardancer Log 20250623",  # Ship Log YYYYMMDD
        "062325 Adagio log",  # MMDDYY Ship log (typo example)
        "Stardancer Mission Brief",  # Should not match
        "Random Page Title",  # Should not match
    ]
    
    print("🧪 Testing Enhanced Log Detection:")
    print("=" * 50)
    
    for title in test_cases:
        is_log, ship, date = processor.detect_mission_log_patterns(title)
        if is_log:
            print(f"✅ '{title}' -> MISSION LOG (ship: {ship}, date: {date})")
        else:
            print(f"❌ '{title}' -> NOT A LOG")

if __name__ == "__main__":
    test_log_detection() 