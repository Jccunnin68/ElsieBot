"""
Query Detection and Intent Classification
========================================

This module contains all query detection and parsing logic extracted from ai_logic.py.
Provides clean, focused interface for identifying user intent patterns.

ENHANCED: Phase 6B Migration with conflict prevention and category intersection.

Usage:
    from handlers.ai_logic.query_detection import is_continuation_request
"""

from typing import Optional, Tuple, Dict, List, Any
import re

from ..ai_wisdom.log_patterns import is_log_query, has_log_specific_terms

# Define all pattern recognition constants locally (moved from config.py)

CHARACTER_PATTERNS = [
    r"tell.*about (?:captain |commander |lieutenant |doctor |dr\. |ensign |chief )?(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)",
    r"who (?:is|was) (?:captain |commander |lieutenant |doctor |dr\. |ensign |chief )?(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)",
    r"(?:captain |commander |lieutenant |doctor |dr\. |ensign |chief )?(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*) (?:biography|background|history|profile)",
    r"(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*) (?:character|person|officer|crew)",
    r"(?:about|info on|information about) (?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)",
    r"(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)'s (?:background|history|bio)"
]

CHARACTER_KEYWORDS = [
    'captain', 'commander', 'lieutenant', 'doctor', 'dr.', 'ensign', 'chief',
    'officer', 'crew', 'member', 'personnel', 'biography', 'background', 
    'history', 'profile', 'character', 'person'
]

COMMON_CHARACTER_NAMES = [
    'kirk', 'spock', 'mccoy', 'scotty', 'uhura', 'sulu', 'chekov',
    'picard', 'riker', 'data', 'worf', 'geordi', 'troi', 'beverly',
    'janeway', 'chakotay', 'tuvok', 'paris', 'torres', 'kim', 'neelix',
    'sisko', 'kira', 'odo', 'dax', 'bashir', 'obrien', 'nog',
    'archer', 'trip', 'reed', 'hoshi', 'travis', 'phlox'
]

SHIP_LOG_PATTERNS = [
    r"show.*logs? for (?:the )?(USS )?(?P<ship>[A-Za-z]+)",
    r"what.*happened (?:on|aboard) (?:the )?(USS )?(?P<ship>[A-Za-z]+)",
    r"tell.*about.*(?:the )?(USS )?(?P<ship>[A-Za-z]+).*(?:logs?|events|missions?)",
    r"(?:get|fetch|find).*logs? for (?:the )?(USS )?(?P<ship>[A-Za-z]+)",
    r"summarize.*logs? (?:for|from) (?:the )?(USS )?(?P<ship>[A-Za-z]+)"
]

LOG_SEARCH_KEYWORDS = [
    'mission', 'event', 'incident', 'encounter', 'expedition',
    'first contact', 'combat', 'diplomatic', 'exploration',
    'scientific', 'medical', 'emergency', 'distress', 'rescue'
]

LOG_SPECIFIC_INDICATORS = [
    'log', 'logs', 'entries', 'entry', 'mission', 'missions', 
    'report', 'reports', 'record', 'records', 'duty log',
    'captain\'s log', 'personal log', 'official log',
    'mission log', 'duty logs', 'mission reports'
]

SHIP_NAMES = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 'banshee', 'enterprise', 'gigantes', 'voyager', 'defiant']


