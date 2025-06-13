"""
Decision Extractor - Response Decision Extraction Logic
======================================================

This module contains the logic for extracting response decisions from
message analysis, determining whether AI generation is needed or if
pre-generated responses can be used.
"""

import random
from typing import Dict, Optional

from config import GEMMA_API_KEY
from .response_decision import ResponseDecision
from .strategy_engine import determine_response_strategy

# Import from ai_attention handlers (Phase 6A)
from handlers.ai_attention.character_tracking import extract_character_names_from_emotes
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.response_logic import extract_drink_from_emote as _extract_drink_from_emote
from handlers.ai_emotion import (
    get_reset_response,
    get_simple_continuation_response,
    get_menu_response
)
from handlers.ai_attention.response_logic import should_elsie_respond_in_roleplay


def detect_mock_response_type(user_message: str) -> Optional[str]:
    """
    Detect what type of mock response this message would trigger.
    Returns the mock response type or None if not a mock response.
    """
    from handlers.ai_emotion.drink_menu import handle_drink_request, is_menu_request
    from handlers.ai_emotion.greetings import handle_greeting, handle_farewell, handle_status_inquiry
    from handlers.ai_emotion.personality_contexts import is_simple_chat
    
    # Check each mock response type in order
    try:
        from handlers.ai_logic.query_detection import is_federation_archives_request
        if is_federation_archives_request(user_message):
            return 'federation_archives'  # Keep as-is
    except ImportError:
        archives_patterns = ['federation archives', 'check archives', 'search archives']
        if any(pattern in user_message.lower() for pattern in archives_patterns):
            return 'federation_archives'  # Keep as-is
    
    if is_menu_request(user_message):
        return 'menu'  # EXCLUDED from AI variety
    
    if handle_drink_request(user_message):
        return 'drink_order'  # Enhance with AI
    
    if handle_greeting(user_message):
        return 'greeting'  # Enhance with AI
    
    if handle_status_inquiry(user_message):
        return 'status_inquiry'  # Enhance with AI
    
    if handle_farewell(user_message):
        return 'farewell'  # Enhance with AI
    
    if is_simple_chat(user_message):
        return 'conversational'  # Enhance with AI
    
    return None


def should_enhance_mock_with_ai(mock_type: str, api_key_available: bool, is_roleplay: bool) -> bool:
    """
    Determine if this mock response should be enhanced with AI variety.
    Only applies when in roleplay mode with API key available.
    """
    if not api_key_available or not is_roleplay:
        return False
    
    # Exclude certain types from AI enhancement
    excluded_types = ['federation_archives', 'menu']
    if mock_type in excluded_types:
        return False
    
    # 80% chance for enhancement
    return random.random() < 0.8


def should_use_ai_variety_for_roleplay(api_key_available: bool) -> bool:
    """
    Determine if we should use AI generation for roleplay variety.
    Returns True 80% of the time when API key is available.
    """
    if not api_key_available:
        return False
    return random.random() < 0.8  # 80% chance


def extract_response_decision(user_message: str, conversation_history: list, channel_context: Dict = None) -> ResponseDecision:
    """
    SIMPLIFIED DECISION EXTRACTOR - Now routes to appropriate handlers.
    
    This is the main entry point but the real logic is in:
    - response_router.py (mode detection and routing)
    - roleplay_handler.py (all roleplay mode responses)
    - non_roleplay_handler.py (all non-roleplay mode responses)
    """
    
    print(f"\n🎯 DECISION EXTRACTOR - Routing to appropriate handler")
    
    # Import and use the new router system
    from .response_router import route_message_to_handler
    
    # Route to appropriate handler based on roleplay mode
    return route_message_to_handler(user_message, conversation_history, channel_context)
    
# Legacy functions moved to handlers but kept for any remaining imports
# These should not be called directly anymore - use the router system 