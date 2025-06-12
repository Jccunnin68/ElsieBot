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

from .character_tracking import is_valid_character_name


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
    
    print(f"   🎭 ROLEPLAY RESPONSE CHECK:")
    print(f"      - Participants: {participants}")
    print(f"      - Multi-character scene: {len(participants) > 1}")
    print(f"      - DGM Session: {is_dgm_session}")
    
    # AUTO-DETECT: Check if this message contains a speaking character (for DGM sessions)
    # Look for [Character Name] format or character names speaking
    from .character_tracking import extract_current_speaker
    speaking_character = extract_current_speaker(user_message)
    if speaking_character and speaking_character not in participants:
        rp_state.add_speaking_character(speaking_character, len(rp_state.confidence_history) + 1)
        participants = rp_state.get_participant_names()  # Refresh the list
        print(f"   🗣️ AUTO-DETECTED SPEAKING CHARACTER: {speaking_character}")
    
    # 1. PRIORITY CHECK: Check for "Thanks Elsie, [then addressing another character]" pattern FIRST
    # This should get a subtle acknowledgment even if another character is addressed after
    acknowledgment_then_redirect_patterns = [
        r'^(?:thanks?|thank you|cheers)\s+elsie[,.]?\s+(?:so\s+)?([A-Z][a-z]+)(?:\s+what|\s+can|\s+do|\s+how)',  # "Thanks Elsie, so John what..." or "Thanks Elsie, John can..."
        r'(?:thanks?|thank you|cheers)\s+elsie[,.]?\s+(?:so\s+)?([A-Z][a-z]+)(?:\s+what|\s+can|\s+do|\s+how)',  # "Well thanks Elsie, so John what..."
    ]
    
    for pattern in acknowledgment_then_redirect_patterns:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            other_character = match.group(1)
            # Verify this is a valid character name and not a common word
            if is_valid_character_name(other_character) and other_character.lower() not in ['that', 'this', 'what', 'how', 'when', 'where', 'why']:
                print(f"   🙏 Acknowledgment + redirect pattern detected: Thanks to Elsie, then addressing '{other_character}'")
                return True, f"acknowledgment_then_redirect_to_{other_character}"
    
    # 2. Check if this dialogue is directed at another character (but not acknowledgment + redirect)
    # If so, Elsie should NOT respond - let that character respond first
    other_character_addressed = check_if_other_character_addressed(user_message, rp_state)
    if other_character_addressed:
        print(f"   🤐 Dialogue directed at other character: '{other_character_addressed}' - Elsie should wait")
        return False, f"dialogue_for_{other_character_addressed}"
    
    # 3. Always respond if directly addressed by name (including variations)
    # Check for direct addressing patterns that indicate speaking TO Elsie, not ABOUT her
    
    # Direct addressing patterns (speaking TO Elsie)
    direct_addressing_patterns = [
        # Name variations at start or with punctuation
        r'^elsie[,!?]?\s',  # "Elsie," "Elsie!" "Elsie?"
        r'\belsie[,!?]\s',  # "Hey Elsie," "Well Elsie!"
        r'^(?:hey|hi|hello)\s+elsie\b',  # "Hey Elsie"
        r'\belsie\s*$',  # "Elsie" at end
        
        # Bartender addressing (but not just mentioning)
        r'^bartender[,!?]?\s',  # "Bartender," "Bartender!"
        r'\bbartender[,!?]\s',  # "Hey bartender,"
        r'^(?:hey|hi|hello)\s+bartender\b',  # "Hey bartender"
        r'\bbartender\s*$',  # "bartender" at end
        
        # Other addressing terms
        r'^(?:hey you|excuse me|miss|ma\'am)[,!?]?\s',  # "Hey you," "Excuse me,"
        r'\b(?:hey you|excuse me|miss|ma\'am)[,!?]\s',  # "Well, excuse me,"
        
        # Other service terms when used for addressing
        r'^(?:barkeep|barmaid|server|waitress)[,!?]?\s',
        r'\b(?:barkeep|barmaid|server|waitress)[,!?]\s',
    ]
    
    for pattern in direct_addressing_patterns:
        if re.search(pattern, message_lower):
            # Extract the addressing term for logging
            match = re.search(pattern, message_lower)
            addressing_term = match.group(0).strip(' ,!?')
            print(f"   👋 Elsie directly addressed: '{addressing_term}' pattern matched")
            return True, f"addressed_as_{addressing_term}"
    
    # 2. Check for "@Elsie" style mentions (common in Discord/chat)
    mention_patterns = [
        r'@elsie\b',
        r'\belsie[,:]',  # "Elsie," or "Elsie:"
        r'\belsie\?',    # "Elsie?"
        r'\belsie!',     # "Elsie!"
    ]
    
    for pattern in mention_patterns:
        if re.search(pattern, message_lower):
            print(f"   👋 Elsie mention pattern detected: '{pattern}'")
            return True, "mentioned_by_name"
    
    # 3. Check for subtle bar interactions first (non-dialogue drink orders)
    # This happens BEFORE DGM guardrail so bar service works even in DGM sessions
    if check_subtle_bar_interaction(user_message, rp_state):
        print(f"   🥃 Subtle bar interaction detected - Elsie provides service")
        return True, "subtle_bar_service"
    
    # 4. Check for simple implicit response (character Elsie addressed responding back)
    # This should work in both DGM and regular sessions AND multi-character scenes
    # It's natural conversation flow and is targeted to the specific character Elsie addressed
    # PRIORITY: This happens BEFORE multi-character guardrail since it's targeted conversation
    # RETURN IMMEDIATELY: If detected, don't let other logic override this response reason
    if rp_state.is_simple_implicit_response(current_turn, user_message):
        print(f"   💬 Simple implicit response detected - natural conversation flow")
        print(f"   🎯 Multi-character scene: {len(participants) > 1} - implicit response still allowed")
        print(f"   🚀 RETURNING IMMEDIATELY - implicit response takes priority over other checks")
        return True, "simple_implicit_response"
    
    # SPECIAL DGM GUARDRAIL: In DGM-initiated sessions, be EXTREMELY passive
    # Only respond to direct addressing by name - NO other interactions
    # (Subtle bar service and implicit responses are allowed above this check)
    if is_dgm_session:
        print(f"   🎬 DGM SESSION GUARDRAIL: ULTRA-PASSIVE mode - ONLY respond to direct name addressing")
        print(f"   🤐 DGM session: Elsie stays completely quiet unless explicitly addressed by name")
        return False, "dgm_ultra_passive_listening"
    
    # 5. Check for bar-related actions that would naturally involve Elsie (NON-DGM sessions only)
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    
    for emote in emotes:
        emote_lower = emote.lower()
        bar_related = [
            'approaches the bar', 'walks to the bar', 'sits at the bar',
            'looks at the bartender', 'gestures to', 'waves at',
            'turns to the bar', 'faces the bar', 'at the bar'
        ]
        
        for bar_action in bar_related:
            if bar_action in emote_lower:
                print(f"   🍺 Bar-related action detected: '{emote}' - Elsie should respond")
                return True, "bar_interaction"
    
    # STRICT GUARDRAIL: In multi-character scenes, be MUCH more selective
    if len(participants) > 1:
        print(f"   🚧 MULTI-CHARACTER GUARDRAIL ACTIVE - Being very selective")
        
        # Only respond to very explicit group questions or direct commands
        # BUT NOT in DGM sessions - DGM sessions require explicit name addressing
        if not is_dgm_session:
            explicit_group_patterns = [
                r'\b(everyone|everybody|all of you|all)\b.*\?',  # Explicit group questions
                r'^(what does everyone|what do you all|how does everyone)\b',  # Group questions
                r'\b(anyone|anybody)\b.*\?',  # Open questions to anyone
            ]
            
            is_explicit_group = any(re.search(pattern, message_lower) for pattern in explicit_group_patterns)
            
            if is_explicit_group:
                print(f"   👥 Explicit group question detected - Elsie can participate")
                return True, "explicit_group_question"
        
        # In multi-character scenes, don't respond to general conversation
        print(f"   🤐 Multi-character scene: Elsie stays quiet unless directly addressed")
        return False, "multi_character_listening"
    
    # 6. For single-character or new scenes - be more responsive to general dialogue
    # BUT NOT in DGM sessions - DGM sessions require explicit name addressing
    if rp_state.is_roleplaying and len(participants) <= 1 and not is_dgm_session:
        print(f"   👤 Single character scene - More responsive")
        
        # Check if this is a general question (not directed at specific character)
        group_question_patterns = [
            r'^(what|who|when|where|why|how)\b.*\?',  # Questions starting with question words
            r'\b(what do you think|your thoughts)\b',  # Opinion requests
        ]
        
        is_general_question = any(re.search(pattern, message_lower) for pattern in group_question_patterns)
        
        if is_general_question:
            print(f"   💬 General question in single-character scene - Elsie can respond")
            return True, "single_character_question"
        
        # Check for general conversation starters that aren't directed
        conversation_starters = [
            r'^(so|well|now|then)\b',  # Conversation connectors
            r'\b(interesting|fascinating|curious|strange|odd)\b',  # Conversation starters
        ]
        
        is_conversation_starter = any(re.search(pattern, message_lower) for pattern in conversation_starters)
        
        if is_conversation_starter and len(user_message.split()) >= 5:
            print(f"   💬 General conversation starter - Elsie can join")
            return True, "conversation_starter"
    
    # 7. Respond to direct questions or commands directed generally (not at specific characters)
    # BUT NOT in DGM sessions - DGM sessions require explicit name addressing
    if not is_dgm_session:
        direct_patterns = [
            r'^(can you|could you|would you|will you)',
            r'^(please|get|bring|show|tell)',
        ]
        
        for pattern in direct_patterns:
            if re.search(pattern, message_lower):
                print(f"   ❓ Direct general command detected")
                return True, "direct_command"
    
    # 8. Enhanced thread responsiveness - but only for substantial, non-directed messages in single-character scenes
    if len(participants) <= 1 and not is_dgm_session:  # Only in single-character scenes and non-DGM sessions
        channel_context = rp_state.channel_context
        if channel_context:
            is_thread = channel_context.get('is_thread', False)
            channel_type = channel_context.get('type', 'unknown')
            discord_thread_types = ['public_thread', 'private_thread', 'news_thread']
            
            if is_thread or channel_type in discord_thread_types:
                # In threads, only respond to substantial messages that aren't clearly directed
                word_count = len(user_message.split())
                if word_count >= 10:  # Even higher threshold for threads
                    # Check if it's not clearly OOC or technical
                    non_rp_indicators = ['ooc', 'debug', 'error', 'code', 'script', 'function']
                    if not any(indicator in message_lower for indicator in non_rp_indicators):
                        print(f"   🧵 Thread context: Substantial undirected message in single-character scene ({word_count} words)")
                        return True, "thread_substantial_single"
    
    # 9. Listen mode - don't respond to conversations clearly between other characters
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