def detect_query_type_with_conflicts(user_message: str) -> Dict[str, Any]:
    """
    Enhanced query detection that prevents conflicts between types.
    Returns query type, subject, and conflict resolution.
    
    PRIORITY ORDER:
    1. Log queries (highest priority for conflict prevention)
    2. Character queries (with category intersection)
    3. Ship queries (with category intersection)
    4. Tell me about fallback
    """
    print(f"   🔍 ENHANCED QUERY DETECTION: '{user_message}'")
    
    # PRIORITY 1: Log queries (highest priority for conflict prevention)
    if has_log_specific_terms(user_message):
        print(f"      📋 Log-specific terms detected")
        
        # Check for ship + log combination
        is_ship_log, ship_name, log_type = is_ship_plus_log_query(user_message)
        if is_ship_log:
            print(f"      🚢📋 Ship+Log conflict resolved: {ship_name} {log_type}")
            return {
                'type': 'ship_log',
                'subject': ship_name,
                'log_type': log_type,
                'conflict_resolved': f'ship+log detected: {ship_name} {log_type}',
                'priority': 1
            }
        
        # Check for character + log combination  
        is_char_log, char_name, log_type = is_character_plus_log_query(user_message)
        if is_char_log:
            print(f"      🧑📋 Character+Log conflict resolved: {char_name} {log_type}")
            return {
                'type': 'character_log', 
                'subject': char_name,
                'log_type': log_type,
                'conflict_resolved': f'character+log detected: {char_name} {log_type}',
                'priority': 1
            }
        
        # General log query
        print(f"      📋 General log query detected")
        return {
            'type': 'log', 
            'subject': None, 
            'conflict_resolved': 'general log query',
            'priority': 1
        }
    
    # PRIORITY 2: Character queries (with category intersection)
    is_char, char_name = is_character_query(user_message)
    if is_char and char_name:
        print(f"      🧑 Character query detected: {char_name}")
        return {
            'type': 'character',
            'subject': char_name,
            'requires_category_intersection': True,
            'valid_categories': ['Characters', 'Personnel', 'Crew'],
            'priority': 2
        }
    
    # PRIORITY 3: Ship queries (with category intersection)
    if is_ship_query(user_message):
        ship_name = extract_ship_name(user_message)
        print(f"      🚢 Ship query detected: {ship_name}")
        return {
            'type': 'ship',
            'subject': ship_name,
            'requires_category_intersection': True,
            'valid_categories': ['Ship Information', 'Starships', 'Vessels'],
            'priority': 3
        }
    
    # PRIORITY 4: Tell me about fallback
    tell_me_subject = extract_tell_me_about_subject(user_message)
    if tell_me_subject:
        print(f"      📖 Tell me about query detected: {tell_me_subject}")
        return {
            'type': 'tell_me_about',
            'subject': tell_me_subject,
            'needs_title_search': True,
            'priority': 4
        }
    
    print(f"      ❓ General query detected (no specific type)")
    return {'type': 'general', 'subject': None, 'priority': 5}


def is_ship_query(user_message: str) -> bool:
    """
    Check if the message is asking about a ship specifically.
    Enhanced to prevent conflicts with log queries.
    """
    user_lower = user_message.lower().strip()
    
    # Skip if this has log-specific terms - let log detection handle it
    if has_log_specific_terms(user_message):
        print(f"      ⚠️  Skipping ship detection - log terms detected")
        return False
    
    # Check for ship indicators
    ship_indicators = [
        'uss', 'ship', 'vessel', 'starship', 'cruiser', 'destroyer',
        'the stardancer', 'the adagio', 'the pilgrim'
    ]
    
    # Check for ship names
    ship_names_detected = []
    for ship in SHIP_NAMES:
        if ship in user_lower:
            ship_names_detected.append(ship)
    
    # Must have ship name AND ship context (or be a tell me about query)
    has_ship_name = len(ship_names_detected) > 0
    has_ship_context = any(indicator in user_lower for indicator in ship_indicators)
    is_tell_me_about = extract_tell_me_about_subject(user_message) is not None
    
    return has_ship_name and (has_ship_context or is_tell_me_about)


def extract_ship_name(user_message: str) -> Optional[str]:
    """Extract ship name from the message."""
    user_lower = user_message.lower().strip()
    
    for ship in SHIP_NAMES:
        if ship in user_lower:
            return ship
    
    return None


def is_continuation_request(user_message: str) -> bool:
    """
    Detect if this is a request to continue with previous context.
    Returns True for phrases like "yes", "tell me more", "continue", etc.
    """
    user_lower = user_message.lower().strip()
    
    continuation_patterns = [
        'yes', 'yeah', 'yep', 'yup', 'continue', 'go on', 'keep going',
        'tell me more', 'more', 'more details', 'more information',
        'elaborate', 'expand', 'explain more', 'continue please',
        'and then', 'what else', 'anything else', 'more about that'
    ]
    
    # Check for exact matches or starts with pattern
    return any(user_lower == pattern or user_lower.startswith(pattern + ' ') 
               for pattern in continuation_patterns)


