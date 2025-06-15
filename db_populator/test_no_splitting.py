#!/usr/bin/env python3
"""
Test script to validate content splitting removal and classification accuracy.
Run this after implementing the migration to ensure everything works correctly.
"""

import os
import sys
from datetime import datetime
from db_operations import DatabaseOperations
from content_processor import ContentProcessor


def create_test_content(size_chars: int) -> str:
    """Create test content of specified size"""
    base_content = """
**Test Mission Log**

## Mission Summary
This is a test mission log entry designed to validate that content splitting
has been properly removed from the database populator. This content is
intentionally made very long to exceed the previous 25,000 character limit
that would have triggered content splitting.

## Mission Details
The mission involved extensive exploration of the Delta Quadrant, where
the crew encountered various alien species and navigated complex
diplomatic situations. The following sections detail the encounters:

"""
    
    # Repeat content to reach desired size
    repeated_section = """
### Encounter Section
During this phase of the mission, the crew engaged with local inhabitants
and conducted scientific surveys. The data collected will be invaluable
for future missions in this region. This section is repeated multiple
times to create test content of sufficient length.

"""
    
    content = base_content
    while len(content) < size_chars:
        content += repeated_section
    
    return content[:size_chars]


def test_classification():
    """Test page classification logic"""
    print("🔍 TESTING PAGE CLASSIFICATION")
    print("=" * 50)
    
    processor = ContentProcessor()
    
    test_cases = [
        # Mission logs
        ("2024/12/15 Stardancer Mission Log", "This is a mission log", "mission_log"),
        ("Adagio 2024/11/20 Log", "Mission details here", "mission_log"),
        ("12/25/2024 Pilgrim Log Entry", "Mission content", "mission_log"),
        
        # Ship info
        ("USS Stardancer", "Ship specifications and details", "ship_info"),
        ("USS Enterprise (NCC-1701)", "Constitution class starship", "ship_info"),
        ("Voyager (NCC-74656)", "Intrepid class vessel", "ship_info"),
        
        # Personnel
        ("Captain Marcus Blaine", "Starfleet officer biography", "personnel"),
        ("Commander Data", "Android officer serving on Enterprise", "personnel"),
        ("Dr. Julian Bashir", "Chief medical officer", "personnel"),
        ("Samwise Blake", "Engineering officer background", "personnel"),
        
        # General
        ("Star Trek Technology", "Overview of various technologies", "general"),
        ("Federation History", "Historical overview", "general"),
    ]
    
    passed = 0
    failed = 0
    
    for title, content, expected_type in test_cases:
        page_type, ship_name, log_date = processor.classify_page_type(title, content)
        
        if page_type == expected_type:
            print(f"✅ PASS: '{title}' → {page_type}")
            passed += 1
        else:
            print(f"❌ FAIL: '{title}' → Expected: {expected_type}, Got: {page_type}")
            failed += 1
    
    print(f"\n📊 Classification Test Results: {passed} passed, {failed} failed")
    return failed == 0


