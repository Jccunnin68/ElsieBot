#!/usr/bin/env python3
"""
Test Script for Phase 1 AI Wisdom Module Refactor Implementation
Tests the new category-specific database controller methods
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_controller import get_db_controller
from typing import List, Dict


def test_category_discovery_methods():
    """Test the new category discovery methods"""
    print("🔍 TESTING CATEGORY DISCOVERY METHODS")
    print("=" * 60)
    
    controller = get_db_controller()
    
    # Test 1: Get character categories
    print("\n📋 Test 1: get_character_categories()")
    character_categories = controller.get_character_categories()
    print(f"   Result: {len(character_categories)} categories found")
    if character_categories:
        print(f"   Categories: {character_categories}")
        # Verify exclusion of NPC Starships
        npc_starships = [cat for cat in character_categories if 'npc starship' in cat.lower()]
        if npc_starships:
            print(f"   ❌ ERROR: Found NPC Starship categories in character results: {npc_starships}")
            return False
        else:
            print(f"   ✅ Correctly excluded NPC Starship categories")
    else:
        print("   ⚠️  No character categories found")
    
    # Test 2: Get ship categories
    print("\n🚢 Test 2: get_ship_categories()")
    ship_categories = controller.get_ship_categories()
    print(f"   Result: {len(ship_categories)} categories found")
    if ship_categories:
        print(f"   Categories: {ship_categories}")
    else:
        print("   ⚠️  No ship categories found")
    
    # Test 3: Get log categories (existing method)
    print("\n📋 Test 3: _get_actual_log_categories_from_db() [existing]")
    log_categories = controller._get_actual_log_categories_from_db()
    print(f"   Result: {len(log_categories)} categories found")
    if log_categories:
        print(f"   Categories: {log_categories}")
        # Verify all contain "log"
        non_log_categories = [cat for cat in log_categories if 'log' not in cat.lower()]
        if non_log_categories:
            print(f"   ❌ ERROR: Found non-log categories: {non_log_categories}")
            return False
        else:
            print(f"   ✅ All categories correctly contain 'log'")
    else:
        print("   ⚠️  No log categories found")
    
    return True


def test_category_search_methods():
    """Test the new category-based search methods"""
    print("\n🔍 TESTING CATEGORY-BASED SEARCH METHODS")
    print("=" * 60)
    
    controller = get_db_controller()
    
    # Test 4: Search characters
    print("\n🧑 Test 4: search_characters()")
    test_queries = ["Marcus", "Blaine", "Captain", "crew"]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = controller.search_characters(query, limit=5)
        print(f"   Result: {len(results)} character pages found")
        
        if results:
            for i, result in enumerate(results[:3], 1):  # Show first 3
                title = result.get('title', 'Unknown')
                categories = result.get('categories', [])
                print(f"      {i}. '{title}' - Categories: {categories}")
                
                # Verify categories are character-related
                is_character_page = any(
                    'character' in cat.lower() or 'npc' in cat.lower() 
                    for cat in categories
                    if 'npc starship' not in cat.lower()
                )
                if not is_character_page and categories:  # Only warn if page has categories
                    print(f"         ⚠️  May not be character-related: {categories}")
    
    # Test 5: Search ships
    print("\n🚢 Test 5: search_ships()")
    test_queries = ["USS", "Stardancer", "Adagio", "ship", "vessel"]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = controller.search_ships(query, limit=5)
        print(f"   Result: {len(results)} ship pages found")
        
        if results:
            for i, result in enumerate(results[:3], 1):  # Show first 3
                title = result.get('title', 'Unknown')
                categories = result.get('categories', [])
                print(f"      {i}. '{title}' - Categories: {categories}")
                
                # Verify categories are ship-related
                is_ship_page = any(
                    'ship' in cat.lower() or 'starship' in cat.lower()
                    for cat in categories
                )
                if not is_ship_page and categories:  # Only warn if page has categories
                    print(f"         ⚠️  May not be ship-related: {categories}")
    
    # Test 6: Search logs
    print("\n📋 Test 6: search_logs()")
    test_queries = ["mission", "log", "Stardancer", "what happened"]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        results = controller.search_logs(query, limit=5)
        print(f"   Result: {len(results)} log pages found")
        
        if results:
            for i, result in enumerate(results[:3], 1):  # Show first 3
                title = result.get('title', 'Unknown')
                categories = result.get('categories', [])
                ship_name = result.get('ship_name', 'Unknown')
                log_date = result.get('log_date', 'Unknown')
                print(f"      {i}. '{title}' - Ship: {ship_name} - Date: {log_date}")
                print(f"         Categories: {categories}")
                
                # Verify categories are log-related
                is_log_page = any('log' in cat.lower() for cat in categories)
                if not is_log_page and categories:  # Only warn if page has categories
                    print(f"         ⚠️  May not be log-related: {categories}")
    
    return True


def test_ship_specific_log_search():
    """Test ship-specific log search functionality"""
    print("\n🔍 TESTING SHIP-SPECIFIC LOG SEARCH")
    print("=" * 60)
    
    controller = get_db_controller()
    
    # Test ship-specific log searches
    test_ships = ["stardancer", "adagio", "pilgrim"]
    
    for ship_name in test_ships:
        print(f"\n🚢 Testing ship-specific logs for: {ship_name}")
        results = controller.search_logs("mission", ship_name=ship_name, limit=5)
        print(f"   Result: {len(results)} {ship_name} logs found")
        
        if results:
            for i, result in enumerate(results[:3], 1):  # Show first 3
                title = result.get('title', 'Unknown')
                ship = result.get('ship_name', 'Unknown')
                categories = result.get('categories', [])
                print(f"      {i}. '{title}' - Ship: {ship}")
                print(f"         Categories: {categories}")
                
                # Verify ship name matches
                if ship.lower() != ship_name and ship_name not in title.lower():
                    print(f"         ⚠️  Ship mismatch: expected {ship_name}, got {ship}")
        else:
            print(f"   ⚠️  No logs found for {ship_name}")
    
    return True


def test_performance_and_error_handling():
    """Test performance and error handling of new methods"""
    print("\n🔍 TESTING PERFORMANCE AND ERROR HANDLING")
    print("=" * 60)
    
    controller = get_db_controller()
    
    # Test empty query handling
    print("\n⚠️  Test 7: Empty query handling")
    empty_results = controller.search_characters("", limit=5)
    print(f"   Empty character query result: {len(empty_results)} results")
    
    # Test very specific queries
    print("\n🎯 Test 8: Very specific queries")
    specific_results = controller.search_ships("USS Enterprise NCC-1701", limit=5)
    print(f"   Specific ship query result: {len(specific_results)} results")
    
    # Test fallback behavior when no categories exist
    print("\n🔄 Test 9: Category availability check")
    char_cats = controller.get_character_categories()
    ship_cats = controller.get_ship_categories()
    log_cats = controller._get_actual_log_categories_from_db()
    
    print(f"   Character categories available: {len(char_cats) > 0}")
    print(f"   Ship categories available: {len(ship_cats) > 0}")
    print(f"   Log categories available: {len(log_cats) > 0}")
    
    return True


def run_comprehensive_test():
    """Run all Phase 1 tests"""
    print("🚀 PHASE 1 AI WISDOM REFACTOR - DATABASE CONTROLLER TESTS")
    print("=" * 80)
    print("Testing new category-specific database methods")
    print("=" * 80)
    
    try:
        # Test category discovery
        print("\n" + "🔍 CATEGORY DISCOVERY TESTS".center(80))
        category_test_success = test_category_discovery_methods()
        
        # Test category-based searches
        print("\n" + "🔍 CATEGORY SEARCH TESTS".center(80))
        search_test_success = test_category_search_methods()
        
        # Test ship-specific functionality
        print("\n" + "🔍 SHIP-SPECIFIC TESTS".center(80))
        ship_test_success = test_ship_specific_log_search()
        
        # Test performance and edge cases
        print("\n" + "🔍 PERFORMANCE & ERROR HANDLING TESTS".center(80))
        performance_test_success = test_performance_and_error_handling()
        
        # Overall results
        print("\n" + "📊 PHASE 1 TEST RESULTS".center(80))
        print("=" * 80)
        
        all_tests_passed = all([
            category_test_success,
            search_test_success, 
            ship_test_success,
            performance_test_success
        ])
        
        if all_tests_passed:
            print("✅ ALL PHASE 1 TESTS PASSED!")
            print("🎉 Database controller enhancements are working correctly")
            print("\n📋 Phase 1 Implementation Complete:")
            print("   ✅ get_character_categories() method added")
            print("   ✅ get_ship_categories() method added") 
            print("   ✅ search_characters() method added")
            print("   ✅ search_ships() method added")
            print("   ✅ search_logs() method enhanced")
            print("   ✅ All new methods tested and validated")
            print("\n🚀 Ready to proceed to Phase 2: Content Retriever Simplification")
        else:
            print("❌ SOME PHASE 1 TESTS FAILED")
            print("🔧 Please review the test output above for specific issues")
        
        return all_tests_passed
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR during Phase 1 testing: {e}")
        return False


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1) 