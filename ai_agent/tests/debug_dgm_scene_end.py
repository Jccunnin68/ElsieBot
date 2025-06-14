#!/usr/bin/env python3
"""
Debug DGM Scene End Detection
============================

Focused debugging of why the DGM scene end scenario is failing
in the enhanced pathway validation.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from handlers.ai_logic.response_router import route_message_to_handler
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.dgm_handler import check_dgm_post

def debug_dgm_scene_end():
    """Debug the DGM scene end detection issue"""
    
    print("=" * 80)
    print("🎬 DEBUGGING DGM SCENE END DETECTION")
    print("=" * 80)
    
    # Setup DGM session
    rp_state = get_roleplay_state()
    
    # Clear any existing state
    if rp_state.is_roleplaying:
        rp_state.end_roleplay_session("test_reset")
    
    # Start DGM session
    rp_state.start_roleplay_session(
        turn_number=1,
        initial_triggers=['dgm_scene_setting'],
        channel_context={"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread", "channel_id": "rp-thread-123"},
        dgm_characters=["Tavi"]
    )
    
    rp_state.add_participant("Tavi", "dgm_mentioned", 1)
    
    print("🎭 DGM SESSION STARTED:")
    print(f"   📅 Roleplaying: {rp_state.is_roleplaying}")
    print(f"   🎯 Session Type: DGM")
    print(f"   📍 Channel: rp-thread (ID: rp-thread-123)")
    print(f"   🎬 DGM Session: Active")
    
    # Test message
    test_message = '[DGM] END'
    channel_context = {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread", "channel_id": "rp-thread-123"}
    
    print(f"\n📝 Test Message: {test_message}")
    print(f"📡 Channel Context: {channel_context}")
    
    print(f"\n🧠 STEP 1: Direct DGM Handler Test")
    dgm_result = check_dgm_post(test_message)
    print(f"   DGM Handler Result:")
    print(f"   - Is DGM: {dgm_result.get('is_dgm', False)}")
    print(f"   - Action: {dgm_result.get('action', 'none')}")
    print(f"   - Triggers: {dgm_result.get('triggers', [])}")
    print(f"   - Confidence: {dgm_result.get('confidence', 0.0)}")
    
    print(f"\n🚀 STEP 2: Full Route Message Analysis")
    response_decision = route_message_to_handler(test_message, [], channel_context)
    
    print(f"   Response Decision:")
    print(f"   - Type: {type(response_decision)}")
    print(f"   - Has strategy: {hasattr(response_decision, 'strategy')}")
    if hasattr(response_decision, 'strategy'):
        print(f"   - Strategy Approach: {response_decision.strategy.get('approach', 'unknown')}")
        print(f"   - Strategy Reasoning: {response_decision.strategy.get('reasoning', 'No reasoning')}")
    if hasattr(response_decision, 'needs_ai_generation'):
        print(f"   - Needs AI Generation: {response_decision.needs_ai_generation}")
    
    # Debug the response decision object
    print(f"   - Response Decision Attributes: {dir(response_decision)}")
    
    print(f"\n📊 ANALYSIS SUMMARY:")
    expected_approach = "dgm_scene_end"
    actual_approach = response_decision.strategy.get('approach', 'unknown')
    
    print(f"   Expected: {expected_approach}")
    print(f"   Actual: {actual_approach}")
    
    if actual_approach == expected_approach:
        print(f"   ✅ SUCCESS: DGM scene end correctly detected!")
    else:
        print(f"   ❌ ISSUE: DGM scene end not detected")
        print(f"   🔧 Likely cause: Routing or detection logic issue")
    
    print(f"\n🛠️  SUGGESTED FIXES:")
    if dgm_result.get('is_dgm', False) and dgm_result.get('action') == 'end_scene':
        print(f"   - DGM handler correctly detects scene end")
        print(f"   - Issue is likely in the routing logic")
        print(f"   - Check response_router.py DGM handling")
    else:
        print(f"   - DGM handler is not detecting scene end")
        print(f"   - Check dgm_handler.py pattern matching")
        print(f"   - Verify scene end patterns include '[DGM] END'")

if __name__ == "__main__":
    debug_dgm_scene_end() 