def is_federation_archives_request(user_message: str) -> bool:
    """
    Detect if the user is specifically asking for federation archives access.
    Only returns True for explicit requests after a search came up empty.
    """
    user_lower = user_message.lower().strip()
    
    archives_patterns = [
        'check the federation archives',
        'search the federation archives', 
        'look in the federation archives',
        'try the federation archives',
        'what about the federation archives',
        'federation archives',
        'check federation archives',
        'search federation archives',
        'archives have anything',
        'check archives',
        'search archives',
        'look in archives',
        'try archives',
        'external archives',
        'outside database'
    ]
    
    return any(pattern in user_lower for pattern in archives_patterns)












def extract_tell_me_about_subject(user_message: str) -> Optional[str]:
    """
    Extract the subject from a 'tell me about' query.
    Returns the subject if found, otherwise None.
    """
    # Variations of "tell me about"
    tell_me_about_patterns = [
        "tell me about ",
        "tell me more about ",
        "what can you tell me about ",
        "can you tell me about ",
        "tell me a story about",
        "retrieve the",
        "summarize"
    ]
    
    # Convert to lowercase for case-insensitive matching
    message_lower = user_message.lower().strip()
    
    # Check each pattern
    for pattern in tell_me_about_patterns:
        if message_lower.startswith(pattern):
            # Extract subject by removing the pattern
            subject = message_lower[len(pattern):].strip()
            
            # Ensure subject is not empty and has some meaningful content
            if subject and len(subject) > 2:
                return subject
    
    return None


def detect_log_selection_query(user_message: str) -> Tuple[bool, str, Optional[str]]:
    """
    Detect log selection queries with temporal and random selection
    Returns (is_selection_query, selection_type, ship_name)
    
    Selection types:
    - 'latest'/'last'/'most_recent' → Most recent by date DESC
    - 'first'/'earliest'/'oldest' → Oldest by date ASC  
    - 'random'/'pick' → Random selection from results
    - 'today'/'yesterday'/'this_week' → Date-filtered
    """
    message = user_message.strip().lower()
    
    # Only process if this contains log indicators
    if not any(indicator in message for indicator in LOG_SPECIFIC_INDICATORS + ['log', 'logs', 'mission']):
        return False, "", None
    
    # Extract ship name if present
    detected_ship = None
    # Use local ship names since SHIP_NAMES was removed in Phase 2
    ship_names = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel']
    for ship in ship_names:
        if ship.lower() in message:
            detected_ship = ship.lower()
            break
    
    # Check for random selection keywords
    random_patterns = [
        'pick a log', 'pick', 'random log', 'any log', 'surprise me',
        'choose a log', 'select a log', 'give me a log'
    ]
    
    for pattern in random_patterns:
        if pattern in message:
            print(f"   🎲 Random log selection detected: '{pattern}' (ship: {detected_ship})")
            return True, 'random', detected_ship
    
    # Check for temporal recent keywords (DESC order)
    recent_patterns = [
        'latest', 'last', 'most recent', 'newest', 'current', 'recent'
    ]
    
    for pattern in recent_patterns:
        if pattern in message:
            print(f"   📅 Recent temporal query detected: '{pattern}' (ship: {detected_ship})")
            return True, 'latest', detected_ship
    
    # Check for temporal old keywords (ASC order)
    old_patterns = [
        'first', 'earliest', 'oldest', 'original', 'initial'
    ]
    
    for pattern in old_patterns:
        if pattern in message:
            print(f"   📅 Historical temporal query detected: '{pattern}' (ship: {detected_ship})")
            return True, 'first', detected_ship
    
    # Check for date-based keywords
    date_patterns = {
        'today': 'today',
        'yesterday': 'yesterday', 
        'this week': 'this_week',
        'last week': 'last_week'
    }
    
    for pattern, selection_type in date_patterns.items():
        if pattern in message:
            print(f"   📅 Date-based query detected: '{pattern}' (ship: {detected_ship})")
            return True, selection_type, detected_ship
    
    return False, "", None


