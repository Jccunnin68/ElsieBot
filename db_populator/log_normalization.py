#!/usr/bin/env python3
"""
Mission Log Normalization Script
Detects and normalizes various mission log title patterns to standard format: YYYYMMDD Ship Log
"""

import psycopg2
import re
from datetime import datetime
from typing import Optional, Tuple, List

# Known ship names from the fleet
SHIP_NAMES = [
    'gigantes', 'sentinel', 'stardancer', 'banshee', 'protector', 'manta', 'pilgrim', 'adagio'
]

class LogNormalizer:
    def __init__(self):
        self.db_config = {
            'dbname': 'elsiebrain',
            'user': 'elsie',
            'password': 'elsie123',
            'host': 'localhost',
            'port': '5433'
        }
    
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def detect_log_patterns(self, title: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        Detect various mission log patterns and extract components.
        Returns: (is_log, normalized_date, ship_name, normalized_title)
        
        Patterns based on examples:
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
                    date_str = f"{year}{month}{day}"
                    normalized = f"{date_str} {ship_title} Log"
                    return True, date_str, ship, normalized
            
            # Pattern 2: Ship YYYY/MM/DD
            # Examples: "Gigantes 2024/04/01", "Protector 2024/05/24"
            pattern2 = rf'^{re.escape(ship)}\s+(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})$'
            match = re.search(pattern2, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    date_str = f"{year}{month}{day}"
                    normalized = f"{date_str} {ship_title} Log"
                    return True, date_str, ship, normalized
            
            # Pattern 3: Ship M/DD/YYYY or Ship MM/DD/YYYY
            # Examples: "Gigantes 4/25/2022", "Banshee 10/24/2022", "Pilgrim 1/10/2023"
            pattern3 = rf'^{re.escape(ship)}\s+(\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{4}})$'
            match = re.search(pattern3, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    date_str = f"{year}{month}{day}"
                    normalized = f"{date_str} {ship_title} Log"
                    return True, date_str, ship, normalized
            
            # Pattern 4: Ship M/DD/YYYY with trailing spaces
            # Examples: "Sentinel 1/17/2021   "
            pattern4 = rf'^{re.escape(ship)}\s+(\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{4}})\s*$'
            match = re.search(pattern4, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    date_str = f"{year}{month}{day}"
                    normalized = f"{date_str} {ship_title} Log"
                    return True, date_str, ship, normalized
            
            # Pattern 5: YYYY/M/D Ship (date first, no "Log")
            # Examples: "2022/3/2 Pilgrim"
            pattern5 = rf'^(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})\s+{re.escape(ship)}$'
            match = re.search(pattern5, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    date_str = f"{year}{month}{day}"
                    normalized = f"{date_str} {ship_title} Log"
                    return True, date_str, ship, normalized
            
            # Pattern 6: YYYY/MM/DD Ship Log
            # Examples: "2024/09/29 Adagio Log"
            pattern6 = rf'^(\d{{4}}[/\-]\d{{1,2}}[/\-]\d{{1,2}})\s+{re.escape(ship)}\s+log$'
            match = re.search(pattern6, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    date_str = f"{year}{month}{day}"
                    normalized = f"{date_str} {ship_title} Log"
                    return True, date_str, ship, normalized
            
            # Pattern 7: Ship YYYY/MM/DD (flexible spacing)
            # Examples: "Manta 2023/02/03", "Adagio 2023/04/22"
            pattern7 = rf'^{re.escape(ship)}\s+(\d{{4}}[/\-]\d{{2}}[/\-]\d{{2}})$'
            match = re.search(pattern7, title_lower)
            if match:
                date_part = match.group(1)
                year, month, day = parse_date_components(date_part)
                if year and month and day:
                    date_str = f"{year}{month}{day}"
                    normalized = f"{date_str} {ship_title} Log"
                    return True, date_str, ship, normalized
        
        # Fallback: General "log" detection with ship names (for entries that have "log" but don't match patterns)
        if 'log' in title_lower:
            for ship in SHIP_NAMES:
                if ship in title_lower:
                    # It's a log with a ship name, but no clear date pattern matched
                    # Mark it as a log but keep original title
                    return True, None, ship, title
        
        return False, None, None, None
    
    def analyze_current_logs(self):
        """Analyze current database to find potential mission logs"""
        print("🔍 Analyzing current database for potential mission logs...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all pages that might be logs
            cursor.execute("""
                SELECT title, page_type 
                FROM wiki_pages 
                WHERE page_type = 'general' 
                AND (
                    LOWER(title) LIKE '%log%' 
                    OR title ~ '[0-9]{6,8}'
                    OR LOWER(title) LIKE '%stardancer%'
                    OR LOWER(title) LIKE '%adagio%'
                )
                ORDER BY title
            """)
            
            candidates = cursor.fetchall()
            
            print(f"\n📊 Found {len(candidates)} potential log candidates:")
            
            detected_logs = []
            for title, current_type in candidates:
                is_log, date_str, ship, normalized = self.detect_log_patterns(title)
                if is_log:
                    detected_logs.append((title, date_str, ship, normalized))
                    status = "✓ DETECTED" if normalized != title else "✓ LOG (no date)"
                    print(f"  {status}: '{title}' -> '{normalized}' (ship: {ship})")
                else:
                    print(f"  ❌ NOT LOG: '{title}'")
            
            print(f"\n🎯 Summary: Found {len(detected_logs)} mission logs currently misclassified as 'general'")
            return detected_logs
    
    def normalize_logs(self, dry_run=True):
        """Normalize all detected mission logs in the database"""
        print(f"🚀 {'DRY RUN - ' if dry_run else ''}Normalizing mission logs...")
        
        detected_logs = self.analyze_current_logs()
        
        if not detected_logs:
            print("No logs to normalize.")
            return
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            updated_count = 0
            for original_title, date_str, ship, normalized_title in detected_logs:
                if not dry_run:
                    # Update the record
                    cursor.execute("""
                        UPDATE wiki_pages 
                        SET title = %s, page_type = 'mission_log', ship_name = %s, log_date = %s
                        WHERE title = %s
                    """, (normalized_title, ship, date_str, original_title))
                    
                    updated_count += 1
                    print(f"  ✅ UPDATED: '{original_title}' -> '{normalized_title}'")
                else:
                    print(f"  🔄 WOULD UPDATE: '{original_title}' -> '{normalized_title}' (ship: {ship}, date: {date_str})")
            
            if not dry_run:
                conn.commit()
                print(f"\n🎉 Successfully updated {updated_count} mission logs!")
            else:
                print(f"\n🔍 DRY RUN COMPLETE: Would update {len(detected_logs)} mission logs")
    
    def get_current_stats(self):
        """Get current database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT page_type, COUNT(*) as count 
                FROM wiki_pages 
                GROUP BY page_type 
                ORDER BY count DESC
            """)
            
            results = cursor.fetchall()
            
            print("📊 Current Page Type Distribution:")
            print("=" * 50)
            for page_type, count in results:
                print(f"{page_type}: {count}")
            
            total = sum(count for _, count in results)
            print(f"\nTotal pages: {total}")

def main():
    normalizer = LogNormalizer()
    
    print("🚀 Mission Log Normalization Tool")
    print("=" * 50)
    
    # Show current stats
    normalizer.get_current_stats()
    
    print("\n" + "=" * 50)
    
    # Run analysis and dry run
    normalizer.normalize_logs(dry_run=True)
    
    print("\n" + "=" * 50)
    print("To actually apply changes, modify the script to set dry_run=False")

if __name__ == "__main__":
    main() 