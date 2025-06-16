#!/usr/bin/env python3
"""
Test Script for Phase 2 AI Wisdom Module Refactor Implementation
Tests the simplified content retriever functions using category-based searches
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from handlers.ai_wisdom.content_retriever import (
    get_log_content, get_ship_information, get_character_context, 
    get_relevant_wiki_context
)

def test_simplified_log_search():
    """Test the simplified get_log_content function"""
    print("🚀 TESTING SIMPLIFIED LOG SEARCH")
    print("=" * 60)
    
    test_queries = [
        "stardancer mission logs",
        "what happened on the latest mission",
        "show me recent logs",
        "captain's log entries"
    ]
    
    for query in test_queries:
        print(f"\n📋 Testing log query: '{query}'")
        try:
            result = get_log_content(query, mission_logs_only=False, is_roleplay=False)
            if result:
                print(f"   ✅ SUCCESS: Retrieved {len(result)} chars")
                print(f"   📝 Preview: {result[:100]}...")
            else:
                print(f"   ⚠️  No results for: {query}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_simplified_ship_search():
    """Test the simplified get_ship_information function"""
    print("\n🚢 TESTING SIMPLIFIED SHIP SEARCH")
    print("=" * 60)
    
    test_ships = [
        "Stardancer",
        "USS Adagio", 
        "Protector",
        "Enterprise"
    ]
    
    for ship in test_ships:
        print(f"\n📋 Testing ship query: '{ship}'")
        try:
            result = get_ship_information(ship)
            if result:
                print(f"   ✅ SUCCESS: Retrieved {len(result)} chars")
                print(f"   📝 Preview: {result[:100]}...")
            else:
                print(f"   ⚠️  No results for: {ship}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_new_character_search():
    """Test the new get_character_context function"""
    print("\n👤 TESTING NEW CHARACTER SEARCH")
    print("=" * 60)
    
    test_characters = [
        "Marcus Blaine",
        "Maeve Blaine",
        "Talia",
        "Spock"
    ]
    
    for character in test_characters:
        print(f"\n📋 Testing character query: '{character}'")
        try:
            result = get_character_context(character)
            if result:
                print(f"   ✅ SUCCESS: Retrieved {len(result)} chars")
                print(f"   📝 Preview: {result[:100]}...")
            else:
                print(f"   ⚠️  No results for: {character}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_unified_search_strategy():
    """Test the simplified get_relevant_wiki_context function"""
    print("\n🔍 TESTING UNIFIED SEARCH STRATEGY")
    print("=" * 60)
    
    test_cases = [
        ("stardancer logs", "Should route to log search"),
        ("who is Marcus Blaine", "Should route to character search"),
        ("USS Enterprise specs", "Should route to ship search"),
        ("warp drive technology", "Should use general search"),
        ("tell me about the Federation", "Should route to character search"),
        ("what happened yesterday", "Should route to log search")
    ]
    
    for query, expected_behavior in test_cases:
        print(f"\n📋 Testing unified query: '{query}'")
        print(f"   🎯 Expected: {expected_behavior}")
        try:
            result = get_relevant_wiki_context(query, mission_logs_only=False, is_roleplay=False)
            if result:
                print(f"   ✅ SUCCESS: Retrieved {len(result)} chars")
                print(f"   📝 Preview: {result[:100]}...")
            else:
                print(f"   ⚠️  No results for: {query}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_phase2_integration():
    """Test that Phase 2 changes work together"""
    print("\n🎯 TESTING PHASE 2 INTEGRATION")
    print("=" * 60)
    
    # Test that removed functions don't break anything
    print("\n📊 Testing that removed complex logic doesn't break system...")
    
    # Test log search without is_ship_log_title
    print("   🔍 Testing log search without complex ship detection...")
    try:
        result = get_log_content("mission report", mission_logs_only=True)
        print(f"   ✅ Log search works: {len(result) if result else 0} chars")
    except Exception as e:
        print(f"   ❌ Log search failed: {e}")
    
    # Test ship search without hardcoded SHIP_NAMES
    print("   🚢 Testing ship search without hardcoded ship names...")
    try:
        result = get_ship_information("starship")
        print(f"   ✅ Ship search works: {len(result) if result else 0} chars")
    except Exception as e:
        print(f"   ❌ Ship search failed: {e}")
    
    # Test character search (new functionality)
    print("   👤 Testing new character search functionality...")
    try:
        result = get_character_context("captain")
        print(f"   ✅ Character search works: {len(result) if result else 0} chars")
    except Exception as e:
        print(f"   ❌ Character search failed: {e}")

def main():
    """Main test function"""
    print("🧪 PHASE 2 CONTENT RETRIEVER SIMPLIFICATION TESTS")
    print("=" * 80)
    print("Testing the simplified, category-based content retriever functions")
    print("=" * 80)
    
    try:
        # Test individual functions
        test_simplified_log_search()
        test_simplified_ship_search()
        test_new_character_search()
        test_unified_search_strategy()
        
        # Test integration
        test_phase2_integration()
        
        print("\n🎉 PHASE 2 TESTING COMPLETE!")
        print("=" * 80)
        print("✅ All simplified functions have been tested")
        print("🚀 Complex logic removed, category-based searches implemented")
        print("📊 Code is now cleaner and more maintainable")
        
    except Exception as e:
        print(f"\n❌ TESTING FAILED: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 