def extract_url_request(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if this is a request for a log URL and extract search terms.
    Returns (is_url_request, search_query)
    """
    message = user_message.strip().lower()
    
    # Multiple patterns for log URL requests (without OOC prefix requirement)
    log_url_patterns = [
        # "link me the log page for the last [shipname]"
        r'link\s+me\s+the\s+log\s+page\s+for\s+the\s+last\s+(\w+)',
        # "link me the log page for [anything]"  
        r'link\s+me\s+the\s+log\s+page\s+for\s+(.+)',
        # "get me the URL for [anything]"
        r'get\s+me\s+the\s+url\s+for\s+(.+)',
        # "show me the link to [anything]"
        r'show\s+me\s+the\s+link\s+to\s+(.+)',
        # "find the log page for [anything]"
        r'find\s+the\s+log\s+page\s+for\s+(.+)',
        # "link to [anything] log"
        r'link\s+to\s+(.+)\s+log',
        # "URL for [anything]"
        r'url\s+for\s+(.+)',
        # "link me the [anything] page" - flexible page pattern
        r'link\s+me\s+the\s+(.+?)\s+page',
        # "link me [anything]" - most flexible
        r'link\s+me\s+(.+)',
        # "get me [anything]" - flexible get pattern
        r'get\s+me\s+(.+)',
        # "[anything] link" or "[anything] url"
        r'(.+?)\s+(?:link|url)',
        # "show me [anything]"
        r'show\s+me\s+(.+)'
    ]
    
    for pattern in log_url_patterns:
        url_match = re.search(pattern, message, re.IGNORECASE)
        if url_match:
            search_query = url_match.group(1).strip()
            # Remove common words that don't help with search
            search_query = re.sub(r'\b(the|page|for|USS|of|a|an)\b', '', search_query, flags=re.IGNORECASE).strip()
            # Clean up extra spaces
            search_query = re.sub(r'\s+', ' ', search_query).strip()
            
            if search_query:  # Only return if we have a valid search query
                print(f"   🔗 URL pattern matched: '{pattern}' -> '{search_query}'")
                return True, search_query
    
    return False, None




def is_ship_plus_log_query(user_message: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Detect when a user is asking for ship logs specifically (not general ship info).
    Returns (is_ship_log_query, ship_name, log_type)
    """
    message_lower = user_message.lower().strip()
    
    # Skip if this is a "tell me about" query - those should get general info
    tell_me_about_subject = extract_tell_me_about_subject(user_message)
    if tell_me_about_subject and not has_log_specific_terms(tell_me_about_subject):
        print(f"   📖 Skipping ship+log detection - this is a 'tell me about' query without log terms")
        return False, None, None
    
    # Look for ship names combined with log indicators
    ship_names = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel','gigantes']
    
    detected_ship = None
    for ship in ship_names:
        if ship in message_lower:
            detected_ship = ship
            break
    
    if detected_ship and has_log_specific_terms(user_message):
        # Extract log type if specified
        log_type = None
        for indicator in LOG_SPECIFIC_INDICATORS:
            if indicator in message_lower:
                log_type = indicator
                break
        
        print(f"   🚢📋 Ship+Log query detected: ship='{detected_ship}', log_type='{log_type}'")
        return True, detected_ship, log_type
    
    return False, None, None


def is_character_plus_log_query(user_message: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Detect when a user is asking for character logs specifically (not general character info).
    Returns (is_character_log_query, character_name, log_type)
    """
    message_lower = user_message.lower().strip()
    
    # Skip if this is a "tell me about" query - those should get general info
    tell_me_about_subject = extract_tell_me_about_subject(user_message)
    if tell_me_about_subject and not has_log_specific_terms(tell_me_about_subject):
        print(f"   📖 Skipping character+log detection - this is a 'tell me about' query without log terms")
        return False, None, None
    
    # Only proceed if there are log-specific terms
    if not has_log_specific_terms(user_message):
        return False, None, None
    
    # Check for character patterns
    is_char, character_name = is_character_query(user_message)
    
    if is_char and character_name:
        # Extract log type if specified
        log_type = None
        for indicator in LOG_SPECIFIC_INDICATORS:
            if indicator in message_lower:
                log_type = indicator
                break
        
        print(f"   🧑📋 Character+Log query detected: character='{character_name}', log_type='{log_type}'")
        return True, character_name, log_type
    
    return False, None, None





def is_character_query(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the message is asking about a character and extract the character name.
    Returns (is_character_query, character_name).
    
    Enhanced to respect log-specific queries and "tell me about" boundaries.
    """
    message = user_message.lower().strip()
    
    # Skip if this is specifically asking for logs - that should be handled by log detection
    if has_log_specific_terms(user_message):
        tell_me_about_subject = extract_tell_me_about_subject(user_message)
        if not tell_me_about_subject:  # Not a "tell me about" query, so it's probably asking for logs
            print(f"   📋 Skipping character detection - log-specific terms detected without 'tell me about'")
            return False, None
    
    # Exclude ship names explicitly to prevent false positives
    ship_indicators = ['uss', 'ship', 'vessel', 'stardancer', 'adagio', 'pilgrim', 'voyager', 'enterprise', 'defiant']
    if any(indicator in message for indicator in ship_indicators):
        print(f"   🚢 Skipping character detection - ship indicator found: {[ind for ind in ship_indicators if ind in message]}")
        return False, None
    
    # Check for character-related keywords
    has_character_keyword = any(keyword in message for keyword in CHARACTER_KEYWORDS)
    
    # Check for character name patterns
    for pattern in CHARACTER_PATTERNS:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            character_name = match.group('name')
            # Double-check it's not a ship name
            if not any(ship_word in character_name.lower() for ship_word in ship_indicators):
                return True, character_name
    
    # Check for common character names (works without keywords)
    for name in COMMON_CHARACTER_NAMES:
        if name in message:
            return True, name.title()
    
    # Enhanced detection for proper names but only with clear character context
    words = user_message.split()
    for i, word in enumerate(words):
        # Skip common non-name words and ship indicators
        if word.lower() in ['USS', 'THE', 'AND', 'FOR', 'TO', 'OF', 'IN', 'ON', 'AT', 'IS', 'WAS', 'ARE', 'WERE', 'A', 'AN', 'THIS', 'THAT', 'SHIP', 'VESSEL']:
            continue
            
        if len(word) > 2 and word[0].isupper():
            # Skip if it looks like a ship name
            if word.lower() in ship_indicators:
                continue
                
            # Check if this looks like a person's name
            # Look for patterns like "tell me about [Name]", "who is [Name]", etc.
            preceding_words = ' '.join(words[max(0, i-3):i]).lower()
            following_words = ' '.join(words[i+1:i+4]).lower()
            
            # Context clues that suggest this is a character query
            name_context_clues = [
                'who is', 'who was', 'captain', 'commander', 'lieutenant', 'ensign', 'admiral',
                'officer', 'crew member', 'character', 'person', 'biography',
                'background of', 'history of'
            ]
            
            # Only return true if we have strong character context clues
            if any(clue in preceding_words or clue in following_words for clue in name_context_clues):
                # Check if next word is also capitalized (full name)
                if i < len(words) - 1 and len(words[i + 1]) > 2 and words[i + 1][0].isupper():
                    full_name = f"{word} {words[i + 1]}"
                    if not any(ship_word in full_name.lower() for ship_word in ship_indicators):
                        return True, full_name
                else:
                    if not any(ship_word in word.lower() for ship_word in ship_indicators):
                        return True, word
    
    # Only if we have explicit character keywords AND find a name
    if has_character_keyword:
        for i, word in enumerate(words):
            if len(word) > 2 and word[0].isupper() and word.lower() not in ['USS', 'THE', 'AND', 'FOR', 'TO', 'OF', 'IN', 'ON', 'AT'] + ship_indicators:
                # Check if next word is also capitalized (full name)
                if i < len(words) - 1 and len(words[i + 1]) > 2 and words[i + 1][0].isupper():
                    full_name = f"{word} {words[i + 1]}"
                    if not any(ship_word in full_name.lower() for ship_word in ship_indicators):
                        return True, full_name
                else:
                    if not any(ship_word in word.lower() for ship_word in ship_indicators):
                        return True, word
    
    return False, None


def get_query_type(user_message: str) -> str:
    """Get the type of query to help detect topic changes"""
    if is_continuation_request(user_message):
        return "continuation"
    elif extract_url_request(user_message)[0]:
        return "url_request"
    elif detect_log_selection_query(user_message)[0]:
        return "log_selection"
    elif is_character_query(user_message)[0]:
        return "character"
    elif is_log_query(user_message):
        return "log"
    elif extract_tell_me_about_subject(user_message):
        return "tell_me_about"
    else:
        return "general"
