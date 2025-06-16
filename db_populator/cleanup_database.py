#!/usr/bin/env python3
"""
Database Cleanup Script for Elsie
Removes split log entries and resets database for fresh import.
This script handles the one-time cleanup needed after removing content splitting logic.
"""

import os
import sys
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseCleanup:
    """Handles database cleanup operations for removing split entries"""
    
    def __init__(self):
        # Database configuration (same as db_operations.py)
        self.db_config = {
            'dbname': os.getenv('DB_NAME', 'elsiebrain'),
            'user': os.getenv('DB_USER', 'elsie'),
            'password': os.getenv('DB_PASSWORD', 'elsie123'),
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5433')
        }
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def get_database_stats(self) -> Dict:
        """Get current database statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Wiki pages stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_pages,
                            COUNT(CASE WHEN page_type = 'mission_log' THEN 1 END) as mission_logs,
                            COUNT(CASE WHEN page_type = 'ship_info' THEN 1 END) as ship_info,
                            COUNT(CASE WHEN page_type = 'personnel' THEN 1 END) as personnel,
                            COUNT(CASE WHEN page_type = 'general' THEN 1 END) as general,
                            COUNT(CASE WHEN page_type = 'location' THEN 1 END) as location,
                            COUNT(CASE WHEN page_type = 'technology' THEN 1 END) as technology,
                            COUNT(DISTINCT ship_name) as unique_ships,
                            AVG(LENGTH(raw_content)) as avg_content_length,
                            MAX(LENGTH(raw_content)) as max_content_length,
                            COUNT(CASE WHEN categories IS NOT NULL AND array_length(categories, 1) > 0 THEN 1 END) as pages_with_categories,
                            COUNT(CASE WHEN categories IS NULL OR array_length(categories, 1) IS NULL THEN 1 END) as pages_without_categories
                        FROM wiki_pages
                    """)
                    wiki_stats = dict(cur.fetchone())
                    
                    # Metadata stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_tracked_pages,
                            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_pages,
                            COUNT(CASE WHEN status = 'error' THEN 1 END) as error_pages
                        FROM page_metadata
                    """)
                    metadata_stats = dict(cur.fetchone())
                    
                    return {**wiki_stats, **metadata_stats}
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    def find_split_entries(self) -> List[Dict]:
        """Find all entries with (Part X/Y) patterns"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Find entries with part patterns
                    cur.execute("""
                        SELECT id, title, page_type, ship_name, log_date, 
                               LENGTH(raw_content) as content_length
                        FROM wiki_pages 
                        WHERE title ~ '\\(Part \\d+/\\d+\\)$'
                        ORDER BY title
                    """)
                    split_entries = [dict(row) for row in cur.fetchall()]
                    
                    logger.info(f"Found {len(split_entries)} split entries")
                    return split_entries
        except Exception as e:
            logger.error(f"Error finding split entries: {e}")
            return []
    
    def group_split_entries(self, split_entries: List[Dict]) -> Dict[str, List[Dict]]:
        """Group split entries by their base title"""
        groups = {}
        part_pattern = re.compile(r'(.+) \(Part \d+/\d+\)$')
        
        for entry in split_entries:
            match = part_pattern.match(entry['title'])
            if match:
                base_title = match.group(1)
                if base_title not in groups:
                    groups[base_title] = []
                groups[base_title].append(entry)
        
        # Sort each group by part number
        for base_title in groups:
            groups[base_title].sort(key=lambda x: self._extract_part_number(x['title']))
        
        return groups
    
    def _extract_part_number(self, title: str) -> int:
        """Extract part number from title like 'Title (Part 2/3)'"""
        match = re.search(r'\(Part (\d+)/\d+\)$', title)
        return int(match.group(1)) if match else 0
    
    def analyze_split_entries(self) -> None:
        """Analyze and report on split entries"""
        print("\n🔍 ANALYZING SPLIT ENTRIES")
        print("=" * 60)
        
        split_entries = self.find_split_entries()
        if not split_entries:
            print("✅ No split entries found in database")
            return
        
        groups = self.group_split_entries(split_entries)
        
        print(f"📊 Split Entry Analysis:")
        print(f"   Total split entries: {len(split_entries)}")
        print(f"   Unique base titles: {len(groups)}")
        
        # Show examples
        print(f"\n📝 Examples of split entries:")
        for i, (base_title, parts) in enumerate(list(groups.items())[:5]):
            print(f"   {i+1}. '{base_title}' - {len(parts)} parts")
            for part in parts[:3]:  # Show first 3 parts
                content_preview = f"({part['content_length']} chars)"
                print(f"      → {part['title']} {content_preview}")
            if len(parts) > 3:
                print(f"      → ... and {len(parts) - 3} more parts")
        
        if len(groups) > 5:
            print(f"   ... and {len(groups) - 5} more split entries")
        
        # Show page type distribution
        type_counts = {}
        for entry in split_entries:
            page_type = entry.get('page_type', 'unknown')
            type_counts[page_type] = type_counts.get(page_type, 0) + 1
        
        print(f"\n📋 Split entries by page type:")
        for page_type, count in sorted(type_counts.items()):
            print(f"   {page_type}: {count}")
    
    def remove_split_entries(self, confirm: bool = False) -> int:
        """Remove all split entries from the database"""
        if not confirm:
            print("\n⚠️  WARNING: This will permanently delete split entries!")
            print("⚠️  Run with --confirm to actually delete entries")
            return 0
        
        print("\n🗑️  REMOVING SPLIT ENTRIES")
        print("=" * 60)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Delete split entries from wiki_pages
                    cur.execute("""
                        DELETE FROM wiki_pages 
                        WHERE title ~ '\\(Part \\d+/\\d+\\)$'
                        RETURNING title
                    """)
                    deleted_pages = cur.fetchall()
                    
                    # Delete corresponding metadata entries
                    cur.execute("""
                        DELETE FROM page_metadata 
                        WHERE title ~ '\\(Part \\d+/\\d+\\)$'
                        RETURNING title
                    """)
                    deleted_metadata = cur.fetchall()
                    
                    conn.commit()
                    
                    print(f"✅ Deleted {len(deleted_pages)} split wiki pages")
                    print(f"✅ Deleted {len(deleted_metadata)} split metadata entries")
                    
                    return len(deleted_pages)
                    
        except Exception as e:
            logger.error(f"Error removing split entries: {e}")
            return 0
    
    def reset_database(self, confirm: bool = False) -> bool:
        """Full database reset - removes all wiki data"""
        if not confirm:
            print("\n⚠️  WARNING: This will DELETE ALL WIKI DATA!")
            print("⚠️  Run with --reset --confirm to actually reset database")
            return False
        
        print("\n🔄 RESETTING DATABASE")
        print("=" * 60)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Delete all wiki pages
                    cur.execute("DELETE FROM wiki_pages")
                    wiki_count = cur.rowcount
                    
                    # Delete all page metadata
                    cur.execute("DELETE FROM page_metadata")
                    metadata_count = cur.rowcount
                    
                    # Reset sequences
                    cur.execute("ALTER SEQUENCE wiki_pages_id_seq RESTART WITH 1")
                    cur.execute("ALTER SEQUENCE page_metadata_id_seq RESTART WITH 1")
                    
                    conn.commit()
                    
                    print(f"✅ Deleted {wiki_count} wiki pages")
                    print(f"✅ Deleted {metadata_count} metadata entries")
                    print(f"✅ Reset database sequences")
                    
                    return True
                    
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            return False
    
    def show_cleanup_stats(self) -> None:
        """Show database statistics"""
        print("\n📈 DATABASE STATISTICS")
        print("=" * 60)
        
        stats = self.get_database_stats()
        
        print(f"📊 Content Statistics:")
        print(f"   Total Pages: {stats.get('total_pages', 0):,}")
        
        # Add category coverage if available
        pages_with_categories = stats.get('pages_with_categories', 0)
        pages_without_categories = stats.get('pages_without_categories', 0)
        if pages_with_categories > 0 or pages_without_categories > 0:
            total_pages = stats.get('total_pages', 0)
            if total_pages > 0:
                coverage_percent = (pages_with_categories / total_pages) * 100
                print(f"   Pages with Categories: {pages_with_categories:,} ({coverage_percent:.1f}%)")
                print(f"   Pages without Categories: {pages_without_categories:,}")
        
        print(f"\n📋 Legacy Page Type Distribution:")
        print(f"   Mission Logs: {stats.get('mission_logs', 0):,}")
        print(f"   Ship Info: {stats.get('ship_info', 0):,}")
        print(f"   Personnel: {stats.get('personnel', 0):,}")
        print(f"   General: {stats.get('general', 0):,}")
        print(f"   Location: {stats.get('location', 0):,}")
        print(f"   Technology: {stats.get('technology', 0):,}")
        print(f"   Unique Ships: {stats.get('unique_ships', 0):,}")
        
        print(f"\n📋 Metadata Statistics:")
        print(f"   Tracked Pages: {stats.get('total_tracked_pages', 0):,}")
        print(f"   Active Pages: {stats.get('active_pages', 0):,}")
        print(f"   Error Pages: {stats.get('error_pages', 0):,}")
        
        if stats.get('avg_content_length'):
            print(f"\n📄 Content Size Statistics:")
            print(f"   Average Content Length: {stats.get('avg_content_length', 0):,.0f} chars")
            print(f"   Maximum Content Length: {stats.get('max_content_length', 0):,.0f} chars")


