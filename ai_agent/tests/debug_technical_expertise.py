#!/usr/bin/env python3
"""
Debug Technical Expertise Detection
==================================

Focused debugging of why the technical expertise scenario is failing
in the enhanced pathway validation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from handlers.ai_logic.response_router import route_message_to_handler
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.context_gatherer import build_contextual_cues
from handlers.ai_logic.response_decision_engine import create_response_decision_engine

def debug_technical_expertise():
    """Debug the technical expertise detection issue"""
    
    print("=" * 80)
    print("🔬 DEBUGGING TECHNICAL EXPERTISE DETECTION")
    print("=" * 80)
    
    # Setup test scenario
    rp_state = get_roleplay_state()
    
    # End any existing session
    if rp_state.is_roleplaying:
        rp_state.end_roleplay_session("test_reset")
    
    # Start DGM session with Shay
    rp_state.start_roleplay_session(
        turn_number=1,
        initial_triggers=['dgm_scene_setting'],
        channel_context={"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread", "channel_id": "rp-thread-123"},
        dgm_characters=["Shay"]
    )
    rp_state.add_participant("Shay", "dgm_mentioned", 1)
    
    # Test message
    test_message = '[Shay] *studying star charts* "These stellar navigation calculations seem off for this sector."'
    channel_context = {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread", "channel_id": "rp-thread-123"}
    
    print(f"📝 Test Message: {test_message}")
    print(f"📡 Channel Context: {channel_context}")
    
    # Step 1: Build contextual cues
    print(f"\n🧠 STEP 1: Building Contextual Cues")
    contextual_cues = build_contextual_cues(test_message, rp_state, 2)
    
    print(f"   Current Speaker: {contextual_cues.current_speaker}")
    print(f"   Current Expertise: {contextual_cues.current_expertise}")
    print(f"   Conversation Themes: {contextual_cues.conversation_dynamics.themes}")
    print(f"   Addressing Context:")
    print(f"      - Direct Mentions: {contextual_cues.addressing_context.direct_mentions}")
    print(f"      - Group Addressing: {contextual_cues.addressing_context.group_addressing}")
    print(f"      - Service Requests: {contextual_cues.addressing_context.service_requests}")
    print(f"      - Implicit Opportunity: {contextual_cues.addressing_context.implicit_opportunity}")
    print(f"      - Other Interactions: {contextual_cues.addressing_context.other_interactions}")
    
    # Step 2: Enhanced decision engine analysis
    print(f"\n🤖 STEP 2: Enhanced Decision Engine Analysis")
    decision_engine = create_response_decision_engine()
    response_decision = decision_engine.getNextResponseEnhanced(contextual_cues)
    
    print(f"   Should Respond: {response_decision.should_respond}")
    print(f"   Response Type: {response_decision.response_type}")
    print(f"   Reasoning: {response_decision.reasoning}")
    print(f"   Confidence: {response_decision.confidence}")
    
    # Step 3: Full route_message_to_handler analysis
    print(f"\n🚀 STEP 3: Full Route Message Analysis")
    final_decision = route_message_to_handler(test_message, [], channel_context)
    
    print(f"   Needs AI Generation: {final_decision.needs_ai_generation}")
    print(f"   Strategy Approach: {final_decision.strategy.get('approach', 'unknown')}")
    print(f"   Strategy Reasoning: {final_decision.strategy.get('reasoning', 'No reasoning')}")
    
    # Step 4: Check specific conditions
    print(f"\n🔍 STEP 4: Detailed Condition Analysis")
    
    # Check stellar cartography detection
    message_lower = test_message.lower()
    stellar_keywords = ['star', 'navigation', 'space', 'galaxy']
    detected_keywords = [kw for kw in stellar_keywords if kw in message_lower]
    print(f"   Stellar Keywords Detected: {detected_keywords}")
    
    # Check if expertise and themes align
    has_stellar_expertise = 'stellar_cartography' in contextual_cues.current_expertise
    has_stellar_theme = 'stellar_cartography' in contextual_cues.conversation_dynamics.themes
    print(f"   Has Stellar Expertise: {has_stellar_expertise}")
    print(f"   Has Stellar Theme: {has_stellar_theme}")
    print(f"   Both Required for Technical Response: {has_stellar_expertise and has_stellar_theme}")
    
    # Check character-to-character detection
    from handlers.ai_attention.response_logic import check_if_other_character_addressed
    other_character = check_if_other_character_addressed(test_message, rp_state)
    print(f"   Other Character Addressed: '{other_character}' (empty = no)")
    
    # Check if Elsie is directly addressed
    from handlers.ai_attention.response_logic import _is_elsie_directly_addressed
    elsie_addressed = _is_elsie_directly_addressed(test_message)
    print(f"   Elsie Directly Addressed: {elsie_addressed}")
    
    # Summary
    print(f"\n📊 ANALYSIS SUMMARY:")
    print(f"   Expected: roleplay_technical")
    print(f"   Actual: {final_decision.strategy.get('approach', 'unknown')}")
    
    if final_decision.strategy.get('approach') == 'roleplay_technical':
        print(f"   ✅ SUCCESS: Technical expertise correctly detected!")
    else:
        print(f"   ❌ ISSUE: Technical expertise not detected")
        print(f"   🔧 Likely cause: Priority logic or condition mismatch")
        
        # Suggest fixes
        print(f"\n🛠️  SUGGESTED FIXES:")
        if not has_stellar_expertise:
            print(f"   - Fix expertise detection in context_gatherer.py")
        if not has_stellar_theme:
            print(f"   - Fix theme detection in context_gatherer.py")
        if other_character:
            print(f"   - Fix character-to-character detection (false positive)")
        if not elsie_addressed and not has_stellar_expertise:
            print(f"   - Consider lowering priority threshold for technical expertise")


if __name__ == "__main__":
    debug_technical_expertise() 