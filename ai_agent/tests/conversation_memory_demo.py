"""
Conversation Memory Demo - Demonstration of Enhanced Roleplay Context
====================================================================

This script demonstrates how the new conversation memory system works
to enhance Elsie's roleplay responses with better continuity and context.
"""

import sys
import os

# Add the parent directory to the path so we can import the handlers
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from handlers.ai_attention.conversation_memory import ConversationMemory, getNextResponse, track_elsie_response, format_conversation_for_context
from handlers.ai_logic.response_decision_engine import create_response_decision_engine
from handlers.ai_attention.context_gatherer import build_contextual_cues
from handlers.ai_attention.state_manager import get_roleplay_state


def demo_conversation_flow():
    """
    Demonstrate how conversation memory enhances roleplay context.
    """
    print("🎭 CONVERSATION MEMORY SYSTEM DEMO")
    print("=" * 50)
    
    # Initialize conversation memory and enhanced decision engine
    memory = ConversationMemory(max_history=5)
    decision_engine = create_response_decision_engine()
    rp_state = get_roleplay_state()
    
    # Setup a test roleplay session
    rp_state.start_roleplay_session(1, ["emote"], {"channel_id": "test", "channel_name": "test"})
    
    # Simulate a roleplay conversation
    conversation_turns = [
        {"speaker": "Tavi", "message": "*walks into the bar looking tired*", "turn": 1},
        {"speaker": "Elsie", "message": "*looks up from polishing glasses* \"Rough day, Tavi?\"", "turn": 2},
        {"speaker": "Tavi", "message": "\"You could say that. Had a difficult training session with Commander Sif.\"", "turn": 3},
        {"speaker": "Elsie", "message": "*sets down a glass of water* \"Want to talk about it?\"", "turn": 4},
        {"speaker": "Tavi", "message": "\"It's just... sometimes I feel like I'm not living up to expectations.\"", "turn": 5},
    ]
    
    print("🎪 SIMULATING ROLEPLAY CONVERSATION:")
    print("-" * 40)
    
    # Process each turn
    for turn_data in conversation_turns:
        speaker = turn_data["speaker"]
        message = turn_data["message"]
        turn_number = turn_data["turn"]
        
        print(f"\n📝 Turn {turn_number}: [{speaker}] {message}")
        
        # Add to conversation memory
        memory.add_turn(speaker, message, turn_number)
        rp_state.add_conversation_turn(speaker, message, turn_number)
        
        # If this is a user turn (not Elsie), analyze for response suggestions
        if speaker != "Elsie" and memory.has_sufficient_context():
            print("\n💭 ANALYZING CONVERSATION FOR RESPONSE SUGGESTIONS:")
            
            # Build contextual cues for enhanced analysis
            contextual_cues = build_contextual_cues(message, rp_state, turn_number)
            
            # Get enhanced response decision
            response_decision = decision_engine.getNextResponseEnhanced(contextual_cues)
            
            print(f"   🎯 ENHANCED RESPONSE ANALYSIS:")
            print(f"      - Should Respond: {response_decision.should_respond}")
            print(f"      - Response Type: {response_decision.response_type.value}")
            print(f"      - Style: {response_decision.response_style}")
            print(f"      - Tone: {response_decision.tone}")
            print(f"      - Approach: {response_decision.approach}")
            print(f"      - Confidence: {response_decision.confidence:.2f}")
            print(f"      - Reasoning: {response_decision.reasoning}")
            
            # Also get traditional conversation analysis for comparison
            conversation_history = []
            for hist_turn in memory.get_recent_history():
                conversation_history.append({
                    'speaker': hist_turn.speaker,
                    'message': hist_turn.message,
                    'turn_number': hist_turn.turn_number,
                    'message_type': hist_turn.message_type
                })
            
            # Get response suggestion from conversation memory
            suggestion, analyzed = getNextResponse(
                conversation_history=conversation_history,
                memory_store=memory,
                character_context={'dgm_session': False}
            )
            
            if analyzed:
                print(f"   📊 CONVERSATION MEMORY ANALYSIS:")
                print(f"      - Style: {suggestion.style}")
                print(f"      - Tone: {suggestion.tone}")
                print(f"      - Approach: {suggestion.approach}")
                print(f"      - Direction: {suggestion.conversation_direction}")
                print(f"      - Themes: {suggestion.themes}")
                print(f"      - Reasoning: {suggestion.reasoning}")
    
    print("\n" + "=" * 50)
    print("📚 FINAL CONVERSATION CONTEXT:")
    print("-" * 40)
    
    # Show formatted conversation context
    context = format_conversation_for_context(memory, include_analysis=True)
    print(context)
    
    print("\n" + "=" * 50)
    print("🎭 ENHANCED ROLEPLAY PROMPT INTEGRATION EXAMPLE:")
    print("-" * 40)
    
    # Show how enhanced decision would be integrated into a roleplay prompt
    final_message = "\"It's just... sometimes I feel like I'm not living up to expectations.\""
    final_cues = build_contextual_cues(final_message, rp_state, 5)
    final_decision = decision_engine.getNextResponseEnhanced(final_cues)
    
    if final_decision.should_respond:
        sample_prompt_section = f"""
**ENHANCED RESPONSE GUIDANCE**:
- Response Type: {final_decision.response_type.value}
- Suggested Style: {final_decision.response_style}
- Suggested Tone: {final_decision.tone}
- Approach: {final_decision.approach}
- Address Character: {final_decision.address_character or 'General'}
- Relationship Tone: {final_decision.relationship_tone}
- Confidence: {final_decision.confidence:.2f}
- Analysis: {final_decision.reasoning}

**CONVERSATION CONTINUITY**: Use the conversation context above to maintain natural flow and avoid repetition. 
Reference recent events, emotions, or topics naturally.

{context}

This shows the recent flow of conversation. Use this context to maintain continuity, avoid repetition, 
and respond appropriately to the conversational dynamics and emotional needs.
"""
        print(sample_prompt_section)
    
    print("\n✨ DEMO COMPLETE - Enhanced conversation system provides:")
    print("   🧠 Contextual intelligence analysis")
    print("   🎯 Enhanced response decision making")
    print("   💭 Emotional intelligence integration")
    print("   📝 Context continuity")
    print("   🔄 Conversation flow analysis")
    print("   🎭 Enhanced roleplay immersion")


