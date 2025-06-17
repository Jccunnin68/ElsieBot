#!/usr/bin/env python3
"""
Test script for enhanced query detection logic
"""

import sys
import os

# Add the parent directory to the path so we can import the handlers
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from handlers.ai_logic.query_detection import (
        is_ship_plus_log_query,
        is_character_plus_log_query
    )
    from handlers.ai_wisdom.log_patterns import has_log_specific_terms
    
    print("✅ Successfully imported new functions!")
    
    # Test cases
    test_cases = [
        # Should prioritize logs over general ship info
        "Stardancer mission logs",
        "USS Enterprise log entries", 
        "Adagio crew reports",
        
        # Should prioritize logs over general character info
        "Captain Smith's log entries",
        "Commander Johnson mission reports",
        "Lieutenant Davis duty logs",
        
        # Should NOT prioritize logs (general info queries)
        "tell me about the Stardancer",
        "tell me about Captain Smith",
        "what is the USS Enterprise",
        
        # Should NOT prioritize logs (no log terms)
        "Stardancer specifications",
        "Captain Smith biography"
    ]
    
    print("\n🧪 Testing enhanced query detection:")
    print("=" * 60)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n{i}. Query: '{query}'")
        
        # Test log prioritization (using ship+log and character+log detection)
        is_ship_log, ship_name_check, log_type_check = is_ship_plus_log_query(query)
        is_char_log, char_name_check, log_type_check2 = is_character_plus_log_query(query)
        prioritize_logs = is_ship_log or is_char_log
        print(f"   Prioritize logs: {prioritize_logs}")
        if prioritize_logs:
            if is_ship_log:
                print(f"   Query type: ship_logs")
                print(f"   Details: {{'ship': '{ship_name_check}', 'log_type': '{log_type_check}'}}")
            elif is_char_log:
                print(f"   Query type: character_logs")
                print(f"   Details: {{'character': '{char_name_check}', 'log_type': '{log_type_check2}'}}")
        
        # Test ship+log detection
        is_ship_log, ship_name, log_type = is_ship_plus_log_query(query)
        if is_ship_log:
            print(f"   Ship+Log detected: {ship_name} ({log_type})")
        
        # Test character+log detection  
        is_char_log, character_name, log_type = is_character_plus_log_query(query)
        if is_char_log:
            print(f"   Character+Log detected: {character_name} ({log_type})")
        
        # Test log terms detection
        has_log_terms = has_log_specific_terms(query)
        print(f"   Has log terms: {has_log_terms}")
    
    print("\n✅ Enhanced query detection test completed!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Test error: {e}") 