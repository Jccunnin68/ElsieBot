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
    
    SIMPLIFIED: Only responds when:
    1. Directly mentioned/addressed by name
    2. Implicit response scenarios (following up after addressing someone)
    3. Specific service scenarios
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
    
    # Determine response style based on context - SIMPLIFIED LOGIC
    should_respond, response_reason = should_elsie_respond_in_roleplay(user_message, rp_state, turn_number)
    
    # Enhanced name detection for Elsie (direct addressing)
    elsie_mentioned = _detect_elsie_mentioned(user_message)
    
    # SIMPLIFIED: Only respond if directly involved
    # No more permissive "new session" or other broad triggers
    if should_respond or elsie_mentioned:
        
        # Prioritize the reason for the response
        if elsie_mentioned:
            reason_priority = "mentioned_by_name"
        else:
            # Use the reason from the response logic function
            reason_priority = response_reason

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
    """
    Check if Elsie is mentioned in the message.
    Enhanced to detect group addressing (everyone, you all, etc.).
    """
    # Direct Elsie mentions
    elsie_patterns = [
        r'\belsie\b',
        r'\bElsie\b',
        r'\[Elsie\]',
        r'\[ELSIE\]',
        r'\bbartender\b',
        r'\bBartender\b'
    ]
    
    # Check direct mentions first
    for pattern in elsie_patterns:
        if re.search(pattern, user_message):
            return True
    
    # NEW: Group addressing patterns (Elsie is part of "everyone")
    group_patterns = [
        r'\beveryone\b',           # "everyone"
        r'\bEveryone\b',           # "Everyone"
        r'\beverybody\b',          # "everybody"  
        r'\bEverybody\b',          # "Everybody"
        r'\byou all\b',            # "you all"
        r'\bYou all\b',            # "You all"
        r'\by\'?all\b',            # "y'all" or "yall"
        r'\bY\'?all\b',            # "Y'all" or "Yall"
        r'\byou guys\b',           # "you guys"
        r'\bYou guys\b',           # "You guys"
        r'\bhey everyone\b',       # "hey everyone"
        r'\bhello everyone\b',     # "hello everyone"
        r'\bhello all\b',          # "hello all"
        r'\bhi everyone\b',        # "hi everyone"
        r'\bhi all\b',             # "hi all"
    ]
    
    for pattern in group_patterns:
        if re.search(pattern, user_message):
            print(f"   👥 GROUP MENTION detected: Pattern '{pattern}' - treating as Elsie mentioned")
            return True
    
    return False 