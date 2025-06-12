"""
Response Logic for Roleplay
===========================

Contains logic for determining when and how Elsie should respond during roleplay
sessions, including detection of addressing patterns, subtle interactions, and
passive listening behavior.
"""

import re
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .state_manager import RoleplayStateManager



def should_elsie_respond_in_roleplay(user_message: str, rp_state: 'RoleplayStateManager', current_turn: int) -> Tuple[bool, str]:
    """
    Determine if Elsie should actively respond during roleplay or just listen.
    Enhanced for better followup dialogue detection in ongoing sessions.
    Now includes better recognition of when dialogue is directed at other characters.
    STRICT GUARDRAILS: In multi-character scenes, only respond when directly involved.
    SPECIAL DGM MODE: In DGM-initiated sessions, be even more passive until directly addressed.
    Returns (should_respond, reason)
    """
    message_lower = user_message.lower().strip()
    participants = rp_state.get_participant_names()
    is_dgm_session = rp_state.is_dgm_session()
    is_thread_session = rp_state.is_thread_based()
    
    print(f"   🎭 ROLEPLAY RESPONSE CHECK:")
    print(f"      - Participants: {participants}")
    print(f"      - Multi-character scene: {len(participants) > 1}")
    print(f"      - DGM Session: {is_dgm_session}")
    print(f"      - Thread Session: {is_thread_session}")
    
    # AUTO-DETECT: Check if this message contains a speaking character (for DGM sessions)
    # Look for [Character Name] format or character names speaking
    from .character_tracking import extract_current_speaker
    speaking_character = extract_current_speaker(user_message)
    
    # 1. DGM Session Special Handling
    if is_dgm_session:
        # In DGM sessions, only respond when directly addressed
        if speaking_character and speaking_character.lower() == 'elsie':
            print(f"   🎭 DGM SESSION: Directly addressed by {speaking_character}")
            return True, "dgm_direct_address"
        
        # Track speaking character in DGM session
        if speaking_character:
            rp_state.add_speaking_character(speaking_character, current_turn)
        
        print(f"   👂 DGM SESSION: Passive listening mode")
        return False, "dgm_passive_listening"
    
    # 2. Thread Session Special Handling
    if is_thread_session:
        # In thread sessions, be more responsive to substantial messages
        word_count = len(user_message.split())
        if word_count >= 10:  # Substantial message threshold
            # Check if it's not clearly OOC or technical
            non_rp_indicators = ['ooc', 'debug', 'error', 'code', 'script', 'function']
            if not any(indicator in message_lower for indicator in non_rp_indicators):
                print(f"   🧵 THREAD: Substantial message detected ({word_count} words)")
                return True, "thread_substantial_message"
    
    # 3. Direct Address Detection
    if speaking_character and speaking_character.lower() == 'elsie':
        print(f"   🎭 DIRECT ADDRESS: {speaking_character} speaking to Elsie")
        return True, "direct_address"
    
    # 4. Multi-character Scene Handling
    if len(participants) > 1:
        # In multi-character scenes, only respond when directly involved
        if speaking_character and speaking_character.lower() == 'elsie':
            print(f"   👥 MULTI-CHARACTER: Elsie directly addressed")
            return True, "multi_character_direct"
        
        print(f"   👂 MULTI-CHARACTER: Characters talking to each other")
        return False, "multi_character_listening"
    
    # 5. Single Character Scene Handling
    if len(participants) == 1:
        # In single character scenes, be more responsive
        if word_count >= 3:  # Lower threshold for single character
            print(f"   👤 SINGLE CHARACTER: Substantial message")
            return True, "single_character_substantial"
    
    # 6. Default to Listening Mode
    print(f"   👂 Listening mode - no response needed")
    return False, "listening"


def check_subtle_bar_interaction(user_message: str, rp_state: 'RoleplayStateManager') -> bool:
    """
    Check for subtle bar interactions that should get a non-verbal service response.
    These are emotes with no dialogue that involve ordering drinks or bar actions.
    Returns True if Elsie should provide a subtle service response.
    """
    # Subtle bar service is allowed even in DGM sessions - it's non-verbal background service
    
    # Only check emotes (actions in asterisks)
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    
    if not emotes:
        return False
    
    # Check if there's any dialogue in the message (quotes)
    has_dialogue = bool(re.search(r'[""\'"]([^""\'"])+[""\'"]', user_message))
    if has_dialogue:
        return False  # Don't do subtle responses if there's dialogue
    
    # Look for drink ordering patterns in emotes
    for emote in emotes:
        emote_lower = emote.lower()
        
        # Patterns that suggest drink ordering without dialogue
        subtle_bar_patterns = [
            r'orders?\s+(?:a\s+)?([a-zA-Z\s]+)',  # "orders a beer", "orders whiskey"
            r'asks?\s+for\s+(?:a\s+)?([a-zA-Z\s]+)',  # "asks for a drink"
            r'requests?\s+(?:a\s+)?([a-zA-Z\s]+)',  # "requests a cocktail"
            r'signals?\s+for\s+(?:a\s+)?([a-zA-Z\s]+)',  # "signals for a drink"
            r'gestures?\s+for\s+(?:a\s+)?([a-zA-Z\s]+)',  # "gestures for a beer"
            r'points?\s+to\s+(?:the\s+)?([a-zA-Z\s]+)',  # "points to the whiskey"
        ]
        
        for pattern in subtle_bar_patterns:
            if re.search(pattern, emote_lower):
                print(f"      🥃 Subtle bar pattern detected: '{pattern}' in emote: '{emote}'")
                return True
        
        # Simple bar action patterns (without specific drinks)
        # More restrictive patterns - must be explicit ordering actions
        simple_bar_actions = [
            'orders a drink', 'orders something', 'asks for a drink',
            'requests a beverage', 'signals for service',
            'taps the bar', 'slides credits across'
        ]
        
        for action in simple_bar_actions:
            if action in emote_lower:
                print(f"      🥃 Simple bar action detected: '{action}' in emote: '{emote}'")
                return True
        
        # More specific gesture patterns (must include service intent)
        specific_gesture_patterns = [
            'gestures to the bartender', 'gestures for service', 'gestures for a drink',
            'points at the bartender', 'points to the menu', 'waves at the bartender'
        ]
        
        for action in specific_gesture_patterns:
            if action in emote_lower:
                print(f"      🥃 Specific gesture pattern detected: '{action}' in emote: '{emote}'")
                return True
    
    return False