def test_no_splitting():
    """Test that content is not split regardless of size"""
    print("\n🧪 TESTING NO CONTENT SPLITTING")
    print("=" * 50)
    
    db_ops = DatabaseOperations()
    processor = ContentProcessor()
    
    # Test with various content sizes
    test_sizes = [1000, 10000, 30000, 50000, 100000]  # Characters
    
    for size in test_sizes:
        print(f"\n📏 Testing {size:,} character content...")
        
        # Create test content
        content = create_test_content(size)
        
        # Create test page data
        page_data = {
            'title': f'Test Page {size} chars',
            'raw_content': content,
            'url': f'https://test.com/page_{size}',
            'crawled_at': datetime.now()
        }
        
        try:
            # Save to database - should not split
            success = db_ops.save_page_to_database(page_data, processor)
            
            if success:
                # Verify only one entry was created
                with db_ops.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT COUNT(*) FROM wiki_pages 
                            WHERE title LIKE %s
                        """, (f'Test Page {size} chars%',))
                        count = cur.fetchone()[0]
                        
                        if count == 1:
                            print(f"✅ PASS: {size:,} chars → 1 database entry")
                        else:
                            print(f"❌ FAIL: {size:,} chars → {count} database entries")
                            return False
            else:
                print(f"❌ FAIL: Failed to save {size:,} char content")
                return False
                
        except Exception as e:
            print(f"❌ ERROR: {size:,} chars → {e}")
            return False
    
    print("\n✅ ALL SPLITTING TESTS PASSED - No content splitting detected")
    return True


def test_split_detection():
    """Test detection of existing split entries"""
    print("\n🔍 TESTING SPLIT ENTRY DETECTION")
    print("=" * 50)
    
    db_ops = DatabaseOperations()
    
    try:
        with db_ops.get_connection() as conn:
            with conn.cursor() as cur:
                # Check for any existing split entries
                cur.execute("""
                    SELECT title FROM wiki_pages 
                    WHERE title ~ '\\(Part \\d+/\\d+\\)$'
                    LIMIT 5
                """)
                split_entries = cur.fetchall()
                
                if split_entries:
                    print(f"⚠️  Found {len(split_entries)} split entries:")
                    for entry in split_entries:
                        print(f"   → {entry[0]}")
                    print("\n💡 Run cleanup script to remove these:")
                    print("   python cleanup_database.py --cleanup --confirm")
                    return False
                else:
                    print("✅ No split entries found in database")
                    return True
                    
    except Exception as e:
        print(f"❌ ERROR checking for split entries: {e}")
        return False


def test_database_stats():
    """Display database statistics"""
    print("\n📊 DATABASE STATISTICS")
    print("=" * 50)
    
    db_ops = DatabaseOperations()
    stats = db_ops.get_database_stats()
    
    print(f"Total Pages: {stats.get('total_pages', 0):,}")
    print(f"Mission Logs: {stats.get('mission_logs', 0):,}")
    print(f"Ship Info: {stats.get('ship_info', 0):,}")
    print(f"Personnel: {stats.get('personnel', 0):,}")
    print(f"General: {stats.get('general', 0):,}")
    print(f"Unique Ships: {stats.get('unique_ships', 0):,}")


def cleanup_test_data():
    """Remove test data created during testing"""
    print("\n🧹 CLEANING UP TEST DATA")
    print("=" * 50)
    
    db_ops = DatabaseOperations()
    
    try:
        with db_ops.get_connection() as conn:
            with conn.cursor() as cur:
                # Remove test pages
                cur.execute("""
                    DELETE FROM wiki_pages 
                    WHERE title LIKE 'Test Page % chars'
                """)
                deleted_count = cur.rowcount
                
                # Remove test metadata
                cur.execute("""
                    DELETE FROM page_metadata 
                    WHERE title LIKE 'Test Page % chars'
                """)
                
                conn.commit()
                
                print(f"✅ Cleaned up {deleted_count} test entries")
                
    except Exception as e:
        print(f"❌ Error cleaning up test data: {e}")


def main():
    """Run all tests"""
    print("🧪 DATABASE POPULATOR MIGRATION VALIDATION")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    
    all_passed = True
    
    try:
        # Test 1: Classification logic
        if not test_classification():
            all_passed = False
        
        # Test 2: No content splitting
        if not test_no_splitting():
            all_passed = False
        
        # Test 3: Check for existing split entries
        if not test_split_detection():
            all_passed = False
        
        # Test 4: Show database stats
        test_database_stats()
        
        # Cleanup test data
        cleanup_test_data()
        
        print(f"\n{'='*60}")
        if all_passed:
            print("🎉 ALL TESTS PASSED - Migration validation successful!")
            print("✅ Content splitting has been successfully removed")
            print("✅ Classification logic is working correctly")
            print("✅ Database is ready for production use")
        else:
            print("❌ SOME TESTS FAILED - Review issues above")
            print("⚠️  Migration may need additional work")
        
        print(f"⏰ Finished at: {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 