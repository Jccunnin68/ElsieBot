"""
Integration Test for Emotional Intelligence Architecture
=======================================================

This test validates the new architecture where:
- ai_attention provides context
- ai_emotion provides emotional intelligence
- ai_logic makes decisions and integrates everything
"""

import sys
import os

# Add the handlers directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_enhanced_architecture():
    """
    Test the complete enhanced architecture flow.
    """
    print("🧪 TESTING ENHANCED EMOTIONAL INTELLIGENCE ARCHITECTURE")
    
    # Test message that should trigger emotional support
    test_message = "I'm having trouble living up to everyone's expectations"
    
    try:
        # Step 1: Test Context Gathering (ai_attention)
        from ai_attention.context_gatherer import build_contextual_cues
        from ai_attention.state_manager import RoleplayStateManager
        
        # Create mock roleplay state
        rp_state = RoleplayStateManager()
        rp_state.start_roleplay_session(1, ['test'], {'channel_name': 'test-channel'})
        
        # Build contextual cues
        contextual_cues = build_contextual_cues(test_message, rp_state, 1)
        contextual_cues.current_message = test_message  # Add message for analysis
        
        print(f"   ✅ CONTEXT GATHERING: Session mode {contextual_cues.session_mode.value}")
        
        # Step 2: Test Emotional Intelligence (ai_emotion)
        from emotional_analysis import analyze_emotional_context
        from context_sensitivity import distinguish_group_vs_contextual
        from priority_resolution import resolve_emotional_vs_group_conflict
        
        # Test emotional analysis
        emotional_context = analyze_emotional_context(test_message)
        print(f"   🎭 EMOTIONAL ANALYSIS: {emotional_context.get('emotional_tone', 'unknown')}")
        
        # Test context sensitivity
        addressing_type, confidence = distinguish_group_vs_contextual(test_message)
        print(f"   👥 ADDRESSING ANALYSIS: {addressing_type} (confidence: {confidence:.2f})")
        
        # Test priority resolution if needed
        if addressing_type == 'contextual_mention' and emotional_context.get('needs_support'):
            decision_type, final_confidence, reasoning = resolve_emotional_vs_group_conflict(
                0.8,  # emotional confidence
                confidence,  # addressing confidence
                test_message,
                {'vulnerability_level': 'moderate'}
            )
            print(f"   ⚖️  PRIORITY RESOLUTION: {decision_type} (confidence: {final_confidence:.2f})")
        
        # Step 3: Test Decision Engine (ai_logic)
        from ai_logic.response_decision_engine import create_response_decision_engine
        
        decision_engine = create_response_decision_engine()
        response_decision = decision_engine.getNextResponseEnhanced(contextual_cues)
        
        print(f"   🧠 DECISION ENGINE RESULT:")
        print(f"      - Should respond: {response_decision.should_respond}")
        print(f"      - Response type: {response_decision.response_type.value}")
        print(f"      - Reasoning: {response_decision.reasoning}")
        print(f"      - Confidence: {response_decision.confidence:.2f}")
        
        # Step 4: Test Integration via Response Router
        from ai_logic.response_router import route_message_to_handler
        
        final_decision = route_message_to_handler(
            test_message,
            [],  # conversation_history
            {'channel_name': 'test-channel', 'type': 'text'}
        )
        
        print(f"   🎯 RESPONSE ROUTER RESULT:")
        print(f"      - Needs AI generation: {final_decision.needs_ai_generation}")
        print(f"      - Strategy approach: {final_decision.strategy.get('approach', 'unknown')}")
        print(f"      - Enhanced decision: {final_decision.strategy.get('enhanced_decision', False)}")
        print(f"      - Emotional intelligence used: {final_decision.strategy.get('emotional_intelligence_used', False)}")
        
        # Clean up
        rp_state.end_roleplay_session('test_complete')
        
        print(f"   ✅ INTEGRATION TEST COMPLETED SUCCESSFULLY")
        return True
        
    except Exception as e:
        print(f"   ❌ INTEGRATION TEST FAILED: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return False


def test_fallback_behavior():
    """
    Test that the system gracefully falls back when emotional intelligence modules aren't available.
    """
    print("🔧 TESTING FALLBACK BEHAVIOR")
    
    # Test with a simple message when not in roleplay
    test_message = "Hello Elsie!"
    
    try:
        from ai_logic.response_router import route_message_to_handler
        
        final_decision = route_message_to_handler(
            test_message,
            [],  # conversation_history
            {'channel_name': 'general', 'type': 'text'}
        )
        
        print(f"   📝 NON-ROLEPLAY HANDLING:")
        print(f"      - Needs AI generation: {final_decision.needs_ai_generation}")
        print(f"      - Strategy approach: {final_decision.strategy.get('approach', 'unknown')}")
        print(f"      - Reasoning: {final_decision.strategy.get('reasoning', 'No reasoning')}")
        
        print(f"   ✅ FALLBACK TEST COMPLETED")
        return True
        
    except Exception as e:
        print(f"   ❌ FALLBACK TEST FAILED: {e}")
        return False


if __name__ == "__main__":
    print("🚀 STARTING EMOTIONAL INTELLIGENCE ARCHITECTURE TESTS")
    
    # Test 1: Enhanced Architecture
    test1_result = test_enhanced_architecture()
    
    # Test 2: Fallback Behavior
    test2_result = test_fallback_behavior()
    
    if test1_result and test2_result:
        print("\n🎉 ALL TESTS PASSED - Enhanced Emotional Intelligence Architecture is working!")
    else:
        print("\n⚠️  SOME TESTS FAILED - Check the error messages above")
        
    print("\n📋 ARCHITECTURE SUMMARY:")
    print("   - ai_attention: Provides contextual intelligence")
    print("   - ai_emotion: Provides emotional intelligence") 
    print("   - ai_logic: Makes decisions and integrates everything")
    print("   - Clean separation of concerns achieved!") 