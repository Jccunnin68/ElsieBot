"""
Roleplay Strategy Handler
========================

Handles roleplay-specific strategy logic and response determination.
Separated from roleplay detection to avoid circular dependencies.
"""

from typing import Dict, List, Tuple
from .character_tracking import (
    extract_character_names_from_emotes,
    extract_addressed_characters
)
from .state_manager import get_roleplay_state
from .response_logic import should_elsie_respond_in_roleplay
import re

def process_roleplay_strategy(user_message: str, turn_number: int, channel_context: Dict, confidence_score: float, triggers: List[str]) -> Dict[str, any]:
    """
    Process roleplay response logic and determine if Elsie should respond.
    Returns strategy dictionary for roleplay handling.
    """
    rp_state = get_roleplay_state()
    
    # Extract character names for speaker permanence
    character_names = extract_character_names_from_emotes(user_message)
    
    # Extract addressed characters (those being spoken to)
    addressed_characters = extract_addressed_characters(user_message)
    
    # Start new session if not already roleplaying
    if not rp_state.is_roleplaying:
        rp_state.start_roleplay_session(turn_number, triggers, channel_context)
    
    # Add new participants and addressed characters
    for name in character_names:
        rp_state.add_participant(name, "user", turn_number)
    
    for name in addressed_characters:
        rp_state.add_participant(name, "addressed", turn_number)
    
    # Track character turn for simple implicit response logic
    if character_names:
        # Use the first detected character as the speaker
        rp_state.mark_character_turn(turn_number, character_names[0])
    
    # Update confidence tracking
    rp_state.update_confidence(confidence_score)
    
    # Determine response style based on context
    should_respond, response_reason = should_elsie_respond_in_roleplay(user_message, rp_state, turn_number)
    
    # Check if this is a new session (first post in roleplay)
    is_new_session = rp_state.session_start_turn == turn_number
    is_dgm_session = rp_state.is_dgm_session()
    
    # Enhanced name detection for Elsie
    elsie_mentioned = _detect_elsie_mentioned(user_message)
    
    # Respond if:
    # 1. Normal response logic says to respond
    # 2. Elsie is mentioned by name
    # 3. New session AND not a DGM session (regular roleplay should have Elsie greet)
    should_respond_new_session = is_new_session and not is_dgm_session
    
    if should_respond or elsie_mentioned or should_respond_new_session:
        # Active response - preserve subtle_bar_service reason
        if response_reason == "subtle_bar_service":
            reason_priority = response_reason
        else:
            reason_priority = (
                "mentioned_by_name" if elsie_mentioned else
                "new_session" if should_respond_new_session else
                response_reason
            )
        
        rp_state.set_listening_mode(False, reason_priority)
        rp_state.mark_response_turn(turn_number)
        
        return {
            'approach': 'roleplay_active',
            'needs_database': True,  # Enable database for contextual RP queries
            'reasoning': f'Roleplay response - {reason_priority}, participants: {rp_state.get_participant_names()}',
            'context_priority': 'roleplay',
            'roleplay_confidence': confidence_score,
            'roleplay_triggers': triggers,
            'participants': rp_state.get_participant_names(),
            'new_characters': character_names,
            'addressed_characters': addressed_characters,
            'response_reason': reason_priority,
            'elsie_mentioned': elsie_mentioned
        }
    else:
        # Passive listening mode - check if we should interject
        should_interject = rp_state.should_interject_subtle_action(turn_number)
        rp_state.set_listening_mode(True, response_reason)
        
        if should_interject:
            rp_state.mark_interjection(turn_number)
        
        return {
            'approach': 'roleplay_listening',
            'needs_database': False,
            'reasoning': f'Roleplay listening - {response_reason}, tracking: {rp_state.get_participant_names()}',
            'context_priority': 'roleplay_listening',
            'roleplay_confidence': confidence_score,
            'participants': rp_state.get_participant_names(),
            'new_characters': character_names,
            'addressed_characters': addressed_characters,
            'should_interject': should_interject,
            'listening_turn_count': rp_state.listening_turn_count
        }

def _detect_elsie_mentioned(user_message: str) -> bool:
    """Check if Elsie is mentioned in the message."""
    elsie_patterns = [
        r'\belsie\b',
        r'\bElsie\b',
        r'\[Elsie\]',
        r'\[ELSIE\]'
    ]
    return any(re.search(pattern, user_message) for pattern in elsie_patterns) 