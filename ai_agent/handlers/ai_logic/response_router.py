"""
Response Router - Main Entry Point for Message Handling
=====================================================

This module provides the single entry point for all message handling.
It checks roleplay mode and routes to the appropriate handler.

CRITICAL FLOW:
1. Message comes in
2. Check: Am I in roleplay mode?
3. Route to roleplay_handler OR non_roleplay_handler
4. Return ResponseDecision
"""

from typing import Dict, List, Optional

from .response_decision import ResponseDecision
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.dgm_handler import check_dgm_post
import re


def route_message_to_handler(user_message: str, conversation_history: List, channel_context: Optional[Dict] = None) -> ResponseDecision:
    """
    THE SINGLE ENTRY POINT for all message handling.
    
    Flow:
    1. Check for DGM posts (never respond)
    2. Check roleplay mode
    3. Route to appropriate handler
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation turns
        channel_context: Channel information
        
    Returns:
        ResponseDecision with needs_ai_generation and strategy
    """
    print(f"\n🎯 RESPONSE ROUTER - ENTRY POINT")
    print(f"   📝 Message: {user_message[:100]}{'...' if len(user_message) > 100 else ''}")
    
    # CRITICAL: Check for DGM posts FIRST - Process DGM action then NEVER respond
    if re.search(r'^\s*\[DGM\]', user_message, re.IGNORECASE):
        print(f"   🎬 DGM POST DETECTED - Processing action then NO RESPONSE")
        
        # STEP 1: Process the DGM action to manage roleplay state
        dgm_result = check_dgm_post(user_message)
        _process_dgm_action(dgm_result, user_message, len(conversation_history) + 1, channel_context)
        
        # STEP 2: Return NO_RESPONSE (Elsie never responds to DGM posts)
        dgm_strategy = {
            'approach': f"dgm_{dgm_result.get('action', 'post')}",
            'needs_database': False,
            'reasoning': f"DGM post processed - {dgm_result.get('action', 'unknown')} - NEVER RESPOND",
            'context_priority': 'none'
        }
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy=dgm_strategy
        )
    
    # Get roleplay state
    rp_state = get_roleplay_state()
    
    # MAIN ROUTING DECISION: Check roleplay mode
    if rp_state.is_roleplaying:
        print(f"   🎭 ROLEPLAY MODE: Routing to roleplay_handler")
        print(f"      👥 Participants: {rp_state.get_participant_names()}")
        print(f"      📍 Channel: {rp_state.get_roleplay_channel_info()['channel_name']}")
        
        from .roleplay_handler import handle_roleplay_message
        return handle_roleplay_message(user_message, conversation_history, channel_context)
    
    else:
        print(f"   💬 NON-ROLEPLAY MODE: Routing to non_roleplay_handler")
        
        from .non_roleplay_handler import handle_non_roleplay_message
        return handle_non_roleplay_message(user_message, conversation_history)


def _process_dgm_action(dgm_result: Dict, user_message: str, turn_number: int, channel_context: Optional[Dict]):
    """
    Process DGM actions to properly manage roleplay state.
    
    This is CRITICAL for DGM scene start/end functionality.
    DGM posts never get responses, but they must update roleplay state.
    """
    action = dgm_result.get('action', 'unknown')
    rp_state = get_roleplay_state()
    
    print(f"   🎬 PROCESSING DGM ACTION: {action}")
    
    if action == 'scene_setting':
        # DGM is starting a new roleplay scene
        dgm_characters = dgm_result.get('characters', [])
        triggers = dgm_result.get('triggers', [])
        
        print(f"   🚀 DGM SCENE START: Starting roleplay session")
        print(f"      👥 DGM Characters: {dgm_characters}")
        print(f"      📍 Channel: {channel_context.get('channel_name', 'Unknown') if channel_context else 'None'}")
        
        # Start new roleplay session
        rp_state.start_roleplay_session(turn_number, triggers, channel_context, dgm_characters)
        
    elif action == 'end_scene':
        # DGM is ending the current roleplay scene
        if rp_state.is_roleplaying:
            print(f"   🎬 DGM SCENE END: Ending roleplay session")
            rp_state.end_roleplay_session("dgm_scene_end")
        else:
            print(f"   ⚠️  DGM SCENE END: No active roleplay session to end")
            
    elif action == 'control_elsie':
        # DGM is controlling Elsie directly
        elsie_content = dgm_result.get('elsie_content', '')
        
        print(f"   🎭 DGM CONTROLLED ELSIE: Content length {len(elsie_content)} chars")
        
        # Ensure roleplay session is active for DGM-controlled Elsie
        if not rp_state.is_roleplaying:
            triggers = dgm_result.get('triggers', [])
            print(f"      🚀 Starting roleplay session for DGM-controlled Elsie")
            rp_state.start_roleplay_session(turn_number, triggers, channel_context)
    
    else:
        print(f"   ❓ UNKNOWN DGM ACTION: {action}")


def is_cross_channel_message(channel_context: Optional[Dict]) -> bool:
    """
    Check if this message is from a different channel than the active roleplay.
    Used for channel isolation during roleplay sessions.
    """
    rp_state = get_roleplay_state()
    
    if not rp_state.is_roleplaying:
        return False
    
    return not rp_state.is_message_from_roleplay_channel(channel_context) 