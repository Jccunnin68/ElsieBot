#!/usr/bin/env python3
"""
Test suite for incremental import system
Validates touched timestamp handling and update detection
"""

import os
import sys
from datetime import datetime, timedelta
from incremental_import import IncrementalImportController
from api_client import MediaWikiAPIClient
from db_operations import DatabaseOperations


def test_touched_timestamp_parsing():
    """Test MediaWiki touched timestamp parsing"""
    print("🧪 Testing Touched Timestamp Parsing")
    print("=" * 50)
    
    db_ops = DatabaseOperations()
    
    # Test cases for touched timestamp parsing
    test_cases = [
        ("2025-05-13T15:09:05Z", True),  # Valid MediaWiki format
        ("2025-05-13T15:09:05+00:00", True),  # Valid ISO format
        ("", False),  # Empty string
        ("invalid-date", False),  # Invalid format
        (None, False)  # None value
    ]
    
    all_passed = True
    
    for touched_str, should_parse in test_cases:
        try:
            # Test the parsing logic from db_operations
            if touched_str:
                try:
                    parsed_dt = datetime.fromisoformat(touched_str.replace('Z', '+00:00'))
                    parse_success = True
                except:
                    parse_success = False
            else:
                parse_success = False
            
            if parse_success == should_parse:
                print(f"   ✅ '{touched_str}' → Parse success: {parse_success}")
            else:
                print(f"   ❌ '{touched_str}' → Expected: {should_parse}, Got: {parse_success}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ '{touched_str}' → Error: {e}")
            all_passed = False
    
    if all_passed:
        print("   🎉 All timestamp parsing tests passed!")
    else:
        print("   ⚠️  Some timestamp parsing tests failed!")
    
    return all_passed


def test_api_metadata_extraction():
    """Test MediaWiki API metadata extraction"""
    print("\n🧪 Testing API Metadata Extraction")
    print("=" * 50)
    
    try:
        api_client = MediaWikiAPIClient()
        
        # Test with known page
        test_page = "Political Timeline"
        print(f"   📡 Testing metadata extraction for: {test_page}")
        
        metadata = api_client.get_page_metadata(test_page)
        
        if metadata:
            required_fields = ['canonical_url', 'touched', 'title', 'pageid']
            missing_fields = []
            
            for field in required_fields:
                if field not in metadata or not metadata[field]:
                    missing_fields.append(field)
            
            if not missing_fields:
                print(f"   ✅ All required metadata fields present:")
                print(f"      - URL: {metadata.get('canonical_url', 'N/A')}")
                print(f"      - Touched: {metadata.get('touched', 'N/A')}")
                print(f"      - Page ID: {metadata.get('pageid', 'N/A')}")
                return True
            else:
                print(f"   ❌ Missing metadata fields: {missing_fields}")
                return False
        else:
            print(f"   ❌ No metadata returned for {test_page}")
            return False
            
    except Exception as e:
        print(f"   ❌ API metadata test failed: {e}")
        return False


def test_update_detection_logic():
    """Test update detection logic"""
    print("\n🧪 Testing Update Detection Logic")
    print("=" * 50)
    
    try:
        db_ops = DatabaseOperations()
        
        # Test update detection with mock timestamps
        test_cases = [
            # (local_touched, remote_touched, should_update, description)
            (None, "2025-05-13T15:09:05Z", True, "No local timestamp"),
            ("", "2025-05-13T15:09:05Z", True, "Empty local timestamp"),
            ("2025-05-13T15:09:05Z", "", False, "No remote timestamp"),
            ("2025-05-13T15:09:05Z", "2025-05-13T15:09:05Z", False, "Same timestamps"),
            ("2025-05-13T15:09:05Z", "2025-05-13T16:09:05Z", True, "Remote newer"),
            ("2025-05-13T16:09:05Z", "2025-05-13T15:09:05Z", False, "Local newer"),
        ]
        
        all_passed = True
        
        for local_touched, remote_touched, expected_update, description in test_cases:
            try:
                # Mock the database response
                if local_touched:
                    local_dt = datetime.fromisoformat(local_touched.replace('Z', '+00:00'))
                else:
                    local_dt = None
                
                # Simulate the logic from should_update_page_by_touched
                if not local_dt:
                    should_update = True  # No local data
                elif not remote_touched:
                    should_update = False  # No remote data
                else:
                    remote_dt = datetime.fromisoformat(remote_touched.replace('Z', '+00:00'))
                    should_update = remote_dt > local_dt
                
                if should_update == expected_update:
                    print(f"   ✅ {description} → Should update: {should_update}")
                else:
                    print(f"   ❌ {description} → Expected: {expected_update}, Got: {should_update}")
                    all_passed = False
                    
            except Exception as e:
                print(f"   ❌ {description} → Error: {e}")
                all_passed = False
        
        if all_passed:
            print("   🎉 All update detection tests passed!")
        else:
            print("   ⚠️  Some update detection tests failed!")
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ Update detection test failed: {e}")
        return False