def check_if_other_character_addressed(user_message: str, rp_state: 'RoleplayStateManager') -> str:
    """
    Check if the message is clearly directed at another character (not Elsie).
    Returns the character name if found, empty string if not directed at anyone specific.
    """
    # Get list of known participants (excluding Elsie)
    participants = rp_state.get_participant_names()
    
    # Check for direct addressing patterns with known characters
    addressing_patterns = [
        r'^([A-Z][a-z]+),\s+',  # "Name, ..."
        r'^(?:hey|hi|hello)\s+([A-Z][a-z]+)[,\s]',  # "Hey Name,"
        r'([A-Z][a-z]+),?\s+(?:what do you think|your thoughts|what about you)',  # "Name, what do you think"
        r'(?:what do you think|your thoughts|what about you),?\s+([A-Z][a-z]+)',  # "What do you think, Name"
        r'\*[^*]*(?:turns? to|looks? at|speaks? to|addresses?|faces?)\s+([A-Z][a-z]+)[^*]*\*',  # Emote addressing
    ]
    
    for pattern in addressing_patterns:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            addressed_name = match.group(1)
            # Check if this is a known participant and not Elsie
            if (addressed_name in participants and 
                addressed_name.lower() not in ['elsie', 'elise', 'elsy', 'els']):
                return addressed_name
    
    # Check for bracket format addressing: [Character Name] followed by addressing
    # NOTE: [Character Name] at the start usually indicates the SPEAKER, not who's being addressed
    # Only consider it addressing if there's clear addressing language AFTER the bracket
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if (name in participants and 
            name.lower() not in ['elsie', 'elise', 'elsy', 'els']):
            # Check if there's addressing language after the bracket (not just the bracket itself)
            # Look for patterns like "[Speaker] turns to Character" or "[Speaker] says to Character"
            addressing_after_bracket = re.search(rf'\[{re.escape(name)}\][^[]*(?:turns? to|speaks? to|says? to|addresses?)\s+([A-Z][a-z]+)', user_message, re.IGNORECASE)
            if addressing_after_bracket:
                addressed_character = addressing_after_bracket.group(1)
                if addressed_character in participants and addressed_character.lower() not in ['elsie', 'elise', 'elsy', 'els']:
                    return addressed_character
    
    return ""


def extract_drink_from_emote(user_message: str) -> str:
    """
    Extract the specific drink mentioned in an emote, or return 'drink' if none specified.
    Used for generating subtle bar service responses.
    """
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    
    # Common drink names to look for (order matters - longer names first)
    drink_names = [
        'romulan ale', 'andorian ale', 'blood wine', 'slug-o-cola', 'old fashioned',
        'beer', 'ale', 'lager', 'whiskey', 'whisky', 'bourbon', 'scotch',
        'wine', 'champagne', 'vodka', 'gin', 'rum', 'tequila', 'brandy',
        'cocktail', 'martini', 'manhattan', 'mojito',
        'coffee', 'tea', 'water', 'soda', 'juice', 'milk',
        'synthehol', 'kanar', 'raktajino', 'tranya'
    ]
    
    for emote in emotes:
        emote_lower = emote.lower()
        
        # Look for specific drink names (check longer names first)
        for drink in drink_names:
            if drink in emote_lower:
                return drink
        
        # Look for drink ordering patterns and extract the drink
        drink_patterns = [
            r'orders?\s+(?:a\s+)?([a-zA-Z\s]+)',
            r'asks?\s+for\s+(?:a\s+)?([a-zA-Z\s]+)',
            r'requests?\s+(?:a\s+)?([a-zA-Z\s]+)',
            r'signals?\s+for\s+(?:a\s+)?([a-zA-Z\s]+)',
            r'gestures?\s+for\s+(?:a\s+)?([a-zA-Z\s]+)',
            r'points?\s+to\s+(?:the\s+)?([a-zA-Z\s]+)',
        ]
        
        for pattern in drink_patterns:
            match = re.search(pattern, emote_lower)
            if match:
                potential_drink = match.group(1).strip()
                # Clean up common words but preserve meaningful drink names
                potential_drink = re.sub(r'\b(drink|beverage|something|anything|the|a|an|service)\b', '', potential_drink).strip()
                # Remove extra spaces
                potential_drink = re.sub(r'\s+', ' ', potential_drink).strip()
                if potential_drink and len(potential_drink) > 2:
                    return potential_drink
    
    return 'drink'  # Default if no specific drink found 