"""
Implicit Response Test - Verify DGM Compatibility
================================================

Test script to verify that implicit response functionality works correctly
in DGM sessions with the new conversation memory system.
"""

from ai_agent.handlers.ai_attention.state_manager import RoleplayStateManager
from ai_agent.handlers.ai_attention.conversation_memory import ConversationMemory
from ai_agent.handlers.ai_logic.strategy_engine import should_elsie_respond_in_roleplay


def test_dgm_implicit_response():
    """
    Test that implicit responses work correctly in DGM sessions.
    """
    print("🧪 IMPLICIT RESPONSE TEST - DGM COMPATIBILITY")
    print("=" * 60)
    
    # Initialize state manager
    rp_state = RoleplayStateManager()
    
    # Start a DGM session
    channel_context = {
        'channel_id': 'test_channel',
        'channel_name': 'Test Channel',
        'type': 'GUILD_TEXT'
    }
    
    triggers = ['dgm_scene_setting']
    rp_state.start_roleplay_session(1, triggers, channel_context)
    
    print(f"📊 SESSION STATE:")
    print(f"   - DGM Session: {rp_state.is_dgm_session()}")
    print(f"   - Roleplaying: {rp_state.is_roleplaying}")
    print(f"   - Conversation Memory: {rp_state.has_conversation_memory()}")
    
    # Simulate conversation sequence
    conversation_scenario = [
        {
            "turn": 2,
            "speaker": "Tavi",
            "message": "*walks into the bar looking tired*",
            "description": "Character enters the scene"
        },
        {
            "turn": 3,
            "speaker": "Elsie",
            "message": "*looks up from cleaning glasses* \"Rough day, Tavi?\"",
            "description": "Elsie initiates conversation (should track Tavi as addressed)",
            "addressed_to": "Tavi"
        },
        {
            "turn": 4,
            "speaker": "Tavi", 
            "message": "\"Yeah, training was brutal today. Thanks for asking.\"",
            "description": "Tavi responds to Elsie (should trigger implicit response)"
        }
    ]
    
    print(f"\n🎪 SIMULATING DGM CONVERSATION SCENARIO:")
    print("-" * 40)
    
    for scenario in conversation_scenario:
        turn_number = scenario["turn"]
        speaker = scenario["speaker"]
        message = scenario["message"]
        description = scenario["description"]
        addressed_to = scenario.get("addressed_to")
        
        print(f"\n📝 Turn {turn_number}: {description}")
        print(f"   [{speaker}]: {message}")
        
        if speaker == "Elsie":
            # Track Elsie's response
            rp_state.add_conversation_turn(speaker, message, turn_number, addressed_to)
            rp_state.mark_response_turn(turn_number)
            if addressed_to:
                rp_state.set_last_character_addressed(addressed_to)
                print(f"   🎯 ELSIE ADDRESSED: {addressed_to}")
        else:
            # Add user turn and check response logic
            rp_state.add_conversation_turn(speaker, message, turn_number)
            rp_state.mark_character_turn(turn_number, speaker)
            
            # Test response logic
            should_respond, reason = should_elsie_respond_in_roleplay(message, rp_state, turn_number)
            
            print(f"   🤔 RESPONSE DECISION:")
            print(f"      - Should respond: {should_respond}")
            print(f"      - Reason: {reason}")
            
            # Special check for implicit response in DGM session
            if reason == "implicit_response":
                print(f"   ✅ DGM IMPLICIT RESPONSE WORKING!")
                print(f"      - DGM session allows implicit responses")
                print(f"      - Natural conversation flow maintained")
            elif turn_number == 4:  # This should be an implicit response
                print(f"   ❌ IMPLICIT RESPONSE FAILED!")
                print(f"      - Expected implicit response but got: {reason}")
                print(f"      - DGM session may be blocking natural conversation")
    
    print(f"\n📊 FINAL STATE ANALYSIS:")
    print("-" * 40)
    
    # Check conversation memory state
    if rp_state.has_conversation_memory():
        print(f"💭 CONVERSATION MEMORY:")
        for turn in rp_state.conversation_memory.get_recent_history():
            print(f"   Turn {turn.turn_number}: [{turn.speaker}] -> {turn.addressed_to or 'general'}")
            print(f"      Message: {turn.message[:50]}...")
    
    # Check implicit response state
    print(f"\n🎯 IMPLICIT RESPONSE STATE:")
    print(f"   - Last character Elsie addressed: {rp_state.last_character_elsie_addressed}")
    print(f"   - Turn history: {rp_state.turn_history[-3:] if rp_state.turn_history else 'Empty'}")
    
    # Test implicit response logic directly
    test_message = "\"Yeah, training was brutal today. Thanks for asking.\""
    is_implicit = rp_state.is_simple_implicit_response(4, test_message)
    print(f"   - Direct implicit check: {is_implicit}")
    
    print(f"\n🎭 DGM IMPLICIT RESPONSE TEST COMPLETE")
    print(f"   Expected: Implicit responses should work in DGM sessions")
    print(f"   Result: {'✅ PASS' if is_implicit else '❌ FAIL'}")


def test_non_dgm_implicit_response():
    """
    Test that implicit responses work correctly in regular (non-DGM) sessions.
    """
    print("\n🧪 IMPLICIT RESPONSE TEST - NON-DGM SESSION")
    print("=" * 60)
    
    # Initialize state manager
    rp_state = RoleplayStateManager()
    
    # Start a regular session
    channel_context = {
        'channel_id': 'test_channel',
        'channel_name': 'Test Channel',
        'type': 'GUILD_TEXT'
    }
    
    triggers = ['emote', 'dialogue']  # Not DGM
    rp_state.start_roleplay_session(1, triggers, channel_context)
    
    print(f"📊 SESSION STATE:")
    print(f"   - DGM Session: {rp_state.is_dgm_session()}")
    print(f"   - Roleplaying: {rp_state.is_roleplaying}")
    
    # Same conversation scenario as DGM test
    rp_state.add_conversation_turn("Tavi", "*walks in*", 2)
    rp_state.add_conversation_turn("Elsie", "\"Hello Tavi!\"", 3, "Tavi")
    rp_state.set_last_character_addressed("Tavi")
    rp_state.mark_response_turn(3)
    
    test_message = "\"Hi Elsie, how are you?\""
    should_respond, reason = should_elsie_respond_in_roleplay(test_message, rp_state, 4)
    
    print(f"🤔 NON-DGM RESPONSE DECISION:")
    print(f"   - Should respond: {should_respond}")
    print(f"   - Reason: {reason}")
    print(f"   - Result: {'✅ PASS' if reason == 'implicit_response' else '❌ FAIL'}")


if __name__ == "__main__":
    test_dgm_implicit_response()
    test_non_dgm_implicit_response()
    
    print(f"\n🎯 SUMMARY:")
    print(f"   The implicit response system should work in BOTH DGM and non-DGM sessions")
    print(f"   DGM sessions use 'selective passive' mode, allowing implicit responses")
    print(f"   This maintains natural conversation flow while respecting DGM scene control") 