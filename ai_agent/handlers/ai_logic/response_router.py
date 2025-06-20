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
from ..service_container import get_roleplay_state
from ..ai_emotion.personality_contexts import is_simple_chat
from ..ai_wisdom.prompt_builder import get_simple_chat_prompt
from .context_detection import detect_elsie_mention

# Specialized handlers imported lazily to avoid circular imports



def route_message_to_handler(user_message: str, conversation_history: list, channel_context: Dict = None) -> ResponseDecision:
    """
    Routes the user's message to the appropriate handler based on the application's state.
    
    New Simplified Flow:
    1. Check for DGM commands first to allow scene control.
    2. Check if roleplay is active. If so, ALL messages go to the Roleplay Handler.
    3. If not in roleplay, check for channel activation.
    4. For simple conversational messages, route to a chat-focused LLM call.
    5. Default to the standard structured query handler for all other messages.
    """
    # Lazy imports to avoid circular dependencies
    from .roleplay_handler import handle_roleplay_message
    from .structured_query_handler import handle_structured_message
    from ..ai_attention.dgm_handler import handle_dgm_command
    
    # 1. Check for DGM commands FIRST to short-circuit all other logic
    dgm_decision = handle_dgm_command(user_message)
    if dgm_decision:
        print("🚦 ROUTER: DGM command detected, routing to DGM Handler.")
        return dgm_decision

    rp_state = get_roleplay_state()
    
    # 2. Prioritize active roleplay sessions
    if rp_state.is_roleplaying:
        # Check if this message is from a different channel than the active roleplay
        if channel_context and not rp_state.is_message_from_roleplay_channel(channel_context):
            print("🚦 ROUTER: Cross-channel message during roleplay - sending busy signal.")
            from .roleplay_handler import handle_cross_channel_busy
            return handle_cross_channel_busy(rp_state, channel_context)
        
        print("🚦 ROUTER: Roleplay active, routing to Roleplay Handler.")
        return handle_roleplay_message(user_message, conversation_history)
        
    # 3. NEW: In non-roleplay, check for channel activation
    channel_id = channel_context.get('channel_id') if channel_context else None
    if not channel_id:
        # If we have no channel context, we can't enforce the rule.
        # Default to old behavior but log a warning.
        print("⚠️ ROUTER: No channel ID found, cannot enforce mention-to-activate rule. Processing message.")
    else:
        is_activated = rp_state.is_channel_activated(channel_id)
        is_mention = detect_elsie_mention(user_message)

        # If channel is not active and this message doesn't activate it, ignore.
        if not is_activated and not is_mention:
            print(f"🚦 ROUTER: Ignoring message in inactive channel ({channel_id}). Waiting for mention.")
            return ResponseDecision.no_response(f"Ignoring message in inactive channel {channel_id}.")

        # If this message is the activation, mark the channel as active.
        if is_mention and not is_activated:
            print(f"🚦 ROUTER: Elsie mentioned. Activating channel ({channel_id}).")
            rp_state.activate_channel(channel_id)

    # 4. Handle simple conversational messages
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
        
    # 5. Default to the standard query handler for all other requests
    print("🚦 ROUTER: Defaulting to Structured Query Handler.")
    return handle_structured_message(user_message, conversation_history)


# REMOVED: All unused routing helper functions
# The route_message_to_handler() function now implements all routing logic directly