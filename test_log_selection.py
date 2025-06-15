#!/usr/bin/env python3
"""
Test script for log selection functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent.handlers.ai_logic.query_detection import detect_log_selection_query

def test_log_selection_detection():
    """Test the new log selection detection"""
    
    test_cases = [
        # Random selection tests
        ("pick a log", True, "random", None),
        ("pick a log from stardancer", True, "random", "stardancer"),
        ("give me a random log", True, "random", None),
        ("surprise me with a log", True, "random", None),
        
        # Latest/Recent tests
        ("show me the latest log", True, "latest", None),
        ("get the most recent adagio log", True, "latest", "adagio"),
        ("what's the last mission log", True, "latest", None),
        ("recent stardancer logs", True, "latest", "stardancer"),
        
        # First/Earliest tests
        ("show me the first log", True, "first", None),
        ("get the earliest pilgrim log", True, "first", "pilgrim"),
        ("what was the original mission log", True, "first", None),
        
        # Date-based tests
        ("logs from today", True, "today", None),
        ("yesterday's mission logs", True, "yesterday", None),
        ("this week's stardancer logs", True, "this_week", "stardancer"),
        
        # Non-log queries (should return False)
        ("tell me about the stardancer", False, "", None),
        ("who is captain kirk", False, "", None),
        ("pick a character", False, "", None),
    ]
    
    print("🧪 TESTING LOG SELECTION DETECTION")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for query, expected_is_selection, expected_type, expected_ship in test_cases:
        is_selection, selection_type, ship_name = detect_log_selection_query(query)
        
        success = (
            is_selection == expected_is_selection and
            selection_type == expected_type and
            ship_name == expected_ship
        )
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | '{query}'")
        print(f"      Expected: is_selection={expected_is_selection}, type='{expected_type}', ship='{expected_ship}'")
        print(f"      Got:      is_selection={is_selection}, type='{selection_type}', ship='{ship_name}'")
        print()
        
        if success:
            passed += 1
        else:
            failed += 1
    
    print("=" * 50)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("⚠️  SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = test_log_selection_detection()
    sys.exit(0 if success else 1) 