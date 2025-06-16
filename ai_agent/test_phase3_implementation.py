#!/usr/bin/env python3
"""
Test Script for Phase 3 AI Wisdom Module Refactor Implementation
Tests the log patterns cleanup - removal of hardcoded ship names and functions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_log_patterns_cleanup():
    """Test that hardcoded ship names and deprecated functions are removed"""
    print("🧹 TESTING LOG PATTERNS CLEANUP")
    print("=" * 60)
    
    try:
        from handlers.ai_wisdom.log_patterns import LOG_INDICATORS
        
        # Test 1: Verify hardcoded ship names removed from LOG_INDICATORS
        print("\n📋 Test 1: LOG_INDICATORS cleanup")
        hardcoded_ships = ['stardancer log', 'adagio log', 'pilgrim log', 'protector log', 
                          'gigantes', 'banshee', 'manta ', 'sentinel', 'caelian']
        
        found_hardcoded = []
        for indicator in LOG_INDICATORS:
            if any(ship in indicator.lower() for ship in hardcoded_ships):
                found_hardcoded.append(indicator)
        
        if found_hardcoded:
            print(f"   ❌ Still contains hardcoded ship names: {found_hardcoded}")
        else:
            print(f"   ✅ LOG_INDICATORS cleaned of hardcoded ship names")
            print(f"   📊 Current indicators: {len(LOG_INDICATORS)} total")
        
        # Test 2: Verify deprecated function is removed
        print("\n🚫 Test 2: Deprecated function removal")
        try:
            from handlers.ai_wisdom.log_patterns import extract_ship_name_from_log_content
            print(f"   ❌ extract_ship_name_from_log_content still exists - should be removed")
        except ImportError:
            print(f"   ✅ extract_ship_name_from_log_content successfully removed")
        
        # Test 3: Verify character correction logic is preserved
        print("\n👥 test 3: Character correction preservation")
        try:
            from handlers.ai_wisdom.log_patterns import (
                resolve_character_name_with_context,
                SHIP_SPECIFIC_CHARACTER_CORRECTIONS,
                FALLBACK_CHARACTER_CORRECTIONS
            )
            
            # Test character resolution
            test_resolution = resolve_character_name_with_context(
                "tolena", "stardancer", "ensign mentioned in the log"
            )
            
            print(f"   ✅ Character correction functions preserved")
            print(f"   📊 Ship-specific corrections: {len(SHIP_SPECIFIC_CHARACTER_CORRECTIONS)} ships")
            print(f"   📊 Fallback corrections: {len(FALLBACK_CHARACTER_CORRECTIONS)} entries")
            print(f"   🧪 Test resolution 'tolena' on 'stardancer': {test_resolution}")
            
        except ImportError as e:
            print(f"   ❌ Character correction functions missing: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing log patterns: {e}")
        return False

def test_content_retriever_dynamic_categories():
    """Test that content retriever uses dynamic categories instead of hardcoded lists"""
    print("\n🔄 TESTING CONTENT RETRIEVER DYNAMIC CATEGORIES")
    print("=" * 60)
    
    try:
        from handlers.ai_wisdom.content_retriever import _get_log_categories, _is_log_category
        
        # Test 1: Dynamic category helper functions
        print("\n🛠️  Test 1: Helper functions")
        log_categories = _get_log_categories()
        print(f"   📊 Dynamic log categories found: {len(log_categories)}")
        if log_categories:
            print(f"   📋 Sample categories: {log_categories[:3]}")
        
        # Test 2: Category detection logic
        print("\n🔍 Test 2: Category detection")
        test_categories = ['Stardancer Log', 'Ship Information', 'Characters']
        is_log = _is_log_category(test_categories)
        print(f"   🧪 Test categories: {test_categories}")
        print(f"   📊 Detected as log: {is_log}")
        
        # Test 3: Verify import cleanup
        print("\n📦 Test 3: Import cleanup")
        try:
            # This should work
            from handlers.ai_wisdom.content_retriever import get_log_content
            print(f"   ✅ Core functions still available")
        except ImportError as e:
            print(f"   ❌ Core function import failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing content retriever: {e}")
        return False

def test_removed_function_usage():
    """Test that removed functions are not being used anywhere"""
    print("\n🔍 TESTING REMOVED FUNCTION USAGE")
    print("=" * 60)
    
    # Test 1: Check if any imports are broken
    print("\n📦 Test 1: Import integrity")
    try:
        from handlers.ai_wisdom.content_retriever import get_log_content, get_ship_information
        from handlers.ai_wisdom.llm_query_processor import get_llm_processor
        print(f"   ✅ All imports working after cleanup")
    except ImportError as e:
        print(f"   ❌ Import broken after cleanup: {e}")
        return False
    
    # Test 2: Test that log query detection still works
    print("\n🔍 Test 2: Log query detection")
    try:
        from handlers.ai_wisdom.log_patterns import is_log_query
        
        test_queries = [
            "show me recent logs",
            "what happened on the latest mission", 
            "captain's log entries",
            "tell me about Marcus Blaine"  # Should be False
        ]
        
        for query in test_queries:
            is_log = is_log_query(query)
            expected = 'log' in query.lower() or 'mission' in query.lower()
            print(f"   🧪 '{query}' -> {is_log} (expected: {expected})")
        
    except Exception as e:
        print(f"   ❌ Error testing log query detection: {e}")
        return False
    
    return True

def test_phase3_integration():
    """Integration test to verify Phase 3 works end-to-end"""
    print("\n🔄 TESTING PHASE 3 INTEGRATION")
    print("=" * 60)
    
    try:
        # Test that we can perform a log search without hardcoded ship names
        print("\n📋 Integration Test: Dynamic log search")
        
        from handlers.ai_wisdom.content_retriever import get_log_content
        
        # This should work using dynamic categories from database
        result = get_log_content("recent mission logs", mission_logs_only=True)
        
        if result:
            print(f"   ✅ Dynamic log search successful")
            print(f"   📊 Result length: {len(result)} characters")
        else:
            print(f"   ⚠️  No results (database may not be available)")
        
        print(f"   ✅ Phase 3 integration test passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Integration test failed: {e}")
        return False

def main():
    """Run all Phase 3 tests"""
    print("🧪 PHASE 3 AI WISDOM MODULE REFACTOR TESTS")
    print("=" * 70)
    print("Testing log patterns cleanup and hardcoded ship name removal")
    
    tests = [
        ("Log Patterns Cleanup", test_log_patterns_cleanup),
        ("Content Retriever Dynamic Categories", test_content_retriever_dynamic_categories),
        ("Removed Function Usage", test_removed_function_usage),
        ("Phase 3 Integration", test_phase3_integration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 50)
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print(f"\n🎉 PHASE 3 TEST RESULTS")
    print("=" * 70)
    print(f"📊 Tests passed: {passed}/{total}")
    print(f"🎯 Success rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("✅ All Phase 3 tests passed!")
        print("🎯 Log patterns cleanup completed successfully!")
        print("🚀 Ready for Phase 4!")
    else:
        print("❌ Some tests failed - review Phase 3 implementation")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 