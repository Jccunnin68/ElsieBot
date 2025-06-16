#!/usr/bin/env python3
"""
Test script for fresh import system
Validates clean schema and category-based classification
"""

import os
import sys
from datetime import datetime
from fresh_import import FreshImportController
from content_processor import ContentProcessor
from db_operations import DatabaseOperations


def test_content_classification():
    """Test content classification system"""
    print("🧪 Testing Content Classification System")
    print("=" * 50)
    
    processor = ContentProcessor()
    
    # Test cases for different content types
    test_cases = [
        # Ship logs
        ("Stardancer 2024/09/29 Mission Log", "Mission log content", ["Stardancer Log"]),
        ("Adagio 4/23/2022 Personal Log", "Personal log entry", ["Adagio Log"]),
        
        # Ship information
        ("USS Enterprise (NCC-1701)", "Constitution class starship", ["Ship Information"]),
        ("USS Voyager", "Intrepid class starship", ["Ship Information"]),
        
        # Characters
        ("Marcus Blaine", "Rank: Captain, Species: Human", ["Characters"]),
        ("Captain Kirk", "Starfleet captain", ["Characters"]),
        ("Dr. McCoy", "Chief Medical Officer", ["Characters"]),
        
        # Technology
        ("Warp Drive", "Faster than light propulsion", ["Technology"]),
        ("Transporter", "Matter to energy conversion", ["Technology"]),
        
        # Locations
        ("Deep Space 9", "Space station", ["Locations"]),
        ("Bajor System", "Star system", ["Locations"]),
        
        # General
        ("Starfleet Academy", "Training institution", ["General Information"]),
        ("Federation Charter", "Founding document", ["General Information"])
    ]
    
    all_passed = True
    
    for title, content, expected_categories in test_cases:
        try:
            result_categories = processor.classify_content(title, content)
            
            if result_categories == expected_categories:
                print(f"   ✅ {title} → {result_categories}")
            else:
                print(f"   ❌ {title} → Expected: {expected_categories}, Got: {result_categories}")
                all_passed = False
                
        except Exception as e:
            print(f"   ❌ {title} → Error: {e}")
            all_passed = False
    
    if all_passed:
        print("   🎉 All classification tests passed!")
    else:
        print("   ⚠️  Some classification tests failed!")
    
    return all_passed


def test_database_schema():
    """Test database schema and operations"""
    print("\n🧪 Testing Database Schema")
    print("=" * 50)
    
    try:
        db_ops = DatabaseOperations()
        
        # Test connection
        print("   🔗 Testing database connection...")
        db_ops.ensure_database_connection()
        print("   ✅ Database connection successful")
        
        # Test statistics
        print("   📊 Testing statistics query...")
        stats = db_ops.get_database_stats()
        
        if stats:
            wiki_stats = stats.get('wiki_stats', {})
            category_stats = stats.get('category_stats', [])
            
            print(f"   📄 Total pages: {wiki_stats.get('total_pages', 0)}")
            print(f"   📋 Categories found: {len(category_stats)}")
            
            if category_stats:
                print("   🏷️  Top categories:")
                for i, cat_stat in enumerate(category_stats[:3], 1):
                    print(f"      {i}. {cat_stat['category']}: {cat_stat['count']} pages")
            
            print("   ✅ Database schema test passed!")
            return True
        else:
            print("   ❌ Failed to get database statistics")
            return False
            
    except Exception as e:
        print(f"   ❌ Database schema test failed: {e}")
        return False


def test_fresh_import_limited():
    """Test fresh import with limited dataset"""
    print("\n🧪 Testing Fresh Import (Limited)")
    print("=" * 50)
    
    try:
        controller = FreshImportController()
        
        # Run test import
        print("   🚀 Running test import...")
        success = controller.run_fresh_import(test_mode=True)
        
        if success:
            print("   ✅ Fresh import test passed!")
            
            # Validate results
            print("   🔍 Validating import results...")
            db_ops = DatabaseOperations()
            stats = db_ops.get_database_stats()
            
            if stats:
                wiki_stats = stats.get('wiki_stats', {})
                total_pages = wiki_stats.get('total_pages', 0)
                pages_with_categories = wiki_stats.get('pages_with_categories', 0)
                
                print(f"   📊 Import validation:")
                print(f"      Total pages: {total_pages}")
                print(f"      Pages with categories: {pages_with_categories}")
                
                if pages_with_categories == total_pages and total_pages > 0:
                    print("   ✅ All imported pages have categories!")
                    return True
                else:
                    print("   ⚠️  Some pages missing categories")
                    return False
            else:
                print("   ❌ Could not validate import results")
                return False
        else:
            print("   ❌ Fresh import test failed!")
            return False
            
    except Exception as e:
        print(f"   ❌ Fresh import test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("🧪 FRESH IMPORT SYSTEM TESTS")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now()}")
    
    tests = [
        ("Content Classification", test_content_classification),
        ("Database Schema", test_database_schema),
        ("Fresh Import (Limited)", test_fresh_import_limited)
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
        print("🎉 ALL TESTS PASSED! Fresh import system is ready!")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False


def main():
    """Main test function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "classification":
            success = test_content_classification()
        elif command == "schema":
            success = test_database_schema()
        elif command == "import":
            success = test_fresh_import_limited()
        else:
            print("Available tests: classification, schema, import, or no argument for all tests")
            return
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 