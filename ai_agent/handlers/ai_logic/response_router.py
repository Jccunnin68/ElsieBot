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

# Import the specialized handlers
from .roleplay_handler import handle_roleplay_message, handle_cross_channel_busy
from .non_roleplay_handler import handle_non_roleplay_message


def route_message_to_handler(user_message: str, conversation_history: List, channel_context: Optional[Dict] = None) -> ResponseDecision:
    """
    Main entry point for all message handling. Routes to appropriate handler based on roleplay state.
    
    ENHANCED: Now uses the new response decision engine for roleplay scenarios.
    
    Args:
        user_message: The user's message content
        conversation_history: List of previous messages
        channel_context: Channel information (ID, name, type, etc.)
        
    Returns:
        ResponseDecision: Decision about how to respond
    """
    print(f"🎯 RESPONSE ROUTER - Processing message")
    print(f"   📝 Message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
    
    # Get current roleplay state
    rp_state = get_roleplay_state()
    turn_number = len(conversation_history) + 1
    
    print(f"   🎭 Roleplay State: {'ACTIVE' if rp_state.is_roleplaying else 'INACTIVE'}")
    
    # Check for cross-channel messages if in roleplay
    if rp_state.is_roleplaying:
        if not rp_state.is_message_from_roleplay_channel(channel_context):
            print(f"   🚫 Cross-channel message detected - returning busy response")
            return handle_cross_channel_busy(rp_state, channel_context)
    
    # Check for DGM actions regardless of roleplay state
    dgm_result = check_dgm_post(user_message)
    if dgm_result['is_dgm']:
        print(f"   🎬 DGM Action detected: {dgm_result['action']}")
        return _process_dgm_action(dgm_result, user_message, turn_number, channel_context)
    
    # Route based on roleplay state
    if rp_state.is_roleplaying:
        print(f"   🎭 ROUTING TO ROLEPLAY HANDLER")
        return handle_roleplay_message(user_message, conversation_history, channel_context)
    else:
        print(f"   📝 ROUTING TO NON-ROLEPLAY HANDLER")
        return handle_non_roleplay_message(user_message, conversation_history)





def _process_dgm_action(dgm_result: Dict, user_message: str, turn_number: int, channel_context: Optional[Dict]):
    """Process DGM (Deputy Game Master) actions."""
    dgm_action = dgm_result['action']
    
    if dgm_action == 'scene_setting':
        print(f"   🎬 DGM Scene Setting - Starting roleplay session")
        
        # Start new roleplay session
        rp_state = get_roleplay_state()
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(
                turn_number=turn_number,
                initial_triggers=['dgm_scene_setting'],
                channel_context=channel_context,
                dgm_characters=dgm_result.get('characters', [])
            )
        
        # PHASE 2D: Store DGM scene context
        scene_context = dgm_result.get('scene_context', {})
        if scene_context:
            rp_state.store_dgm_scene_context(scene_context)
        
        # Return no-response decision with proper NO_RESPONSE string
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={
                'approach': 'dgm_scene_setting',
                'needs_database': False,
                'reasoning': 'DGM scene setting - no response needed',
                'context_priority': 'none'
            }
        )
    
    elif dgm_action == 'end_scene':
        print(f"   🎬 DGM Scene End - Ending roleplay session")
        
        # End roleplay session
        rp_state = get_roleplay_state()
        if rp_state.is_roleplaying:
            rp_state.end_roleplay_session('dgm_scene_end')
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={
                'approach': 'dgm_scene_end',
                'needs_database': False,
                'reasoning': 'DGM scene end - roleplay session ended',
                'context_priority': 'none'
            }
        )
    
    elif dgm_action == 'control_elsie':
        print(f"   🎭 DGM Controlled Elsie - Adding to context")
        
        # Ensure roleplay session is active
        rp_state = get_roleplay_state()
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(
                turn_number=turn_number,
                initial_triggers=['dgm_controlled_elsie'],
                channel_context=channel_context
            )
        
        # PHASE 2D: Store DGM scene context if present
        scene_context = dgm_result.get('scene_context', {})
        if scene_context:
            rp_state.store_dgm_scene_context(scene_context)
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={
                'approach': 'dgm_controlled_elsie',
                'needs_database': False,
                'reasoning': f'DGM controlled Elsie - content: "{dgm_result.get("elsie_content", "")}"',
                'context_priority': 'dgm_elsie_context',
                'elsie_content': dgm_result.get('elsie_content', '')
            }
        )
    
    # Unknown DGM action
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response="NO_RESPONSE",
        strategy={
            'approach': 'general',
            'needs_database': False,
            'reasoning': f'Unknown DGM action: {dgm_action}',
            'context_priority': 'none'
        }
    )


def is_cross_channel_message(channel_context: Optional[Dict]) -> bool:
    """Check if this message is from a different channel than the current roleplay."""
    rp_state = get_roleplay_state()
    
    if not rp_state.is_roleplaying or not channel_context:
        return False
    
    return not rp_state.is_message_from_roleplay_channel(channel_context)


 