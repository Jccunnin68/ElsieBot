"""
Response Logic for Roleplay
===========================

Contains logic for determining when and how Elsie should respond during roleplay
sessions, including detection of addressing patterns, subtle interactions, and
passive listening behavior.
"""

import re
from typing import Tuple, Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from .state_manager import RoleplayStateManager



def should_elsie_respond_in_roleplay(user_message: str, rp_state: 'RoleplayStateManager', current_turn: int) -> Tuple[bool, str]:
    """
    Determine if Elsie should actively respond during roleplay or just listen.
    
    IMPLICIT RESPONSE PATHWAYS:
    
    Pathway 1 (Single Character):
    - Character Addresses Elsie → Elsie Addresses Character → Character Responds → Elsie Responds (no break)
    
    Pathway 2 (Multi-Character):
    - Character Addresses Elsie → Elsie Addresses Character → Character Responds → Elsie Responds
    - Continue chain UNLESS: Character 2 addresses Elsie explicitly, Character 1 addresses Character 2 explicitly, or Character walks away
    
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
    
    # Get speaking character from current message
    from .character_tracking import extract_current_speaker
    speaking_character = extract_current_speaker(user_message)
    
    print(f"      - Speaking Character: {speaking_character}")
    print(f"      - Last Character Elsie Addressed: {rp_state.last_character_elsie_addressed}")
    print(f"      - Turn History: {rp_state.turn_history[-3:] if len(rp_state.turn_history) >= 3 else rp_state.turn_history}")
    
    # 1. DGM Session Special Handling (unchanged)
    if is_dgm_session:
        if speaking_character and speaking_character.lower() == 'elsie':
            print(f"   🎭 DGM SESSION: Directly addressed by {speaking_character}")
            return True, "dgm_direct_address"
        
        if speaking_character:
            rp_state.add_speaking_character(speaking_character, current_turn)
        
        print(f"   👂 DGM SESSION: Passive listening mode")
        return False, "dgm_passive_listening"
    
    # 2. Direct Address Detection (always respond)
    if _is_elsie_directly_addressed(user_message, speaking_character):
        print(f"   🎭 DIRECT ADDRESS: Elsie directly addressed")
        return True, "direct_address"
    
    # 3. Check for explicit redirection (breaks implicit chain)
    redirection_target = _check_explicit_redirection(user_message, participants)
    if redirection_target:
        print(f"   🔄 EXPLICIT REDIRECTION: Conversation redirected to {redirection_target}")
        return False, "explicit_redirection"
    
    # 4. Check for walk-away emotes (breaks implicit chain)
    if _check_walk_away_emote(user_message):
        print(f"   🚶 WALK AWAY: Character walking away detected")
        return False, "character_walking_away"
    
    # 5. IMPLICIT RESPONSE LOGIC - The core fix
    is_implicit = rp_state.is_simple_implicit_response(current_turn, user_message)
    if is_implicit:
        # Pathway 1: Single Character - Always respond
        if len(participants) <= 1:
            print(f"   💬 PATHWAY 1 (SINGLE): Implicit response - always respond")
            return True, "implicit_single_character"
        
        # Pathway 2: Multi-Character - Respond unless redirected (already checked above)
        else:
            print(f"   💬 PATHWAY 2 (MULTI): Implicit response - continuing conversation chain")
            return True, "implicit_multi_character"
    
    # 6. Thread Session Special Handling
    if is_thread_session:
        word_count = len(user_message.split())
        if word_count >= 10:
            non_rp_indicators = ['ooc', 'debug', 'error', 'code', 'script', 'function']
            if not any(indicator in message_lower for indicator in non_rp_indicators):
                print(f"   🧵 THREAD: Substantial message detected ({word_count} words)")
                return True, "thread_substantial_message"
    
    # 7. Single Character Scene - Be responsive
    if len(participants) <= 1:
        word_count = len(user_message.split())
        if word_count >= 1:
            print(f"   👤 SINGLE CHARACTER: Substantial message")
            return True, "single_character_substantial"
    
    # 8. Check for subtle bar interactions
    if check_subtle_bar_interaction(user_message, rp_state):
        print(f"   🥃 SUBTLE BAR SERVICE: Non-verbal drink order detected")
        return True, "subtle_bar_service"
    
    # 9. Default to Listening Mode
    print(f"   👂 LISTENING MODE: No response needed")
    return False, "listening"


def _is_elsie_directly_addressed(user_message: str, speaking_character: str) -> bool:
    """Check if Elsie is directly addressed in the message."""
    # Check if Elsie is the speaking character (direct address)
    if speaking_character and speaking_character.lower() == 'elsie':
        return True
    
    # Check for explicit addressing patterns
    elsie_patterns = [
        r'\belsie\b', r'\bElsie\b', r'\[Elsie\]', r'\[ELSIE\]',
        r'\bbartender\b', r'\bbarkeep\b', r'\bbarmaid\b'
    ]
    
    for pattern in elsie_patterns:
        if re.search(pattern, user_message):
            return True
    
    return False


def _check_explicit_redirection(user_message: str, participants: List[str]) -> str:
    """
    Check if the message explicitly redirects conversation to another character.
    Returns the character name if redirection found, empty string otherwise.
    """
    # Direct addressing patterns
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
    
    return ""


def _check_walk_away_emote(user_message: str) -> bool:
    """Check if the message contains walk-away emotes that break conversation."""
    walk_away_patterns = [
        r'\*[^*]*(?:walks? away|leaves?|exits?|departs?|turns? and walks?|heads? (?:to|for|toward))[^*]*\*',
        r'\*[^*]*(?:storms? (?:off|out)|stalks? (?:off|away)|hurries? (?:off|away))[^*]*\*',
        r'\*[^*]*(?:moves? away|steps? away|backs? away|retreats?)[^*]*\*'
    ]
    
    for pattern in walk_away_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True
    
    return False


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