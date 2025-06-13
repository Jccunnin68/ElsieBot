"""
Roleplay Handler - All Roleplay Mode Logic
==========================================

This module handles ALL responses when Elsie is in roleplay mode.
Provides rich, character-aware responses with full feature set including:
- Bar service with character knowledge
- Character-aware greetings, farewells, status responses  
- Full database context via roleplay_contexts.py
- AI-generated responses with relationship awareness

CRITICAL: This handler is ONLY called when in roleplay mode.
"""

import random
from typing import Dict, List, Optional

from .response_decision import ResponseDecision
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.character_tracking import extract_character_names_from_emotes
from handlers.ai_attention.response_logic import should_elsie_respond_in_roleplay
from config import GEMMA_API_KEY


def handle_roleplay_message(user_message: str, conversation_history: List, channel_context: Dict) -> ResponseDecision:
    """
    Handle ALL roleplay mode messages with full character-aware features.
    
    Roleplay mode provides:
    - Character-aware greetings ("Welcome back, Maeve!")
    - Bar service with relationships ("Here's your usual, Commander")
    - Menu interactions in roleplay context
    - Full database context for roleplay queries
    - Rich AI-generated responses
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation turns  
        channel_context: Channel information
        
    Returns:
        ResponseDecision with roleplay strategy
    """
    print(f"\n🎭 ROLEPLAY HANDLER - Processing roleplay message")
    
    rp_state = get_roleplay_state()
    turn_number = len(conversation_history) + 1
    
    # Handle cross-channel messages (busy responses)
    if not rp_state.is_message_from_roleplay_channel(channel_context):
        return _handle_cross_channel_busy(rp_state, channel_context)
    
    # Update activity for roleplay channel messages
    rp_state.update_roleplay_channel_activity()
    
    # Track character turns
    character_names = extract_character_names_from_emotes(user_message)
    if character_names:
        rp_state.mark_character_turn(turn_number, character_names[0])
    
    # Determine if Elsie should respond and how
    should_respond, response_reason = should_elsie_respond_in_roleplay(
        user_message, rp_state, turn_number
    )
    
    if not should_respond:
        return _handle_roleplay_no_response(response_reason)
    
    # Detect response type for roleplay
    response_type = detect_roleplay_response_type(user_message)
    
    print(f"   🎭 Roleplay Response Type: {response_type}")
    print(f"   🎯 Response Reason: {response_reason}")
    
    # ALL roleplay responses use AI generation with character context
    # This ensures greetings, drink orders, etc. are character-aware
    strategy = build_roleplay_strategy(
        user_message, response_type, response_reason, rp_state, turn_number, channel_context
    )
    
    # Check for AI variety enhancement (80% chance in roleplay)
    if response_type in ['greeting', 'drink_order', 'farewell', 'status_inquiry', 'conversational']:
        if should_use_ai_variety_for_roleplay():
            print(f"   ✨ AI VARIETY ENHANCED: {response_type} with full roleplay context")
            strategy['ai_variety_type'] = response_type
            strategy['approach'] = 'roleplay_mock_enhanced'
    
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
        strategy=strategy
    )


def detect_roleplay_response_type(user_message: str) -> str:
    """
    Detect what type of roleplay response is needed.
    All types get character-aware treatment in roleplay mode.
    """
    from handlers.ai_emotion.greetings import handle_greeting, handle_farewell, handle_status_inquiry
    from handlers.ai_emotion.drink_menu import handle_drink_request, is_menu_request
    from handlers.ai_emotion.personality_contexts import is_simple_chat
    
    # Check response types in priority order
    if handle_greeting(user_message):
        return 'greeting'
    elif handle_drink_request(user_message):
        return 'drink_order'  
    elif is_menu_request(user_message):
        return 'menu_request'
    elif handle_farewell(user_message):
        return 'farewell'
    elif handle_status_inquiry(user_message):
        return 'status_inquiry'
    elif is_simple_chat(user_message):
        return 'conversational'
    else:
        return 'roleplay_active'


