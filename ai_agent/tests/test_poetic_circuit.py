#!/usr/bin/env python3
"""
Test script for Elsie's poetic short circuit feature
"""

import sys
import os

# Add the parent directory to the path so we can import the handlers
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from handlers.ai_emotion import should_trigger_poetic_circuit, get_poetic_response

def test_poetic_circuits():
    """Test the poetic short circuit functionality"""
    
    print("🎭 TESTING ELSIE'S POETIC SHORT CIRCUITS")
    print("=" * 60)
    
    # Test messages that should be eligible for poetic responses
    casual_messages = [
        "I love the view from here",
        "The music sounds beautiful tonight",
        "This place has such a nice atmosphere",
        "You seem different somehow",
        "The stars look amazing through that window",
        "I feel so relaxed here",
        "Something about this moment feels special",
        "The lighting in here is perfect"
    ]
    
    # Test messages that should NOT trigger poetic responses (serious queries)
    serious_messages = [
        "Tell me about Captain Picard",
        "What is the USS Enterprise?",
        "Show me the mission logs",
        "OOC when is the next meeting?",
        "Who is Data?"
    ]
    
    print("\n🌟 TESTING CASUAL MESSAGES (eligible for poetic circuits):")
    print("-" * 50)
    
    for message in casual_messages:
        should_trigger = should_trigger_poetic_circuit(message, [])
        print(f"Message: '{message}'")
        print(f"Trigger: {'YES' if should_trigger else 'NO'}")
        
        if should_trigger:
            poetic_response = get_poetic_response(message, "normal response")
            print(f"Poetic Response:\n{poetic_response}")
            print()
        print("-" * 30)
    
    print("\n⚡ TESTING SERIOUS MESSAGES (should never trigger):")
    print("-" * 50)
    
    for message in serious_messages:
        should_trigger = should_trigger_poetic_circuit(message, [])
        print(f"Message: '{message}' -> Trigger: {'YES' if should_trigger else 'NO'}")
    
    print("\n🎨 EXAMPLE POETIC RESPONSES:")
    print("-" * 50)
    
    # Force generate a few poetic responses to show variety
    for i in range(3):
        response = get_poetic_response("test message", "")
        print(f"Example {i+1}:")
        print(response)
        print("-" * 30)
    
    print("\n" + "=" * 60)
    print("🎭 POETIC CIRCUIT TESTING COMPLETE")
    print("Note: In actual usage, poetic circuits trigger randomly ~15% of the time")
    print("for eligible casual dialogue messages.")

if __name__ == "__main__":
    test_poetic_circuits() 