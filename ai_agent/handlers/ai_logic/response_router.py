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
from ..ai_attention import get_roleplay_state
from ..ai_emotion.personality_contexts import is_simple_chat
from ..ai_wisdom.prompt_builder import get_simple_chat_prompt

# Import the specialized handlers
from .roleplay_handler import handle_roleplay_message
from .structured_query_handler import handle_structured_message



def route_message_to_handler(user_message: str, conversation_history: list, channel_context: Dict = None) -> ResponseDecision:
    """
    Routes the user's message to the appropriate handler based on the application's state.
    
    New Simplified Flow:
    1. Check if roleplay is active. If so, ALL messages go to the Roleplay Handler.
    2. For simple conversational messages, route to a chat-focused LLM call.
    3. Default to the standard structured query handler for all other messages.
    """
    rp_state = get_roleplay_state()
    
    # 1. Prioritize active roleplay sessions
    if rp_state.is_roleplaying:
        print("🚦 ROUTER: Roleplay active, routing to Roleplay Handler.")
        return handle_roleplay_message(user_message, conversation_history)
        
    # 2. Handle simple conversational messages
    if is_simple_chat(user_message):
        print("🚦 ROUTER: Simple chat detected, routing to conversational LLM call.")
        return ResponseDecision(
            needs_ai_generation=True,
            pre_generated_response=get_simple_chat_prompt(user_message, conversation_history),
            strategy={
                'approach': 'simple_chat',
                'reasoning': 'Simple conversational message, routing to LLM for chat.'
            }
        )
        
    # 3. Default to the standard query handler for all other requests
    print("🚦 ROUTER: Defaulting to Structured Query Handler.")
    return handle_structured_message(user_message, conversation_history)


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


def is_cross_channel_message(channel_context: Optional[Dict]) -> bool:
    """Check if this message is from a different channel than the current roleplay."""
    rp_state = get_roleplay_state()
    
    if not rp_state.is_roleplaying or not channel_context:
        return False
    
    return not rp_state.is_message_from_roleplay_channel(channel_context)


 