def build_roleplay_strategy(user_message: str, response_type: str, response_reason: str, 
                           rp_state, turn_number: int, channel_context: Dict) -> Dict:
    """
    Build strategy for roleplay responses.
    Always includes full roleplay context and character awareness.
    """
    from handlers.ai_attention.roleplay_detection import detect_roleplay_triggers
    
    # Get roleplay triggers and confidence
    is_roleplay, confidence_score, triggers = detect_roleplay_triggers(user_message, channel_context)
    
    # Build comprehensive roleplay strategy
    strategy = {
        'approach': 'roleplay_active',
        'needs_database': True,  # Always use database for roleplay context
        'reasoning': f'Roleplay {response_type} - {response_reason}',
        'context_priority': 'roleplay',
        
        # Roleplay context information
        'participants': rp_state.get_participant_names(),
        'new_characters': _extract_new_characters(user_message, rp_state),
        'addressed_characters': _extract_addressed_characters(user_message),
        'roleplay_confidence': confidence_score,
        'roleplay_triggers': triggers,
        'response_reason': response_reason,
        'elsie_mentioned': _is_elsie_mentioned(user_message),
        
        # Character knowledge preservation
        'preserve_character_knowledge': True,
        'use_full_roleplay_context': True,
        
        # Response type context
        'response_type': response_type
    }
    
    # Mark Elsie's response turn
    rp_state.mark_response_turn(turn_number)
    
    return strategy


def should_use_ai_variety_for_roleplay() -> bool:
    """
    Determine if we should use AI generation for roleplay variety.
    Returns True 80% of the time when API key is available.
    """
    if not GEMMA_API_KEY:
        return False
    return random.random() < 0.8


def _handle_cross_channel_busy(rp_state, channel_context: Dict) -> ResponseDecision:
    """Handle messages from different channels during roleplay."""
    channel_info = rp_state.get_roleplay_channel_info()
    busy_message = f"I am currently roleplaying in {channel_info['channel_name']}. Please try again later or join that thread."
    
    # Check if this is a DM
    if channel_context and channel_context.get('type', '').lower() in ['dm', 'group_dm']:
        busy_message = f"I am currently roleplaying in {channel_info['channel_name']}. DM interactions are paused during roleplay sessions."
    
    print(f"   🚫 CROSS-CHANNEL BUSY: Returning busy signal")
    
    strategy = {
        'approach': 'cross_channel_busy',
        'needs_database': False,
        'reasoning': f'Cross-channel message while roleplaying in {channel_info["channel_name"]}',
        'context_priority': 'none',
        'busy_message': busy_message,
        'roleplay_channel': channel_info['channel_name']
    }
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=busy_message,
        strategy=strategy
    )


def _handle_roleplay_no_response(response_reason: str) -> ResponseDecision:
    """Handle cases where Elsie shouldn't respond in roleplay."""
    if response_reason == 'listening_mode':
        # Subtle presence responses during listening
        interjection_responses = [
            "*quietly tends to the bar in the background*",
            "*adjusts the ambient lighting subtly*", 
            "*continues her work with practiced efficiency*",
            "*maintains the bar's atmosphere unobtrusively*"
        ]
        
        # 20% chance of subtle interjection during listening
        if random.random() < 0.2:
            return ResponseDecision(
                needs_ai_generation=False,
                pre_generated_response=random.choice(interjection_responses),
                strategy={'approach': 'roleplay_listening_interjection'}
            )
    
    # Most cases: complete silence
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response="NO_RESPONSE",
        strategy={'approach': 'roleplay_no_response', 'reasoning': response_reason}
    )


def _extract_new_characters(user_message: str, rp_state) -> List[str]:
    """Extract any new characters mentioned in this message."""
    character_names = extract_character_names_from_emotes(user_message)
    existing_participants = [p.lower() for p in rp_state.get_participant_names()]
    
    new_characters = []
    for name in character_names:
        if name.lower() not in existing_participants:
            new_characters.append(name)
            rp_state.add_participant(name, "mentioned", len(rp_state.turn_history) + 1)
    
    return new_characters


def _extract_addressed_characters(user_message: str) -> List[str]:
    """Extract characters being addressed in the message."""
    from handlers.ai_attention.character_tracking import extract_addressed_characters
    return extract_addressed_characters(user_message)


def _is_elsie_mentioned(user_message: str) -> bool:
    """Check if Elsie is directly mentioned or addressed."""
    elsie_names = ['elsie', 'elise', 'bartender', 'barkeep', 'barmaid']
    message_lower = user_message.lower()
    
    return any(name in message_lower for name in elsie_names) 