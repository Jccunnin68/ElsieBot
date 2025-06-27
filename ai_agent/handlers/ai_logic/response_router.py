"""
Response Router - Routing Logic for AI Responses
===============================================

This module handles the routing logic for determining how to respond to user messages,
including roleplay state management and cross-channel busy signals.
All responses go through the LLM with appropriate contextual information.
"""

from typing import Optional, Dict, Any

# Import services from service container
from ..service_container import get_roleplay_state, get_context_analysis_service


def route_message(user_message: str, channel_context: Optional[Dict[str, Any]] = None) -> str:
    """
    Route incoming messages to appropriate handlers based on current state.
    
    This is the main entry point for message routing logic.
    All responses go through the LLM with appropriate context.
    """
    # Get services
    rp_state = get_roleplay_state()
    context_service = get_context_analysis_service()
    
    # Check if Elsie is mentioned (to wake her up in channels she's not monitoring)
    if context_service.detect_elsie_mention(user_message):
        print("   👋 ELSIE MENTIONED - Processing message")
    
    # CRITICAL FIX: Check for DGM posts FIRST, before roleplay routing decisions
    # This allows DGM posts to initiate roleplay sessions even when not currently in roleplay
    from ..ai_attention.dgm_handler import check_dgm_post
    dgm_result = check_dgm_post(user_message)
    if dgm_result and dgm_result.get('is_dgm'):
        print(f"   🎬 DGM POST DETECTED - Routing to roleplay handler")
        print(f"   🎯 DGM Action: {dgm_result.get('action')}")
        print(f"   🎭 Triggers Roleplay: {dgm_result.get('triggers_roleplay')}")
        return _handle_roleplay_message_properly(user_message, [], channel_context)  # DGM posts always go to roleplay handler
    
    # Check roleplay state and handle cross-channel scenarios
    if rp_state.is_roleplaying:
        if channel_context and not rp_state.is_message_from_roleplay_channel(channel_context):
            return handle_cross_channel_busy(rp_state, channel_context)
        return _handle_roleplay_message_properly(user_message, [], channel_context)  # conversation_history would be passed from caller
    
    # Route to standard handler for non-roleplay scenarios
    return handle_standard_message(user_message)


def handle_cross_channel_busy(rp_state, channel_context: Dict[str, Any]) -> str:
    """
    Handle cross-channel messages when Elsie is busy roleplaying in another channel.
    """
    current_channel = rp_state.current_roleplay_channel
    busy_message = f"*interface flickers briefly* I'm currently engaged in roleplay in #{current_channel}. "
    busy_message += "I'll be available for other interactions once that session concludes."
    return busy_message


def _handle_roleplay_message_properly(user_message: str, conversation_history: list, channel_context: Dict = None) -> str:
    """
    Handle messages during roleplay sessions using the correct roleplay handler.
    This calls the proper roleplay handler that handles DGM commands first.
    """
    try:
        # Use the proper roleplay handler from roleplay_handler.py
        from .roleplay_handler import handle_roleplay_message as proper_roleplay_handler
        
        # The proper handler returns a ResponseDecision, so we need to process it
        decision = proper_roleplay_handler(user_message, conversation_history, channel_context)
        
        # If no AI generation needed, return the pre-generated response
        if not decision.needs_ai_generation:
            response = decision.pre_generated_response
            # FIXED: Return "NO_RESPONSE" as-is for Discord bot to handle properly
            if response == "NO_RESPONSE":
                return "NO_RESPONSE"  # DGM posts that don't need responses - Discord bot will stay silent
            return response or ""
        
        # Otherwise, generate AI response
        from ..service_container import get_ai_engine
        ai_engine = get_ai_engine()
        return ai_engine.generate_response_with_decision(decision, user_message, conversation_history)
            
    except Exception as e:
        print(f"Error in proper roleplay handler: {e}")
        import traceback
        traceback.print_exc()
        return "I'm experiencing some technical difficulties during roleplay. Please try again in a moment."


