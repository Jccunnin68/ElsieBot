#!/usr/bin/env python3
"""
Debug Character-to-Character Interaction Detection
=================================================

Focused debugging of why the character-to-character interaction scenario is failing
in the enhanced pathway validation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from handlers.ai_logic.response_router import route_message_to_handler
from handlers.ai_attention.state_manager import get_roleplay_state

def debug_character_to_character():
    """Debug the character-to-character interaction detection issue"""
    
    print("=" * 80)
    print("👥 DEBUGGING CHARACTER-TO-CHARACTER INTERACTION DETECTION")
    print("=" * 80)
    
    # Setup DGM session with Maeve and Zarina
    rp_state = get_roleplay_state()
    
    # Clear any existing state
    if rp_state.is_roleplaying:
        rp_state.end_roleplay_session("test_reset")
    
    # Start DGM session with Maeve and Zarina
    rp_state.start_roleplay_session(
        turn_number=1,
        initial_triggers=['dgm_scene_setting'],
        channel_context={"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread", "channel_id": "rp-thread-123"},
        dgm_characters=["Maeve", "Zarina"]
    )
    
    rp_state.add_participant("Maeve", "dgm_mentioned", 1)
    rp_state.add_participant("Zarina", "dgm_mentioned", 1)
    
    print("🎭 DGM SESSION STARTED:")
    print(f"   📅 Roleplaying: {rp_state.is_roleplaying}")
    print(f"   🎯 Session Type: DGM")
    print(f"   📍 Channel: rp-thread (ID: rp-thread-123)")
    print(f"   👥 Participants: Maeve, Zarina")
    
    # Test message - character-to-character interaction
    test_message = '[Maeve] "Zarina, what do you think about the new mission parameters?"'
    channel_context = {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread", "channel_id": "rp-thread-123"}
    
    print(f"\n📝 Test Message: {test_message}")
    print(f"📡 Channel Context: {channel_context}")
    
    print(f"\n🚀 STEP 1: Full Route Message Analysis")
    response_decision = route_message_to_handler(test_message, [], channel_context)
    
    print(f"   Response Decision:")
    print(f"   - Type: {type(response_decision)}")
    print(f"   - Has strategy: {hasattr(response_decision, 'strategy')}")
    if hasattr(response_decision, 'strategy'):
        print(f"   - Strategy Approach: {response_decision.strategy.get('approach', 'unknown')}")
        print(f"   - Strategy Reasoning: {response_decision.strategy.get('reasoning', 'No reasoning')}")
    if hasattr(response_decision, 'needs_ai_generation'):
        print(f"   - Needs AI Generation: {response_decision.needs_ai_generation}")
    
    print(f"\n📊 ANALYSIS SUMMARY:")
    expected_approach = "roleplay_listening"
    expected_ai_generation = False
    actual_approach = response_decision.strategy.get('approach', 'unknown')
    actual_ai_generation = response_decision.needs_ai_generation
    
    print(f"   Expected Approach: {expected_approach}")
    print(f"   Actual Approach: {actual_approach}")
    print(f"   Expected AI Generation: {expected_ai_generation}")
    print(f"   Actual AI Generation: {actual_ai_generation}")
    
    approach_match = actual_approach == expected_approach
    ai_generation_match = actual_ai_generation == expected_ai_generation
    
    if approach_match and ai_generation_match:
        print(f"   ✅ SUCCESS: Character-to-character interaction correctly detected!")
    else:
        print(f"   ❌ ISSUE: Character-to-character interaction not detected correctly")
        print(f"   🔧 Approach match: {approach_match}")
        print(f"   🔧 AI generation match: {ai_generation_match}")
    
    print(f"\n🛠️  ANALYSIS:")
    print(f"   - Message contains 'Zarina' (character name)")
    print(f"   - Message does NOT contain 'Elsie' (should not trigger individual addressing)")
    print(f"   - This should be detected as character-to-character interaction")
    print(f"   - Expected result: roleplay_listening with AI generation = False")

if __name__ == "__main__":
    debug_character_to_character() 