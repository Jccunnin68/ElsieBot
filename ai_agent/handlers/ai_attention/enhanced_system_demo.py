#!/usr/bin/env python3
"""
Enhanced Contextual Intelligence System Demo
============================================

This demo script shows the enhanced getNextResponse system with contextual intelligence
in action, demonstrating how it analyzes complex roleplay scenarios and makes
intelligent decisions about whether and how Elsie should respond.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from handlers.ai_attention.context_gatherer import build_contextual_cues
from handlers.ai_attention.conversation_memory import getNextResponseEnhanced
from handlers.ai_attention.state_manager import RoleplayStateManager
from handlers.ai_attention.contextual_cues import ResponseType

def run_enhanced_system_demo():
    """Run comprehensive demonstration of the enhanced system"""
    
    print("=" * 80)
    print("🧠 ENHANCED CONTEXTUAL INTELLIGENCE SYSTEM DEMO")
    print("=" * 80)
    print()
    
    # Initialize test state
    rp_state = RoleplayStateManager()
    
    # Test scenarios
    scenarios = [
        {
            "name": "Direct Mention - Close Friend",
            "setup": lambda: setup_dgm_session(rp_state, ["Tavi"]),
            "message": '[Tavi] *walks up to the bar* "Hey Elsie, how are you doing today?"',
            "expected": ResponseType.ACTIVE_DIALOGUE
        },
        {
            "name": "Group Greeting",
            "setup": lambda: setup_regular_session(rp_state, ["Maeve", "Zarina"]),
            "message": '[Maeve] *enters Ten Forward* "Good morning everyone!"',
            "expected": ResponseType.GROUP_ACKNOWLEDGMENT
        },
        {
            "name": "Drink Service Request",
            "setup": lambda: setup_regular_session(rp_state, ["Marcus"]),
            "message": '[Marcus] *signals for a drink*',
            "expected": ResponseType.SUBTLE_SERVICE
        },
        {
            "name": "Implicit Response - Follow Up",
            "setup": lambda: setup_implicit_scenario(rp_state, "Zarina"),
            "message": '[Zarina] "I\'ve been thinking about what you said about stellar navigation."',
            "expected": ResponseType.IMPLICIT_RESPONSE
        },
        {
            "name": "Technical Expertise - Stellar Cartography",
            "setup": lambda: setup_regular_session(rp_state, ["Shay"]),
            "message": '[Shay] *studying star charts* "These navigation calculations seem off for this sector."',
            "expected": ResponseType.TECHNICAL_EXPERTISE
        },
        {
            "name": "Emotional Support Needed",
            "setup": lambda: setup_regular_session(rp_state, ["Tavi"]),
            "message": '[Tavi] *sits heavily at the bar* "I\'m having trouble living up to everyone\'s expectations."',
            "expected": ResponseType.SUPPORTIVE_LISTEN
        },
        {
            "name": "Character-to-Character Interaction",
            "setup": lambda: setup_regular_session(rp_state, ["Maeve", "Zarina"]),
            "message": '[Maeve] "Zarina, what do you think about the new mission parameters?"',
            "expected": ResponseType.NONE
        },
        {
            "name": "DGM Selective Mode - No Involvement",
            "setup": lambda: setup_dgm_session(rp_state, ["Tavi", "Maeve"]),
            "message": '[Tavi] *looks around the bar* "This place is so peaceful."',
            "expected": ResponseType.NONE
        }
    ]
    
    # Run each scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'=' * 60}")
        print(f"🎭 SCENARIO {i}: {scenario['name']}")
        print(f"{'=' * 60}")
        
        # Setup scenario
        scenario['setup']()
        
        # Build contextual cues
        print(f"\n📝 Message: {scenario['message']}")
        contextual_cues = build_contextual_cues(scenario['message'], rp_state, i)
        
        # Get enhanced response decision
        response_decision = getNextResponseEnhanced(contextual_cues)
        
        # Analyze results
        print(f"\n📊 ANALYSIS RESULTS:")
        print(f"   Expected: {scenario['expected'].value}")
        print(f"   Actual: {response_decision.response_type.value}")
        print(f"   Match: {'✅' if response_decision.response_type == scenario['expected'] else '❌'}")
        print(f"   Should Respond: {response_decision.should_respond}")
        print(f"   Confidence: {response_decision.confidence:.2f}")
        print(f"   Reasoning: {response_decision.reasoning}")
        
        if response_decision.should_respond:
            print(f"   Style: {response_decision.response_style}")
            print(f"   Tone: {response_decision.tone}")
            print(f"   Address: {response_decision.address_character}")
            print(f"   Relationship Tone: {response_decision.relationship_tone}")
        
        # Show contextual intelligence
        print(f"\n🧠 CONTEXTUAL INTELLIGENCE:")
        print(f"   Session Mode: {contextual_cues.session_mode.value}")
        print(f"   Scene Control: {contextual_cues.scene_control.value}")
        print(f"   Speaker: {contextual_cues.current_speaker}")
        print(f"   Known Characters: {list(contextual_cues.known_characters.keys())}")
        print(f"   Personality Mode: {contextual_cues.personality_mode.value}")
        print(f"   Conversation Themes: {contextual_cues.conversation_dynamics.themes}")
        print(f"   Emotional Tone: {contextual_cues.conversation_dynamics.emotional_tone}")
        
        addressing = contextual_cues.addressing_context
        print(f"   Direct Mentions: {addressing.direct_mentions}")
        print(f"   Group Addressing: {addressing.group_addressing}")
        print(f"   Service Requests: {addressing.service_requests}")
        print(f"   Implicit Opportunity: {addressing.implicit_opportunity}")
        print(f"   Other Interactions: {addressing.other_interactions}")
    
    # Summary
    print(f"\n{'=' * 80}")
    print("📋 DEMO COMPLETE")
    print("=" * 80)
    print("The enhanced contextual intelligence system successfully analyzed")
    print("complex roleplay scenarios and made intelligent decisions about")
    print("whether and how Elsie should respond, taking into account:")
    print("• Character relationships and personalities")
    print("• Conversation dynamics and emotional context")
    print("• Session modes and scene control levels")
    print("• Addressing patterns and implicit opportunities")
    print("• Technical expertise and emotional support needs")
    print("• DGM compatibility and selective response modes")
    print()
    print("This represents a major advancement from fragmented if-statement")
    print("logic to holistic, context-aware AI decision making.")


def setup_regular_session(rp_state: RoleplayStateManager, participants: list):
    """Setup a regular roleplay session"""
    rp_state.end_roleplay_session("test_reset")
    rp_state.start_roleplay_session(1, ["emote"], {"channel_id": "test", "channel_name": "test"})
    for participant in participants:
        rp_state.add_participant(participant, "user", 1)


def setup_dgm_session(rp_state: RoleplayStateManager, participants: list):
    """Setup a DGM-initiated session"""
    rp_state.end_roleplay_session("test_reset")
    rp_state.start_roleplay_session(1, ["dgm_scene_setting"], {"channel_id": "test", "channel_name": "test"})
    for participant in participants:
        rp_state.add_participant(participant, "dgm_mentioned", 1)


def setup_implicit_scenario(rp_state: RoleplayStateManager, character: str):
    """Setup an implicit response scenario"""
    setup_regular_session(rp_state, [character])
    # Simulate Elsie having addressed this character recently
    rp_state.set_last_character_addressed(character)
    rp_state.mark_character_turn(1, character)
    rp_state.mark_response_turn(2)  # Simulate Elsie responding
    rp_state.mark_character_turn(3, character)  # Now character is responding back


def demonstrate_character_knowledge():
    """Demonstrate the character knowledge system"""
    print(f"\n{'=' * 60}")
    print("👥 CHARACTER KNOWLEDGE DEMONSTRATION")
    print(f"{'=' * 60}")
    
    from handlers.ai_attention.context_gatherer import STARDANCER_CREW
    
    print("Known USS Stardancer crew members:")
    for name, profile in STARDANCER_CREW.items():
        print(f"\n• {name.title()}:")
        print(f"  Relationship: {profile.relationship.replace('_', ' ').title()}")
        print(f"  Role: {profile.role}")
        print(f"  Notes: {profile.personality_notes}")
        if profile.preferences:
            print(f"  Preferences: {profile.preferences}")


def demonstrate_conversation_analysis():
    """Demonstrate conversation analysis capabilities"""
    print(f"\n{'=' * 60}")
    print("💬 CONVERSATION ANALYSIS DEMONSTRATION")
    print(f"{'=' * 60}")
    
    from handlers.ai_attention.context_gatherer import (
        _analyze_emotional_tone, _extract_conversation_themes,
        _determine_conversation_direction, _analyze_conversation_intensity
    )
    
    test_messages = [
        "Hey everyone! Great to see you all here tonight!",
        "I'm feeling really down about the mission failure...",
        "Can you help me understand these stellar coordinates?",
        "Urgent! We need navigation data for the emergency jump!",
        "Tell me about the history of this sector."
    ]
    
    for message in test_messages:
        print(f"\nMessage: '{message}'")
        print(f"  Emotional Tone: {_analyze_emotional_tone(message)}")
        print(f"  Intensity: {_analyze_conversation_intensity(message)}")
        print(f"  Direction: {_determine_conversation_direction(message, None)}")


if __name__ == "__main__":
    try:
        run_enhanced_system_demo()
        demonstrate_character_knowledge()
        demonstrate_conversation_analysis()
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc() 