def handle_roleplay_message(user_message: str, conversation_history: list) -> str:
    """
    Handle messages during roleplay sessions.
    All roleplay messages go through the LLM with roleplay context.
    
    DEPRECATED: This function is kept for backwards compatibility but should not be used.
    Use _handle_roleplay_message_properly instead.
    """
    # Import services from service container
    from ..service_container import get_attention_engine, get_ai_engine
    
    try:
        # Use attention engine to determine roleplay strategy
        attention_engine = get_attention_engine()
        strategy = attention_engine.determine_response_strategy(
            user_message, 
            conversation_history or [], 
            None  # roleplay state will be checked internally
        )
        
        # Always use AI engine for roleplay - no mocking
        ai_engine = get_ai_engine()
        if hasattr(ai_engine, 'generate_ai_response'):
            return ai_engine.generate_ai_response(user_message, strategy, conversation_history)
        else:
            # Fallback if method name is different
            return ai_engine.generate_response_with_strategy(user_message, strategy, conversation_history)
            
    except Exception as e:
        print(f"Error in roleplay handler: {e}")
        import traceback
        traceback.print_exc()
        return "I'm experiencing some technical difficulties during roleplay. Please try again in a moment."


def handle_standard_message(user_message: str) -> str:
    """
    Handle standard (non-roleplay) messages.
    All messages go through the LLM with appropriate contextual information.
    """
    # Import services from service container
    from ..service_container import get_ai_engine
    
    try:
        # Detect contextual information to pass to LLM
        context_info = _detect_message_context(user_message)
        
        # Build strategy with contextual information
        strategy = {
            'approach': 'simple_chat',
            'context_type': context_info['type'],
            'personality_context': context_info['personality'],
            'prompt_hints': context_info['hints'],
            'needs_ai_generation': True
        }
        
        # Always use AI engine - no mocking responses
        ai_engine = get_ai_engine()
        if hasattr(ai_engine, 'generate_ai_response'):
            return ai_engine.generate_ai_response(user_message, strategy, [])
        else:
            # Fallback if method name is different
            return ai_engine.generate_response_with_strategy(user_message, strategy, [])
        
    except Exception as e:
        print(f"Error in standard handler: {e}")
        import traceback
        traceback.print_exc()
        return "I'm experiencing some technical difficulties. Please try again in a moment."


def _detect_message_context(user_message: str) -> Dict[str, Any]:
    """
    Detect contextual information about the message to inform LLM processing.
    
    Returns:
        Dictionary with context type, personality, and prompt hints
    """
    user_lower = user_message.lower().strip()
    
    # Detect greeting patterns
    greeting_patterns = ["hello", "hi", "greetings", "hey", "good morning", "good afternoon", "good evening"]
    is_greeting = any(pattern in user_lower for pattern in greeting_patterns)
    
    # Detect farewell patterns
    farewell_patterns = ["bye", "goodbye", "see you", "farewell", "take care", "goodnight"]
    is_farewell = any(pattern in user_lower for pattern in farewell_patterns)
    
    # Detect drink/bar related patterns
    drink_patterns = ["drink", "beverage", "bar", "alcohol", "cocktail", "wine", "beer", "coffee", "tea"]
    is_drink_related = any(pattern in user_lower for pattern in drink_patterns)
    
    # Detect status inquiry patterns
    status_patterns = ["how are you", "how's it going", "what's up", "how do you feel"]
    is_status_inquiry = any(pattern in user_lower for pattern in status_patterns)
    
    # Detect emotional context
    from ..ai_emotion.personality_contexts import detect_mock_personality_context
    personality_context = detect_mock_personality_context(user_message)
    
    # Build context info
    if is_greeting:
        return {
            'type': 'greeting',
            'personality': personality_context,
            'hints': ['respond_warmly', 'establish_presence', 'invite_interaction']
        }
    elif is_farewell:
        return {
            'type': 'farewell', 
            'personality': personality_context,
            'hints': ['acknowledge_departure', 'warm_closure', 'leave_door_open']
        }
    elif is_drink_related:
        return {
            'type': 'drink_service',
            'personality': 'bartender',
            'hints': ['bartender_mode', 'drink_knowledge', 'service_oriented']
        }
    elif is_status_inquiry:
        return {
            'type': 'status_inquiry',
            'personality': personality_context,
            'hints': ['share_current_state', 'maintain_character', 'engage_conversation']
        }
    else:
        return {
            'type': 'general_chat',
            'personality': personality_context,
            'hints': ['natural_conversation', 'helpful_response', 'maintain_character']
        }