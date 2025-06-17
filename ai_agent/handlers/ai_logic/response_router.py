"""
Response Router - Message Routing and Decision Coordination
==========================================================

This module routes incoming messages to the appropriate handler based on:
- Roleplay vs non-roleplay context
- Enhanced query detection with conflict prevention
- Cross-channel message coordination

ENHANCED: Uses enhanced query detection to prevent conflicts and provide
appropriate routing for different query types.
"""

from typing import Dict, List, Optional
import traceback

from .response_decision import ResponseDecision
from ..ai_attention import get_roleplay_state, is_roleplay_allowed_channel
from ..ai_attention.dgm_handler import check_dgm_post

# Import the specialized handlers
from .roleplay_handler import handle_roleplay_message, handle_cross_channel_busy
from .structured_query_handler import handle_structured_query



def route_message_to_handler(user_message: str, conversation_history: list, channel_context: Dict = None) -> ResponseDecision:
    """
    Routes the user's message to the appropriate handler based on the application's state.
    
    New Simplified Flow:
    1. Check if roleplay is active. If so, ALL messages go to the Roleplay Handler.
    2. If not in roleplay, check if the channel is a designated roleplay channel to potentially start a session.
    3. Check for mock responses (e.g., simple greetings).
    4. Default to the standard structured query handler for all other messages.
    """
    rp_state = get_roleplay_state()
    
    # 1. Prioritize active roleplay sessions
    if rp_state.is_roleplay_active():
        print("🚦 ROUTER: Roleplay active, routing to Roleplay Handler.")
        return handle_roleplay_message(user_message, conversation_history)
        

        
    # 3. Default to the standard query handler for all other requests
    print("🚦 ROUTER: Defaulting to Structured Query Handler.")
    return handle_structured_query(user_message, conversation_history)


def _determine_routing_context(channel_context: Optional[Dict]) -> Dict:
    """
    Determine whether to route to roleplay or standard handler.
    
    SIMPLIFIED LOGIC: Only route to roleplay when actively in a roleplay state.
    """
    try:
        # Get current roleplay state
        rp_state = get_roleplay_state()
        
        # SIMPLIFIED: Only route to roleplay if actively in roleplay state
        if rp_state.is_roleplaying:
            return {
                'mode': 'roleplay',
                'reasoning': 'Active roleplay state detected'
            }
        
        # All other cases go to standard handler
        return {
            'mode': 'standard',
            'reasoning': 'Not in active roleplay - using standard handler'
        }
        
    except Exception as e:
        print(f"      ⚠️  Error determining routing context: {e}")
        return {
            'mode': 'standard',
            'reasoning': f'Error fallback - using standard: {e}'
        }


def _route_to_roleplay_handler(user_message: str, conversation_history: List, channel_context: Dict) -> ResponseDecision:
    """Route to roleplay handler."""
    try:
        print(f"   🎭 ROUTING TO ROLEPLAY HANDLER")
        print(f"      Mode: Quick response for roleplay flow")
        
        return handle_roleplay_message(user_message, conversation_history, channel_context or {})
        
    except Exception as e:
        print(f"   ❌ ERROR routing to roleplay handler: {e}")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="I'm having difficulty with roleplay processing right now.",
            strategy={
                'approach': 'roleplay_fallback',
                'needs_database': False,
                'reasoning': f'Roleplay handler error: {e}',
                'context_priority': 'safety'
            }
        )


def _route_to_standard_handler(user_message: str, conversation_history: List) -> ResponseDecision:
    """Route to the new structured query handler."""
    try:
        print(f"   💬 ROUTING TO STRUCTURED QUERY HANDLER")
        print(f"      Mode: Comprehensive response with agentic reasoning")
        
        return handle_structured_query(user_message, conversation_history)
        
    except Exception as e:
        print(f"   ❌ ERROR routing to standard handler: {e}")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="I'm having difficulty processing that request right now.",
            strategy={
                'approach': 'general',
                'needs_database': False,
                'reasoning': f'Standard handler error: {e}',
                'context_priority': 'safety'
            }
        )


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
        print(f"   🎭 DGM Controlled Elsie - Processing DGM content for Elsie awareness")
        
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
        
        # Extract the DGM content that Elsie "said"
        elsie_content = dgm_result.get('elsie_content', '')
        
        if not elsie_content:
            print(f"   ⚠️  No DGM content provided - using NO_RESPONSE")
            return ResponseDecision(
                needs_ai_generation=False,
                pre_generated_response="NO_RESPONSE",
                strategy={
                    'approach': 'dgm_controlled_elsie',
                    'needs_database': False,
                    'reasoning': 'DGM controlled Elsie - no content provided',
                    'context_priority': 'none'
                }
            )
        
        print(f"   📝 DGM Content for Elsie: '{elsie_content}'")
        
        # Return the DGM content as Elsie's response so she's aware of it
        # Use roleplay approach so it goes through roleplay context pipeline
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=elsie_content,
            strategy={
                'approach': 'roleplay_dgm_controlled',
                'needs_database': False,
                'reasoning': f'DGM controlled Elsie - content processed for awareness',
                'context_priority': 'roleplay',
                'dgm_controlled': True,
                'original_dgm_content': elsie_content
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


 