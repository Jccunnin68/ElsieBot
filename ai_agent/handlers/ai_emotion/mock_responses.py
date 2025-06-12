"""
Mock Response Coordinator
========================

This module coordinates all mock responses when the Gemma API is unavailable
or for simple conversational interactions.
"""

from typing import Optional, Dict, Any
import sys
import os


# from handlers.ai_logic.query_detection import is_federation_archives_request  # Moved to local import to prevent circular dependency
from handlers.handlers_utils import convert_earth_date_to_star_trek
from content_retrieval_db import search_memory_alpha

from .personality_contexts import detect_mock_personality_context, is_simple_chat
from .drink_menu import handle_drink_request, get_menu_response, is_menu_request
from .greetings import handle_greeting, handle_farewell, handle_status_inquiry, get_conversational_response
from .poetic_responses import should_trigger_poetic_circuit, get_poetic_response


def should_use_mock_response(user_message: str, api_available: bool = False) -> bool:
    """
    Determine if a mock response should be used instead of calling the AI API.
    
    Args:
        user_message: The user's message
        api_available: Whether the Gemma API is available
        
    Returns:
        True if mock response should be used
    """
    # Always use mock if API is unavailable
    if not api_available:
        return True
    
    # Use mock for simple chat interactions
    if is_simple_chat(user_message):
        return True
    
    # Use mock for drink orders and menu requests
    if handle_drink_request(user_message) or is_menu_request(user_message):
        return True
    
    # Use mock for federation archives requests (they have their own search)
    try:
        from handlers.ai_logic.query_detection import is_federation_archives_request
        if is_federation_archives_request(user_message):
            return True
    except ImportError:
        # Fallback federation archives detection
        archives_patterns = ['federation archives', 'check archives', 'search archives']
        if any(pattern in user_message.lower() for pattern in archives_patterns):
            return True
    
    return False


def get_mock_response(user_message: str, context: Dict[str, Any] = None) -> str:
    """
    Generate a mock response for the user's message.
    
    Args:
        user_message: The user's message
        context: Additional context information
        
    Returns:
        Mock response string
    """
    # Get personality context for the response
    personality_context = detect_mock_personality_context(user_message)
    
    # Check for specific response types in order of priority
    
    # 1. Federation Archives requests (special handling)
    try:
        from handlers.ai_logic.query_detection import is_federation_archives_request
        if is_federation_archives_request(user_message):
            return _handle_federation_archives_request(user_message)
    except ImportError:
        # Fallback federation archives detection
        archives_patterns = ['federation archives', 'check archives', 'search archives']
        if any(pattern in user_message.lower() for pattern in archives_patterns):
            return _handle_federation_archives_request(user_message)
    
    # 2. Menu requests
    if is_menu_request(user_message):
        return get_menu_response()
    
    # 3. Drink orders
    drink_response = handle_drink_request(user_message)
    if drink_response:
        return drink_response
    
    # 4. Greetings
    greeting_response = handle_greeting(user_message, personality_context)
    if greeting_response:
        return greeting_response
    
    # 5. Status inquiries ("how are you")
    status_response = handle_status_inquiry(user_message)
    if status_response:
        return status_response
    
    # 6. Farewells
    farewell_response = handle_farewell(user_message, personality_context)
    if farewell_response:
        return farewell_response
    
    # 7. Check for poetic short circuit (before default conversational)
    if should_trigger_poetic_circuit(user_message, context.get('conversation_history', []) if context else []):
        print("🎭 MOCK POETIC SHORT CIRCUIT TRIGGERED")
        return get_poetic_response(user_message)
    
    # 8. Default conversational response
    conversational_response = get_conversational_response(user_message, personality_context)
    if conversational_response:
        return conversational_response
    
    # 9. Fallback response
    return "*adjusts display with fluid precision* That's intriguing. Tell me more."


def _handle_federation_archives_request(user_message: str) -> str:
    """
    Handle federation archives requests with mock search functionality.
    
    Args:
        user_message: The user's message requesting archives search
        
    Returns:
        Archives search response
    """
    # Extract what they're searching for
    search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
    search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
    if not search_query:
        search_query = "general information"
    
    # Search archives and provide response
    archives_info = search_memory_alpha(search_query, limit=3, is_federation_archives=True)
    
    if archives_info:
        converted_archives_info = convert_earth_date_to_star_trek(archives_info)
        return f"*fingers dance across controls with quiet precision, accessing distant archives*\n\nAccessing federation archives for '{search_query}'...\n\n{converted_archives_info}\n\n*adjusts display with practiced grace* The archives yield their secrets. Would you like me to search for anything else?"
    else:
        return f"*attempts access with fluid motions, then pauses with subtle disappointment*\n\nI've searched the federation archives for '{search_query}', but they don't seem to have information on that topic available.\n\n*adjusts parameters thoughtfully* Perhaps try a different search term, or there may simply be no records of that particular subject."


def get_mock_personality_context(user_message: str) -> str:
    """
    Get the personality context for mock responses.
    
    Args:
        user_message: The user's message
        
    Returns:
        Personality context string
    """
    return detect_mock_personality_context(user_message)


def is_mock_response_appropriate(user_message: str, conversation_history: list = None) -> bool:
    """
    Check if a mock response is appropriate for this message.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation history
        
    Returns:
        True if mock response is appropriate
    """
    # Mock responses are appropriate for:
    # - Simple chat interactions
    # - Drink orders and menu requests
    # - Greetings and farewells
    # - Status inquiries
    # - Federation archives requests
    
    # Check federation archives with local import
    is_archives_request = False
    try:
        from handlers.ai_logic.query_detection import is_federation_archives_request
        is_archives_request = is_federation_archives_request(user_message)
    except ImportError:
        archives_patterns = ['federation archives', 'check archives', 'search archives']
        is_archives_request = any(pattern in user_message.lower() for pattern in archives_patterns)
    
    return (is_simple_chat(user_message) or
            handle_drink_request(user_message) is not None or
            is_menu_request(user_message) or
            handle_greeting(user_message) is not None or
            handle_farewell(user_message) is not None or
            handle_status_inquiry(user_message) is not None or
            is_archives_request) 