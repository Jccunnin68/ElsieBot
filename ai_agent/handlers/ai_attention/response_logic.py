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
    
    CRITICAL: This function should ONLY be called when rp_state.is_roleplaying = True
    Implicit responses and roleplay logic don't apply outside roleplay sessions.
    
    Returns (should_respond, reason)
    """
    # SAFETY CHECK: This function should only be called in roleplay mode
    if not rp_state.is_roleplaying:
        print(f"   ⚠️  WARNING: should_elsie_respond_in_roleplay called when NOT in roleplay mode!")
        return False, "not_in_roleplay"
    
    message_lower = user_message.lower().strip()
    participants = rp_state.get_participant_names()
    is_dgm_session = rp_state.is_dgm_session()
    is_thread_session = rp_state.is_thread_based()
    
    print(f"   🎭 ROLEPLAY RESPONSE CHECK:")
    print(f"      - Participants: {participants}")
    print(f"      - DGM Session: {is_dgm_session}")
    print(f"      - Thread Session: {is_thread_session}")
    
    from .character_tracking import extract_current_speaker
    speaking_character = extract_current_speaker(user_message)
    
    # Universal speaker tracking for all RP messages
    if speaking_character:
        rp_state.add_speaking_character(speaking_character, current_turn)
    
    # 1. Check for clear reasons to LISTEN FIRST
    # This prevents Elsie from responding to her own posts.
    if speaking_character and speaking_character.lower() == 'elsie':
        print(f"   👂 LISTENING: Elsie is the speaker in this post.")
        return False, "elsie_is_speaker"

    # 2. ENHANCED: Check if other character is addressed FIRST (before implicit response check)
    # This prevents false positives when characters are talking to each other
    other_character_addressed = check_if_other_character_addressed(user_message, rp_state)
    if other_character_addressed:
        print(f"   👂 LISTENING: Message directed at '{other_character_addressed}', not Elsie.")
        print(f"      - Character conversation detected: {speaking_character} → {other_character_addressed}")
        return False, "other_character_addressed"

    # 3. Check for DIRECT ADDRESSING of Elsie
    if _is_elsie_directly_addressed(user_message):
        print(f"   🗣️ DIRECT ADDRESSING: Elsie is directly mentioned or addressed.")
        return True, "elsie_directly_addressed"

    # 4. Check for IMPLICIT RESPONSE scenarios (character following up after Elsie addressed them)
    # This is now much more restrictive and accurate
    if rp_state.is_simple_implicit_response(current_turn, user_message):
        print(f"   🗣️ IMPLICIT RESPONSE: Following up on conversation with Elsie.")
        return True, "implicit_response"
    
    # 5. Check for SUBTLE BAR SERVICE scenarios (drink requests, etc.)
    if _is_subtle_bar_service_needed(user_message):
        print(f"   🍺 SUBTLE BAR SERVICE: Service request detected.")
        return True, "subtle_bar_service"
    
    # 6. DEFAULT TO LISTENING for everything else
    # This is the key change - we no longer respond to "substantial messages" just because they exist
    # Elsie should be passive and only respond when directly involved
    print(f"   👂 LISTENING: No direct involvement detected - passive monitoring.")
    return False, "passive_listening"


def _is_elsie_directly_addressed(user_message: str) -> bool:
    """
    Check if Elsie is directly addressed or mentioned by name in the message.
    Enhanced to detect group addressing (everyone, you all, etc.).
    """
    # Patterns for Elsie being addressed directly
    elsie_patterns = [
        r'\belsie\b',              # "Elsie" as a word
        r'\bElsie\b',              # "Elsie" capitalized  
        r'\bbartender\b',          # "bartender"
        r'\bBartender\b',          # "Bartender"
        r'\bhey\s+elsie\b',        # "hey Elsie"
        r'\bhi\s+elsie\b',         # "hi Elsie"
        r'\bhello\s+elsie\b',      # "hello Elsie"
        r'elsie,',                 # "Elsie," with comma
        r'Elsie,',                 # "Elsie," capitalized
        r'"[^"]*elsie[^"]*"',      # Elsie mentioned in dialogue
        r'"[^"]*Elsie[^"]*"',      # Elsie mentioned in dialogue (capitalized)
    ]
    
    # Check for direct Elsie addressing
    for pattern in elsie_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True
    
    # NEW: Group addressing patterns (includes Elsie as part of "everyone")
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
        r'\bgood morning everyone\b',  # "good morning everyone"
        r'\bgood evening everyone\b',  # "good evening everyone"
    ]
    
    for pattern in group_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            print(f"   👥 GROUP ADDRESSING detected: Pattern '{pattern}' matches")
            return True
    
    # Check for emotes addressing Elsie
    emote_addressing_patterns = [
        r'\*[^*]*(?:turns? to|looks? at|speaks? to|addresses?|faces?)\s+(?:the\s+)?(?:bartender|elsie)[^*]*\*',
        r'\*[^*]*(?:approaches?|walks? (?:up )?to|goes? to)\s+(?:the\s+)?(?:bar|bartender|elsie)[^*]*\*',
    ]
    
    for pattern in emote_addressing_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True
    
    return False


def _is_subtle_bar_service_needed(user_message: str) -> bool:
    """
    Check if this message contains a subtle bar service request that should get a response.
    Only responds to clear drink ORDERING actions, not consumption actions.
    FIXED: More specific patterns to avoid false positives from consumption.
    """
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
        
        # FIRST: Check for consumption patterns - exclude these explicitly
        consumption_patterns = [
            r'drinking\s+',           # "*drinking water*"
            r'sips?\s+',             # "*sips his drink*" 
            r'takes?\s+a\s+drink',   # "*takes a drink*"
            r'finishes?\s+drinking', # "*finishes drinking*"
            r'gulps?\s+',            # "*gulps down*"
            r'swallows?\s+',         # "*swallows*"
            r'drinks?\s+(?:his|her|the|some)', # "*drinks his beer*"
            r'consuming\s+',         # "*consuming*"
            r'enjoying\s+(?:a|his|her|the)\s+drink', # "*enjoying a drink*"
            
            # ENHANCED: Roleplay consumption actions that were causing false positives
            r'fills?\s+.*glass.*drinking',      # "*fills a holographic glass to appear to be drinking*"
            r'appears?\s+to\s+be\s+drinking',   # "*appears to be drinking*"
            r'seems?\s+to\s+be\s+drinking',     # "*seems to be drinking*"
            r'pretends?\s+to\s+drink',          # "*pretends to drink*"
            r'mimics?\s+drinking',              # "*mimics drinking*"
            r'holographic.*drinking',           # "*holographic glass to appear to be drinking*"
            r'to\s+appear.*drinking',           # "*to appear to be drinking*"
            r'fills.*(?:glass|cup|mug).*(?:appear|seem).*drink', # Complex fills patterns
        ]
        
        # If consumption pattern detected, this is NOT a service request
        for pattern in consumption_patterns:
            if re.search(pattern, emote_lower):
                print(f"   🚫 CONSUMPTION DETECTED: '{pattern}' in '{emote}' - not a service request")
                return False
        
        # SECOND: Check for clear ORDERING patterns only
        ordering_patterns = [
            # Clear ordering verbs with specific drinks
            r'orders?\s+(?:a\s+)?(?:drink|beer|ale|whiskey|wine|cocktail|beverage)',
            r'asks?\s+for\s+(?:a\s+)?(?:drink|beer|ale|whiskey|wine|cocktail|beverage)', 
            r'requests?\s+(?:a\s+)?(?:drink|beer|ale|whiskey|wine|cocktail|beverage)',
            
            # Service-seeking gestures (must be explicit about wanting service)
            r'signals?\s+(?:for\s+)?(?:a\s+)?(?:drink|service|bartender)',
            r'motions?\s+(?:for\s+)?(?:a\s+)?(?:drink|service|bartender)',
            r'gestures?\s+(?:for\s+)?(?:a\s+)?(?:drink|service|bartender)',
            r'waves?\s+(?:to\s+)?(?:the\s+)?(?:bartender|bar)',
            r'calls?\s+(?:for\s+)?(?:service|bartender)',
            
            # Bar interaction patterns (seeking service)
            r'taps?\s+(?:the\s+)?bar(?:\s+for\s+service)?',
            r'slides?\s+credits?\s+across',
            r'approaches?\s+(?:the\s+)?bar(?:\s+for\s+service)?',
            r'walks?\s+(?:up\s+)?to\s+(?:the\s+)?bar',
        ]
        
        for pattern in ordering_patterns:
            if re.search(pattern, emote_lower):
                print(f"   🍺 ORDERING PATTERN DETECTED: '{pattern}' in '{emote}' - service request")
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
    Enhanced to detect conversation flow between characters.
    Returns the character name if found, empty string if not directed at anyone specific.
    """
    # Get list of known participants (excluding Elsie)
    participants = rp_state.get_participant_names()
    
    # ENHANCED: Check for conversation flow context
    # If this character is responding immediately after another character spoke,
    # they're likely talking to that character
    from .character_tracking import extract_current_speaker
    current_speaker = extract_current_speaker(user_message)
    
    if current_speaker:
        # Get the last speaker from turn history
        last_turn_info = rp_state.get_last_turn_info()
        if last_turn_info and last_turn_info.get('speaker'):
            last_speaker = last_turn_info['speaker']
            
            # If different characters and last speaker wasn't Elsie, likely talking to each other
            if (last_speaker != current_speaker and 
                last_speaker.lower() not in ['elsie', 'elise', 'elsy', 'els'] and
                current_speaker.lower() not in ['elsie', 'elise', 'elsy', 'els']):
                
                # Check if this seems like a response/conversation continuation
                conversation_indicators = [
                    # Direct responses
                    r'\bi\s+(?:still\s+)?(?:fail\s+to\s+see|don\'?t\s+understand|think|believe)',
                    r'\bthat\'?s\s+(?:not|why|how|what)',
                    r'\byou\s+(?:said|mentioned|asked|told)',
                    r'\bwhat\s+you\s+(?:said|mean|did)',
                    
                    # Conversation flow indicators
                    r'\b(?:yes|no|sure|maybe|perhaps|well),?\s',
                    r'\b(?:but|however|although|still),?\s',
                    r'\bi\s+(?:agree|disagree|know|understand)',
                    r'\bthat\'?s\s+(?:true|false|right|wrong|funny|interesting)',
                    
                    # Emotional responses
                    r'\*(?:laughs?|sighs?|smiles?|nods?|shakes?\s+head)\*',
                    r'\*she\s+(?:laughs?|sighs?|smiles?|nods?)',
                ]
                
                message_lower = user_message.lower()
                if any(re.search(pattern, message_lower) for pattern in conversation_indicators):
                    print(f"   💬 CONVERSATION FLOW: {current_speaker} responding to {last_speaker}")
                    return last_speaker
    
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