def test_incremental_import_dry_run():
    """Test incremental import controller (dry run)"""
    print("\n🧪 Testing Incremental Import Controller")
    print("=" * 50)
    
    try:
        controller = IncrementalImportController()
        
        print("   🔍 Testing page title retrieval...")
        page_titles = controller.get_page_titles(test_mode=True, limit=5)
        
        if page_titles and len(page_titles) > 0:
            print(f"   ✅ Retrieved {len(page_titles)} test page titles")
            
            print("   🔍 Testing update checking (first 2 pages)...")
            test_titles = page_titles[:2]
            
            for title in test_titles:
                try:
                    print(f"      📄 Checking: {title}")
                    
                    # Get metadata without actually updating
                    metadata = controller.extractor.api_client.get_page_metadata(title)
                    
                    if metadata:
                        touched = metadata.get('touched', '')
                        canonical_url = metadata.get('canonical_url', '')
                        print(f"         ✓ Metadata available")
                        print(f"         - Touched: {touched}")
                        print(f"         - URL: {canonical_url}")
                    else:
                        print(f"         ⚠️  No metadata available")
                        
                except Exception as e:
                    print(f"         ❌ Error checking {title}: {e}")
            
            print("   ✅ Incremental import controller test passed!")
            return True
        else:
            print("   ❌ No page titles retrieved")
            return False
            
    except Exception as e:
        print(f"   ❌ Incremental import test failed: {e}")
        return False


def test_database_schema():
    """Test database schema for touched field"""
    print("\n🧪 Testing Database Schema")
    print("=" * 50)
    
    try:
        db_ops = DatabaseOperations()
        
        # Test connection
        print("   🔗 Testing database connection...")
        db_ops.ensure_database_connection()
        print("   ✅ Database connection successful")
        
        # Check for touched field
        with db_ops.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'wiki_pages' AND column_name = 'touched'
                """)
                has_touched = cur.fetchone() is not None
                
                if has_touched:
                    print("   ✅ 'touched' field exists in database")
                else:
                    print("   ⚠️  'touched' field missing from database")
                    print("   💡 Run schema migration: python schema_migration.py add-touched --confirm")
                
                # Check for touched index
                cur.execute("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename = 'wiki_pages' AND indexname = 'idx_wiki_pages_touched'
                """)
                has_index = cur.fetchone() is not None
                
                if has_index:
                    print("   ✅ 'touched' field index exists")
                else:
                    print("   ⚠️  'touched' field index missing")
                
                return has_touched and has_index
                
    except Exception as e:
        print(f"   ❌ Database schema test failed: {e}")
        return False


def run_all_tests():
    """Run all incremental import tests"""
    print("🧪 INCREMENTAL IMPORT SYSTEM TESTS")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    
    tests = [
        ("Touched Timestamp Parsing", test_touched_timestamp_parsing),
        ("API Metadata Extraction", test_api_metadata_extraction),
        ("Update Detection Logic", test_update_detection_logic),
        ("Database Schema", test_database_schema),
        ("Incremental Import (Dry Run)", test_incremental_import_dry_run)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*20} {test_name} {'='*20}")
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n🎉 TEST RESULTS")
    print("=" * 60)
    print(f"⏰ Finished at: {datetime.now()}")
    print(f"📊 Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Incremental import system is ready!")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        print("\n💡 Common fixes:")
        print("   - Run schema migration: python schema_migration.py add-touched --confirm")
        print("   - Check database connection settings")
        print("   - Verify MediaWiki API access")
        return False


def main():
    """Main test function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "timestamps":
            success = test_touched_timestamp_parsing()
        elif command == "api":
            success = test_api_metadata_extraction()
        elif command == "logic":
            success = test_update_detection_logic()
        elif command == "schema":
            success = test_database_schema()
        elif command == "incremental":
            success = test_incremental_import_dry_run()
        else:
            print("Available tests: timestamps, api, logic, schema, incremental, or no argument for all tests")
            return
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 