def main():
    """Main cleanup function"""
    print("🧹 Elsie Database Cleanup Tool")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print(f"  python {sys.argv[0]} --analyze              # Analyze split entries")
        print(f"  python {sys.argv[0]} --cleanup              # Show what would be deleted")
        print(f"  python {sys.argv[0]} --cleanup --confirm    # Actually delete split entries")
        print(f"  python {sys.argv[0]} --reset                # Show reset warning")
        print(f"  python {sys.argv[0]} --reset --confirm      # Actually reset database")
        print(f"  python {sys.argv[0]} --stats                # Show database statistics")
        return
    
    cleanup = DatabaseCleanup()
    
    # Parse arguments
    analyze = '--analyze' in sys.argv
    do_cleanup = '--cleanup' in sys.argv
    reset = '--reset' in sys.argv
    stats = '--stats' in sys.argv
    confirm = '--confirm' in sys.argv
    
    try:
        if analyze:
            cleanup.analyze_split_entries()
        
        if do_cleanup:
            removed_count = cleanup.remove_split_entries(confirm=confirm)
            if removed_count > 0:
                print(f"\n✅ Successfully removed {removed_count} split entries")
        
        if reset:
            success = cleanup.reset_database(confirm=confirm)
            if success:
                print(f"\n✅ Database reset completed successfully")
        
        if stats or not any([analyze, do_cleanup, reset]):
            cleanup.show_cleanup_stats()
        
        print(f"\n⏰ Finished at: {datetime.now()}")
        print("🎯 Cleanup operation completed!")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 