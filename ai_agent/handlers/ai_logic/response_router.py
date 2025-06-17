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
from ..ai_attention.state_manager import get_roleplay_state
from ..ai_attention.dgm_handler import check_dgm_post

# Import the specialized handlers
from .roleplay_handler import handle_roleplay_message, handle_cross_channel_busy
from .structured_query_handler import handle_structured_message


def route_message_to_handler(user_message: str, conversation_history: List, channel_context: Optional[Dict] = None) -> ResponseDecision:
    """
    Enhanced message routing with conflict prevention and context awareness.
    
    Routes messages to appropriate handlers based on:
    1. Roleplay vs non-roleplay context detection
    2. Cross-channel message coordination
    
    Args:
        user_message: The user's input message
        conversation_history: List of previous conversation turns
        channel_context: Optional channel and context information
        
    Returns:
        ResponseDecision with routing decision and strategy
    """
    print(f"\n🚦 RESPONSE ROUTER - Enhanced message routing")
    print(f"   📝 Message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
    
    try:
        # Step 1: Check for DGM actions (takes precedence)
        dgm_result = check_dgm_post(user_message)
        if dgm_result['is_dgm']:
            print(f"   🎬 DGM Action detected: {dgm_result['action']}")
            return _process_dgm_action(dgm_result, user_message, len(conversation_history) + 1, channel_context)
        
        # Step 2: Determine routing context (roleplay vs non-roleplay)
        routing_context = _determine_routing_context(channel_context)
        
        print(f"   🎯 Routing Context: {routing_context['mode']}")
        if routing_context.get('reasoning'):
            print(f"      Reasoning: {routing_context['reasoning']}")
        
        # Step 3: Check for cross-channel messages if in roleplay
        rp_state = get_roleplay_state()
        
        # CLEANUP: Check for auto-exit conditions before routing
        if rp_state.is_roleplaying and rp_state.should_auto_exit_roleplay():
            print(f"   🧹 AUTO-CLEANUP: Ending inactive roleplay session")
            rp_state.auto_exit_roleplay("auto_cleanup_on_query")
            # Re-determine routing context after cleanup
            routing_context = _determine_routing_context(channel_context)
            print(f"   🎯 UPDATED Routing Context: {routing_context['mode']}")
        
        if rp_state.is_roleplaying and routing_context['mode'] == 'roleplay':
            if not rp_state.is_message_from_roleplay_channel(channel_context):
                print(f"   🚫 Cross-channel message detected - returning busy response")
                return handle_cross_channel_busy(rp_state, channel_context)
        
        # Step 4: Route to appropriate handler
        if routing_context['mode'] == 'roleplay':
            return _route_to_roleplay_handler(user_message, conversation_history, channel_context)
        else:
            return _route_to_standard_handler(user_message, conversation_history)
            
    except Exception as e:
        print(f"   ❌ CRITICAL ERROR in response router: {e}")
        print(f"   📋 Traceback: {traceback.format_exc()}")
        
        # Safe fallback
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="I'm having difficulty processing that request right now. Please try again in a moment.",
            strategy={
                'approach': 'general',
                'needs_database': False,
                'reasoning': f'Router error fallback: {str(e)}',
                'context_priority': 'safety'
            }
        )


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
        
        return handle_structured_message(user_message, conversation_history)
        
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


 