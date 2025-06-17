"""
Standard Handler - Simple Responses and Factual Queries
=======================================================

This module handles ALL responses when Elsie is NOT in roleplay mode.
Provides simple, efficient responses including:
- Basic mock responses for greetings, farewells
- Factual database queries (character info, logs, ship data)
- Comprehensive database responses with disambiguation
- Simple conversational responses
- NO bar/menu functionality (that belongs to roleplay)
- NO character relationship tracking

CRITICAL: This handler is ONLY called when NOT in roleplay mode.
ENHANCED: Comprehensive database responses with summary + disambiguation.
"""

from typing import Dict, List, Optional

from .response_decision import ResponseDecision
from .query_detection import (
     detect_query_type_with_conflicts
)


def handle_standard_message(user_message: str, conversation_history: List) -> ResponseDecision:
    """
    Handle ALL standard mode messages with comprehensive responses.
    
    Standard mode provides:
    - Simple mock responses for basic interactions
    - Comprehensive database queries with disambiguation
    - Basic conversational responses
    - Summary + disambiguation for multiple results
    - NO bar/menu features (roleplay-only)
    - NO character tracking
    
    Args:
        user_message: The user's message
                
    Returns:
        ResponseDecision with appropriate strategy
    """
    print(f"\n💬 STANDARD HANDLER - Comprehensive response mode")
    
    # PRIORITY 1: Check for simple mock responses first (before query detection)
    # This handles greetings, farewells, simple chat, etc.
    simple_mock_response = _check_for_simple_mock_response(user_message)
    if simple_mock_response:
        return simple_mock_response
    
    # PRIORITY 2: Use enhanced query detection for database queries
    query_info = detect_query_type_with_conflicts(user_message)
    
    print(f"   📋 Query Analysis: {query_info['type']} - {query_info.get('subject', 'N/A')}")
    
    # Handle special standard cases
    if query_info.get('type') == 'menu_request':
        return _handle_menu_request()
    
    if query_info.get('type') == 'reset_request':
        return _handle_reset_request()
    
    # Handle comprehensive database queries
    database_query_types = ['log', 'general', 'temporal_log']
    if query_info['type'] in database_query_types:
        return _handle_comprehensive_database_query(user_message, query_info)
    
    # Default: simple conversational response
    return _handle_default_conversational(user_message)


def _handle_comprehensive_database_query(user_message: str, query_info: Dict) -> ResponseDecision:
    """
    Comprehensive database query for standard contexts.
    Maps simplified query types to context builder approaches.
    """
    query_type = query_info['type']
    
    # Map simple types to approaches
    if query_type == 'temporal_log':
        approach = 'temporal_logs'
    elif query_type == 'log':
        approach = 'logs'
    else:
        approach = 'comprehensive'
    
    print(f"   📚 COMPREHENSIVE DATABASE QUERY: {query_type} -> Approach: {approach}")
    
    strategy = {
        'approach': approach,
        'needs_database': True,
        'query_type': query_type,
        'subject': query_info.get('subject'),
        'context_priority': 'factual',
        'reasoning': f"Standard comprehensive database query: {query_type} - {query_info.get('subject', 'N/A')}"
    }
    
    # Add temporal-specific parameters
    if query_type == 'temporal_log':
        strategy['temporal_type'] = query_info.get('temporal_type')
        strategy['ship_name'] = query_info.get('ship_name')
        print(f"      ⏰ Temporal parameters: type={strategy['temporal_type']}, ship={strategy['ship_name']}")
    
    # Add disambiguation requirements for "general" queries that act like "tell_me_about"
    if query_type == 'general':
        strategy['needs_title_fallback'] = True
        strategy['provide_disambiguation'] = True
        strategy['include_summary'] = True
        print(f"      📋 Disambiguation enabled for general query")

    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
        strategy=strategy
    )





def _handle_menu_request() -> ResponseDecision:
    """Handle menu requests in standard mode."""
    from handlers.ai_emotion.drink_menu import get_menu_response
    
    print(f"   📋 MENU REQUEST: Standard menu")
    
    menu_response = get_menu_response()
    
    strategy = {
        'approach': 'menu_request',
        'needs_database': False,
        'reasoning': 'Menu request in standard mode',
        'context_priority': 'none'
    }
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=menu_response,
        strategy=strategy
    )


def _handle_reset_request() -> ResponseDecision:
    """Handle reset requests."""
    from handlers.ai_emotion import get_reset_response
    
    print(f"   🔄 RESET REQUEST")
    
    reset_response = get_reset_response()
    
    strategy = {
        'approach': 'reset',
        'needs_database': False,
        'reasoning': 'Reset request',
        'context_priority': 'none'
    }
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=reset_response,
        strategy=strategy
    )


def _handle_default_conversational(user_message: str) -> ResponseDecision:
    """Handle default conversational responses."""
    from handlers.ai_emotion.personality_contexts import is_simple_chat
    
    if is_simple_chat(user_message):
        # Simple mock response
        from handlers.ai_emotion.mock_responses import get_mock_response
        mock_response = get_mock_response(user_message)
        
        strategy = {
            'approach': 'simple_chat',
            'needs_database': False,
            'reasoning': 'Simple conversational response',
            'context_priority': 'none'
        }
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=mock_response,
            strategy=strategy
        )
    else:
        # General AI response with light context
        strategy = {
            'approach': 'general',
            'needs_database': True,
            'reasoning': 'General conversational response with light context',
            'context_priority': 'low'
        }
        
        return ResponseDecision(
            needs_ai_generation=True,
            pre_generated_response=None,
            strategy=strategy
        )


def _check_for_simple_mock_response(user_message: str) -> Optional[ResponseDecision]:
    """
    Check if this message should get a simple mock response.
    Returns ResponseDecision if it should use mock, None otherwise.
    
    This handles:
    - Greetings (hello, hi, etc.)
    - Farewells (bye, goodbye, etc.)
    - Status inquiries (how are you, etc.)
    - Simple chat (yes, no, thanks, etc.)
    - Menu requests
    - Drink orders
    - Federation archives requests
    """
    from handlers.ai_emotion.mock_responses import is_mock_response_appropriate, get_mock_response
    from handlers.ai_emotion.personality_contexts import is_simple_chat
    from handlers.ai_emotion.drink_menu import is_menu_request
    from handlers.ai_logic.query_detection import is_federation_archives_request
    
    # Check if any mock response is appropriate
    if is_mock_response_appropriate(user_message):
        print(f"   🤖 SIMPLE MOCK RESPONSE DETECTED")
        
        # Determine the specific type for better logging
        mock_type = "unknown"
        if is_simple_chat(user_message):
            mock_type = "simple_chat"
        elif is_menu_request(user_message):
            mock_type = "menu_request"
        elif is_federation_archives_request(user_message):
            mock_type = "federation_archives"
        
        print(f"      Type: {mock_type}")
        
        # Get the mock response
        mock_response = get_mock_response(user_message)
        
        strategy = {
            'approach': f'mock_{mock_type}',
            'needs_database': False,
            'reasoning': f'Simple mock response for {mock_type}',
            'context_priority': 'none'
        }
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=mock_response,
            strategy=strategy
        )
    
    return None