def demo_conversation_analysis_types():
    """
    Demonstrate different types of conversation analysis.
    """
    print("\n🤖 ENHANCED CONVERSATION ANALYSIS TYPES DEMO")
    print("=" * 50)
    
    decision_engine = create_response_decision_engine()
    rp_state = get_roleplay_state()
    
    test_conversations = [
        {
            "name": "Emotional Support Scenario",
            "messages": [
                "*sits at the bar looking dejected*",
                "\"What's wrong? You look upset.\"",
                "\"I just got some bad news from home.\""
            ]
        },
        {
            "name": "Technical Discussion",
            "messages": [
                "\"Elsie, what do you know about stellar cartography?\"",
                "\"Quite a bit actually. What specifically interests you?\"",
                "\"I'm trying to understand how we navigate in the Large Magellanic Cloud.\""
            ]
        },
        {
            "name": "Social Interaction",
            "messages": [
                "\"Hey everyone! *waves to the bar*\"",
                "\"Hello there! Welcome to the bar.\"",
                "\"Thanks! Mind if I join the conversation?\""
            ]
        }
    ]
    
    for scenario in test_conversations:
        print(f"\n🎪 SCENARIO: {scenario['name']}")
        print("-" * 30)
        
        # Setup fresh session for each scenario
        rp_state.end_roleplay_session("test_reset")
        rp_state.start_roleplay_session(1, ["emote"], {"channel_id": "test", "channel_name": "test"})
        
        memory = ConversationMemory()
        
        # Add messages to memory and analyze the final one
        for i, message in enumerate(scenario['messages']):
            speaker = "User" if i % 2 == 0 else "Elsie"
            memory.add_turn(speaker, message, i + 1)
            rp_state.add_conversation_turn(speaker, message, i + 1)
        
        # Analyze the final user message with enhanced system
        final_message = scenario['messages'][-1]
        if len(scenario['messages']) % 2 == 1:  # Odd number means last is user message
            contextual_cues = build_contextual_cues(final_message, rp_state, len(scenario['messages']))
            response_decision = decision_engine.getNextResponseEnhanced(contextual_cues)
            
            print(f"📊 ENHANCED ANALYSIS RESULTS:")
            print(f"   Should Respond: {response_decision.should_respond}")
            print(f"   Response Type: {response_decision.response_type.value}")
            print(f"   Style: {response_decision.response_style}")
            print(f"   Tone: {response_decision.tone}")
            print(f"   Approach: {response_decision.approach}")
            print(f"   Confidence: {response_decision.confidence:.2f}")
            print(f"   Reasoning: {response_decision.reasoning}")


if __name__ == "__main__":
    # Run the demonstrations
    demo_conversation_flow()
    demo_conversation_analysis_types() 