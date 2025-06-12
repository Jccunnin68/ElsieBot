"""AI logic for intent detection, guard rails, and conversation flow management"""

import re
from datetime import datetime
from typing import Optional, Tuple, Dict, List
import json

from config import (
    estimate_token_count,
    OOC_PREFIX, OOC_KEYWORDS,
    MEETING_INFO_PATTERNS,
    SHIP_LOG_PATTERNS, SHIP_NAMES, LOG_SEARCH_KEYWORDS,
    CHARACTER_PATTERNS, CHARACTER_KEYWORDS, COMMON_CHARACTER_NAMES,
    ROLEPLAY_EXCLUDED_WORDS
)
from log_processor import is_log_query


def convert_earth_date_to_star_trek(date_text: str) -> str:
    """
    Convert Earth dates in text to Star Trek era dates.
    Prior to June 2024: year + 404
    After June 2024: year + 430
    """
    # Pattern to match various date formats
    date_patterns = [
        r'\b(\d{4})\b',  # Just year
        r'\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})\b',  # MM/DD/YYYY or MM-DD-YYYY
        r'\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b(\w+)\s+(\d{1,2}),?\s+(\d{4})\b',  # Month DD, YYYY
        r'\b(\d{1,2})\s+(\w+)\s+(\d{4})\b'  # DD Month YYYY
    ]
    
    def convert_year(year: int, month: int = 6, day: int = 1) -> int:
        """Convert a year based on the June 2024 cutoff"""
        cutoff_date = datetime(2024, 6, 1)
        date_to_check = datetime(year, month, day)
        
        if date_to_check < cutoff_date:
            return year + 404
        else:
            return year + 430
    
    converted_text = date_text
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, date_text, re.IGNORECASE)
        for match in matches:
            original = match.group(0)
            groups = match.groups()
            
            if len(groups) == 1:  # Just year
                year = int(groups[0])
                if 1900 <= year <= 2100:  # Reasonable year range
                    converted_year = convert_year(year)
                    converted_text = converted_text.replace(original, str(converted_year), 1)
            
            elif len(groups) == 3:  # Full date
                try:
                    if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                        # Numeric date
                        if len(groups[0]) == 4:  # YYYY/MM/DD
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # MM/DD/YYYY
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    else:
                        # Text month format
                        if groups[0].isdigit():  # DD Month YYYY
                            day, month_name, year = int(groups[0]), groups[1], int(groups[2])
                        else:  # Month DD, YYYY
                            month_name, day, year = groups[0], int(groups[1]), int(groups[2])
                        
                        # Convert month name to number
                        month_names = {
                            'january': 1, 'february': 2, 'march': 3, 'april': 4,
                            'may': 5, 'june': 6, 'july': 7, 'august': 8,
                            'september': 9, 'october': 10, 'november': 11, 'december': 12,
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        month = month_names.get(month_name.lower(), 6)  # Default to June if unknown
                    
                    if 1900 <= year <= 2100:  # Reasonable year range
                        converted_year = convert_year(year, month, day)
                        # Replace the year in the original date
                        new_date = original.replace(str(year), str(converted_year))
                        converted_text = converted_text.replace(original, new_date, 1)
                
                except (ValueError, KeyError):
                    continue  # Skip if date parsing fails
    
    return converted_text


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


def extract_continuation_focus(user_message: str, conversation_history: list) -> tuple[bool, str, str]:
    """
    Extract what specific aspect the user wants more information about in a continuation request.
    Returns (is_focused_continuation, focus_subject, context_type)
    """
    user_lower = user_message.lower().strip()
    
    # Check if this is a continuation request first
    if not is_continuation_request(user_message):
        return False, "", ""
    
    # Get the last assistant response to understand previous context
    last_assistant_responses = [msg for msg in conversation_history if msg["role"] == "assistant"]
    if not last_assistant_responses:
        return False, "", ""
    
    last_response = last_assistant_responses[-1]["content"].lower()
    
    # Determine what type of context we had before
    context_type = "general"
    if "mission log" in last_response or "log content" in last_response:
        context_type = "logs"
    elif "character" in last_response or "personnel" in last_response:
        context_type = "character"
    elif "ship" in last_response or "vessel" in last_response:
        context_type = "ship"
    
    # Look for specific focus indicators in the continuation request
    focus_patterns = {
        'character_focus': [
            r'about ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "about Captain Smith"
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[\'s\s]+(role|part|actions|involvement)',  # "Smith's role"
            r'what (?:did|was) ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # "what did Smith"
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:do|did|say|said)',  # "Smith did"
        ],
        'event_focus': [
            r'about (?:the\s+)?([a-z\s]+(?:incident|event|mission|operation|encounter))',  # "about the incident"
            r'what happened (?:to|with|during|in)\s+(.+)',  # "what happened to"
            r'(?:the\s+)?([a-z\s]+(?:battle|fight|conflict|crisis))',  # "the battle"
        ],
        'location_focus': [
            r'(?:on|at|in)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # "on the bridge"
            r'what about (?:the\s+)?([a-z\s]+(?:station|ship|planet|system))',  # "what about the station"
        ],
        'time_focus': [
            r'(?:when|what time|during)\s+(.+)',  # "when did"
            r'(?:before|after)\s+(.+)',  # "after the"
        ]
    }
    
    # Try to extract specific focus
    for focus_type, patterns in focus_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                focus_subject = match.group(1).strip()
                # Clean up common words
                focus_subject = re.sub(r'\b(the|a|an|that|this|what|did|was|were|is|are)\b', '', focus_subject, flags=re.IGNORECASE).strip()
                focus_subject = re.sub(r'\s+', ' ', focus_subject).strip()
                
                if focus_subject and len(focus_subject) > 2:
                    return True, focus_subject, context_type
    
    # If no specific focus found, but it's a continuation, return general continuation
    return True, "", context_type


def is_specific_log_request(user_message: str) -> bool:
    """
    Detect if user is specifically asking for mission logs (not other page types).
    Returns True when they use the word "log" specifically.
    """
    user_lower = user_message.lower().strip()
    
    # Look for specific log indicators
    log_specific_patterns = [
        'show me the log', 'get the log', 'find the log', 'retrieve the log',
        'mission log', 'ship log', 'captain log', 'personal log',
        'show log', 'get log', 'find log', 'log for', 'log from',
        'logs for', 'logs from', 'recent log', 'last log', 'latest log'
    ]
    
    # Check if message contains "log" in a specific context
    if any(pattern in user_lower for pattern in log_specific_patterns):
        return True
    
    # Check for standalone "log" requests
    words = user_lower.split()
    if 'log' in words or 'logs' in words:
        return True
    
    return False


def is_stardancer_query(user_message: str) -> bool:
    """
    Check if the message is asking about the USS Stardancer specifically.
    Requires special guard rails to prevent inventing command staff.
    """
    user_lower = user_message.lower().strip()
    
    stardancer_indicators = [
        'stardancer', 'star dancer', 'uss stardancer', 'this ship', 'our ship',
        'the ship', 'my ship', 'your ship'
    ]
    
    return any(indicator in user_lower for indicator in stardancer_indicators)


def is_stardancer_command_query(user_message: str) -> bool:
    """
    Check if the message is asking about Stardancer command staff specifically.
    These queries need the strictest guard rails.
    """
    user_lower = user_message.lower().strip()
    
    command_indicators = [
        'captain', 'commander', 'first officer', 'xo', 'command staff',
        'senior staff', 'bridge crew', 'officers', 'command structure',
        'who commands', 'who is the captain', 'command team'
    ]
    
    return is_stardancer_query(user_message) and any(indicator in user_lower for indicator in command_indicators)


def chunk_prompt_for_tokens(prompt: str, max_tokens: int = 7192) -> list:
    """
    Break large prompts into manageable chunks that fit within token limits.
    Returns a list of prompt chunks.
    """
    estimated_tokens = estimate_token_count(prompt)
    
    if estimated_tokens <= max_tokens:
        return [prompt]
    
    # Split prompt into sections
    sections = prompt.split('\n\n')
    chunks = []
    current_chunk = ""
    current_tokens = 0
    
    for section in sections:
        section_tokens = estimate_token_count(section)
        
        if current_tokens + section_tokens <= max_tokens:
            if current_chunk:
                current_chunk += '\n\n' + section
            else:
                current_chunk = section
            current_tokens += section_tokens
        else:
            # Finish current chunk
            if current_chunk:
                chunks.append(current_chunk)
            
            # Start new chunk
            if section_tokens <= max_tokens:
                current_chunk = section
                current_tokens = section_tokens
            else:
                # Section too large, split it further
                words = section.split()
                temp_section = ""
                for word in words:
                    test_section = temp_section + ' ' + word if temp_section else word
                    if estimate_token_count(test_section) <= max_tokens:
                        temp_section = test_section
                    else:
                        if temp_section:
                            chunks.append(temp_section)
                        temp_section = word
                
                if temp_section:
                    current_chunk = temp_section
                    current_tokens = estimate_token_count(temp_section)
    
    # Add final chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


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
        "tell me a story about"
        "Retrieve the",
        "Summarize"
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


def is_ooc_query(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the message is an out-of-character query.
    Returns (is_ooc, subject) where subject is the query without the OOC prefix.
    """
    message = user_message.strip()
    if not message.upper().startswith(OOC_PREFIX):
        return False, None
        
    # Remove OOC prefix and get the actual query
    query = message[len(OOC_PREFIX):].strip()
    if not query:
        return False, None
        
    # Check for log URL patterns first (specific pattern)
    log_url_pattern = r'link\s+me\s+the\s+log\s+page\s+for\s+the\s+last\s+(\w+)'
    url_match = re.search(log_url_pattern, query, re.IGNORECASE)
    if url_match:
        return True, query  # Return the full query for processing
        
    # Check if query contains any OOC keywords
    query_lower = query.lower()
    if any(keyword in query_lower for keyword in OOC_KEYWORDS):
        return True, query
        
    return False, None


def extract_ooc_log_url_request(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if this is an OOC request for a log URL and extract search terms.
    Returns (is_url_request, search_query)
    """
    message = user_message.strip()
    if not message.upper().startswith(OOC_PREFIX):
        return False, None
        
    # Remove OOC prefix and get the actual query
    query = message[len(OOC_PREFIX):].strip()
    
    # Multiple patterns for log URL requests
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
        url_match = re.search(pattern, query, re.IGNORECASE)
        if url_match:
            search_query = url_match.group(1).strip()
            # Remove common words that don't help with search
            search_query = re.sub(r'\b(the|page|for|USS|of|a|an)\b', '', search_query, flags=re.IGNORECASE).strip()
            # Clean up extra spaces
            search_query = re.sub(r'\s+', ' ', search_query).strip()
            
            if search_query:  # Only return if we have a valid search query
                print(f"   🔗 OOC URL pattern matched: '{pattern}' -> '{search_query}'")
                return True, search_query
    
    return False, None


def filter_meeting_info(text: str) -> str:
    """Remove meeting schedule information from responses"""
    filtered_text = text
    for pattern in MEETING_INFO_PATTERNS:
        filtered_text = re.sub(pattern, "", filtered_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up any double newlines or spaces created by the filtering
    filtered_text = re.sub(r'\n\s*\n', '\n\n', filtered_text)
    filtered_text = re.sub(r' +', ' ', filtered_text)
    return filtered_text.strip()


def extract_ship_log_query(user_message: str) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    Check if the message is requesting ship logs and extract ship name and context.
    Returns (is_ship_log_query, details) where details contains ship name and query type.
    """
    message = user_message.lower().strip()
    
    # Check each pattern for a match
    for pattern in SHIP_LOG_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            ship_name = match.group('ship').lower()
            # Verify it's a known ship
            if ship_name in [s.lower() for s in SHIP_NAMES]:
                # Extract any specific log keywords
                log_type = None
                for keyword in LOG_SEARCH_KEYWORDS:
                    if keyword in message:
                        log_type = keyword
                        break
                
                return True, {
                    'ship': ship_name,
                    'log_type': log_type
                }
    
    return False, None


def is_character_query(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the message is asking about a character and extract the character name.
    Returns (is_character_query, character_name).
    """
    message = user_message.lower().strip()
    
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
                    return True, word
    
    return False, None


def get_query_type(user_message: str) -> str:
    """Get the type of query to help detect topic changes"""
    if is_continuation_request(user_message):
        return "continuation"
    elif is_character_query(user_message)[0]:
        return "character"
    elif is_stardancer_query(user_message):
        return "stardancer"
    elif extract_ship_log_query(user_message)[0]:
        return "ship_log"
    elif is_log_query(user_message):
        return "log"
    elif is_ooc_query(user_message)[0]:
        return "ooc"
    elif extract_tell_me_about_subject(user_message):
        return "tell_me_about"
    else:
        return "general"


def detect_topic_change(user_message: str, conversation_history: list) -> bool:
    """
    Detect if the current message represents a topic change from previous conversation.
    Returns True if this is a new topic that should break continuity.
    Enhanced to allow follow-up questions and detect explicit reset requests.
    """
    if not conversation_history:
        return True  # First message is always a new topic
    
    current_message = user_message.lower().strip()
    
    # Check for explicit conversation reset phrases
    reset_phrases = [
        "let's talk about something else",
        "lets talk about something else", 
        "change the subject",
        "something different",
        "new topic",
        "talk about something different"
    ]
    
    if any(phrase in current_message for phrase in reset_phrases):
        print("🔄 Explicit topic reset detected")
        return True
    
    # Get the last user message for comparison
    last_user_messages = [msg for msg in conversation_history if msg["role"] == "user"]
    if not last_user_messages:
        return True
    
    last_user_message = last_user_messages[-1]["content"].lower().strip()
    
    # Follow-up question indicators that should NOT break continuity
    followup_indicators = [
        'what about', 'how about', 'what else', 'tell me more', 'more about',
        'and what', 'what other', 'any other', 'also', 'additionally',
        'what was', 'what were', 'when did', 'where did', 'how did',
        'can you elaborate', 'more details', 'more information',
        'what happened to', 'what about their', 'what about his', 'what about her'
    ]
    
    # Check if this is a follow-up question or continuation request
    is_followup = any(current_message.startswith(indicator) for indicator in followup_indicators)
    is_continuation = is_continuation_request(user_message)
    
    if is_followup or is_continuation:
        print("🔗 Follow-up question or continuation detected - maintaining context")
        return False
    
    # Question starters that might indicate a new topic (but not always)
    potential_new_topic_indicators = [
        'tell me about', 'what is', 'what are', 'who is', 'who are', 
        'how does', 'how do', 'why', 'when', 'where', 'show me',
        'explain', 'describe', 'ooc', 'summarize', 'what happened',
        'can you', 'could you', 'would you', 'retrieve'
    ]
    
    # Check if this is a different type of query
    current_query_type = get_query_type(user_message)
    last_query_type = get_query_type(last_user_messages[-1]["content"])
    
    # For "tell me about" queries, check if it's about the same subject
    if current_query_type == "tell_me_about" and last_query_type == "tell_me_about":
        current_subject = extract_tell_me_about_subject(user_message)
        last_subject = extract_tell_me_about_subject(last_user_messages[-1]["content"])
        
        if current_subject and last_subject:
            # Check if subjects are similar (allow for variations like "ship" vs "USS ship")
            if (current_subject in last_subject or last_subject in current_subject or
                any(word in current_subject.split() for word in last_subject.split() if len(word) > 3)):
                print(f"🔗 Same subject detected: '{current_subject}' similar to '{last_subject}' - maintaining context")
                return False
    
    # Check for keyword similarity to detect if it's about the same subject
    current_keywords = set(current_message.split())
    last_keywords = set(last_user_message.split())
    
    # Remove common words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'me', 'you', 'can', 'could', 'would', 'should', 'tell', 'about', 'what', 'who'}
    current_keywords -= common_words
    last_keywords -= common_words
    
    # If there's reasonable keyword overlap, it's likely the same topic
    if current_keywords and last_keywords:
        overlap = len(current_keywords.intersection(last_keywords))
        total_unique = len(current_keywords.union(last_keywords))
        similarity = overlap / total_unique if total_unique > 0 else 0
        
        # More lenient similarity check - 20% overlap suggests same topic
        if similarity >= 0.2:
            print(f"🔗 Topic similarity detected ({similarity:.2%}) - maintaining context")
            return False
    
    # Different query types usually indicate topic change (unless it's a follow-up)
    if current_query_type != last_query_type:
        print(f"🔄 Query type change: {last_query_type} -> {current_query_type}")
        return True
    
    # If current message starts with a strong new topic indicator and we haven't caught it yet
    current_starts_new_topic = any(current_message.startswith(indicator) for indicator in potential_new_topic_indicators)
    if current_starts_new_topic and similarity < 0.1:  # Very low similarity + new topic starter
        print("🔄 New topic starter with low similarity - breaking context")
        return True
    
    # For very short messages like "hello", "hi", "how are you", maintain context unless it's the first message
    if len(current_message.split()) <= 3 and not any(current_message.startswith(indicator) for indicator in potential_new_topic_indicators):
        print("🔗 Short casual message - maintaining context for natural conversation flow")
        return False
    
    # Default to maintaining context for ambiguous cases
    print("🔗 Ambiguous case - maintaining context")
    return False


def format_conversation_history(conversation_history: list, is_topic_change: bool) -> str:
    """Format conversation history, expanding context for follow-up questions"""
    if is_topic_change:
        # For topic changes, only include the last exchange to avoid confusion
        recent_messages = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
        print("🔄 Topic change detected - limiting conversation history to prevent continuity issues")
    else:
        # For continuing conversations, include more context to allow better follow-ups
        recent_messages = conversation_history[-6:]  # Increased from 4 to 6 for better follow-up support
        print("🔗 Maintaining conversation context - including extended history for follow-ups")
    
    chat_history = ""
    for msg in recent_messages:
        role = "Customer" if msg["role"] == "user" else "Elsie"
        chat_history += f"{role}: {msg['content']}\n"
    
    return chat_history


def format_conversation_history_with_dgm_elsie(conversation_history: list, is_topic_change: bool) -> str:
    """
    Format conversation history with special handling for DGM-controlled Elsie posts.
    DGM-controlled Elsie content ([DGM][Elsie] posts) should appear as if Elsie said them.
    """
    if is_topic_change:
        # For topic changes, only include the last exchange to avoid confusion
        recent_messages = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
        print("🔄 Topic change detected - limiting conversation history to prevent continuity issues")
    else:
        # For continuing conversations, include more context to allow better follow-ups
        recent_messages = conversation_history[-6:]  # Increased from 4 to 6 for better follow-up support
        print("🔗 Maintaining conversation context - including extended history for follow-ups")
    
    chat_history = ""
    for msg in recent_messages:
        content = msg['content']
        
        # Check if this is a DGM-controlled Elsie post
        dgm_result = _check_dgm_post(content)
        if dgm_result['dgm_controlled_elsie']:
            # Extract the Elsie content and present it as if Elsie said it
            elsie_content = dgm_result['elsie_content']
            chat_history += f"Elsie: {elsie_content}\n"
            print(f"   🎭 DGM-CONTROLLED ELSIE CONTENT ADDED TO HISTORY: '{elsie_content[:50]}{'...' if len(elsie_content) > 50 else ''}'")
        else:
            # Regular message formatting
            role = "Customer" if msg["role"] == "user" else "Elsie"
            chat_history += f"{role}: {content}\n"
    
    return chat_history


def detect_roleplay_triggers(user_message: str, channel_context: Dict = None) -> Tuple[bool, float, List[str]]:
    """
    Roleplay Detection Engine: Detect if user is initiating or continuing roleplay.
    Enhanced with passive listening and channel restrictions.
    Now includes DGM (Deputy Game Master) scene setting support.
    Returns (is_roleplay, confidence_score, detected_triggers)
    """
    print(f"\n🔍 ROLEPLAY DETECTION ENGINE:")
    print(f"   📝 Message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
    
    # Check for DGM (Deputy Game Master) posts first
    dgm_result = _check_dgm_post(user_message)
    if dgm_result['is_dgm']:
        print(f"   🎬 DGM POST DETECTED: {dgm_result['action']}")
        return dgm_result['triggers_roleplay'], dgm_result['confidence'], dgm_result['triggers']
    
    # Check if we're in an appropriate channel for roleplay
    if not is_roleplay_allowed_channel(channel_context):
        print(f"   🚫 DETECTION BLOCKED: Roleplay not allowed in this channel")
        return False, 0.0, ["channel_restricted"]
    
    confidence_score = 0.0
    detected_triggers = []
    
    # Check if we're in a thread - threads get bonus confidence
    is_thread = False
    channel_type = "unknown"
    if channel_context:
        is_thread = channel_context.get('is_thread', False)
        channel_type = channel_context.get('type', 'unknown')
        discord_thread_types = ['public_thread', 'private_thread', 'news_thread']
        if is_thread or channel_type in discord_thread_types:
            is_thread = True
    
    print(f"   🎯 SCANNING FOR ROLEPLAY PATTERNS:")
    if is_thread:
        print(f"      🧵 THREAD CONTEXT DETECTED - Enhanced roleplay detection")
    
    # 0. Character Name Brackets - Very Strong Indicator (NEW)
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    if bracket_matches:
        confidence_score += 0.7  # Very high confidence for character brackets
        detected_triggers.append("character_brackets")
        character_names = [name.strip() for name in bracket_matches if is_valid_character_name(name.strip())]
        print(f"      ✅ CHARACTER BRACKETS DETECTED: {character_names} (+0.7 confidence)")
    else:
        print(f"      ❌ No character brackets found")
    
    # 1. Emote-Based Detection (Primary Trigger) - Strong indicator
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    if emotes:
        confidence_score += 0.6  # High confidence for emotes
        detected_triggers.append("emotes")
        print(f"      ✅ EMOTES DETECTED: {emotes} (+0.6 confidence)")
    else:
        print(f"      ❌ No emotes found")
    
    # 2. Quoted Dialogue - Moderate indicator (Enhanced for bracket format)
    quote_patterns = [
        r'"([^"]+)"',  # Standard quotes
        r'"([^"]+)"',  # Smart quotes
        r"'([^']+)'",  # Single smart quotes
    ]
    
    has_quotes = False
    for pattern in quote_patterns:
        if re.search(pattern, user_message):
            has_quotes = True
            break
    
    if has_quotes:
        # Higher confidence if combined with character brackets
        quote_bonus = 0.4 if bracket_matches else 0.3
        confidence_score += quote_bonus
        detected_triggers.append("quoted_dialogue")
        print(f"      ✅ QUOTED DIALOGUE: Found quotes (+{quote_bonus} confidence{'with brackets' if bracket_matches else ''})")
    else:
        print(f"      ❌ No quoted dialogue found")
    
    # 3. Second-Person Imperative Actions - Commands directed at the character
    imperative_patterns = [
        r'^(look|tell|show|get|bring|give|take|come|go|sit|stand|walk|turn)',
        r'^(help|find|search|check|grab|pick)',
        r'\b(you should|you need to|you can|could you)\b'
    ]
    
    message_lower = user_message.lower().strip()
    imperative_found = False
    for pattern in imperative_patterns:
        if re.search(pattern, message_lower):
            confidence_score += 0.25
            detected_triggers.append("imperative_action")
            print(f"      ✅ IMPERATIVE ACTION: Pattern '{pattern}' matched (+0.25 confidence)")
            imperative_found = True
            break
    
    if not imperative_found:
        print(f"      ❌ No imperative actions found")
    
    # 4. Narrative/Descriptive Language - Contextual tone
    narrative_indicators = [
        r'\b(she|he|they)\s+(walked|moved|smiled|looked|turned|said|whispered|replied)',
        r'\b(the room|the air|the atmosphere|the place|around them|nearby)',
        r'\b(suddenly|quietly|slowly|carefully|nervously|confidently)\b',
        r'\b(seemed|appeared|felt|looked like|sounded)\b'
    ]
    
    narrative_found = False
    for pattern in narrative_indicators:
        if re.search(pattern, user_message, re.IGNORECASE):
            confidence_score += 0.15
            detected_triggers.append("narrative_tone")
            print(f"      ✅ NARRATIVE TONE: Pattern '{pattern}' matched (+0.15 confidence)")
            narrative_found = True
            break
    
    if not narrative_found:
        print(f"      ❌ No narrative tone found")
    
    # 5. Character Actions Without Emotes - Descriptive actions
    action_indicators = [
        r'\b(nods|shrugs|sighs|laughs|chuckles|grins|frowns|winces)',
        r'\b(approaches|enters|exits|sits down|stands up|leans)',
        r'\b(gestures|points|waves|reaches for|holds)'
    ]
    
    action_found = False
    for pattern in action_indicators:
        if re.search(pattern, user_message, re.IGNORECASE):
            confidence_score += 0.2
            detected_triggers.append("character_actions")
            print(f"      ✅ CHARACTER ACTIONS: Pattern '{pattern}' matched (+0.2 confidence)")
            action_found = True
            break
    
    if not action_found:
        print(f"      ❌ No character actions found")
    
    # 6. Thread Context Bonus - If in a thread, lower the threshold
    thread_bonus = 0.0
    if is_thread:
        # Check for conversational patterns that are common in RP threads
        thread_rp_patterns = [
            r'\b(says|replies|responds|asks|tells|whispers|shouts)\b',
            r'\b(looks at|turns to|faces|addresses)\b',
            r'\b(thinking|wondering|feeling|realizing)\b',
            r'\b(meanwhile|suddenly|then|after|before)\b',
        ]
        
        for pattern in thread_rp_patterns:
            if re.search(pattern, user_message, re.IGNORECASE):
                thread_bonus += 0.25
                detected_triggers.append("thread_rp_pattern")
                print(f"      ✅ THREAD RP PATTERN: '{pattern}' matched (+0.25 thread bonus)")
                break
        
        # General thread bonus for substantial messages
        word_count = len(user_message.split())
        if word_count >= 4:
            thread_bonus += 0.1
            detected_triggers.append("thread_context")
            print(f"      ✅ THREAD CONTEXT: Substantial message in thread (+0.1 thread bonus)")
    
    confidence_score += thread_bonus
    
    # Determine if this qualifies as roleplay
    # Lower threshold for threads since they're primarily for RP
    threshold = 0.2 if is_thread else 0.25
    is_roleplay = confidence_score >= threshold
    
    print(f"   📊 DETECTION RESULTS:")
    print(f"      - Total Confidence: {confidence_score:.2f}")
    print(f"      - Threshold: {threshold} {'(lowered for thread)' if is_thread else ''}")
    print(f"      - Thread Bonus: +{thread_bonus:.2f}")
    print(f"      - Triggers Found: {detected_triggers}")
    print(f"      - Is Roleplay: {is_roleplay}")
    print(f"   🎯 MONITORING STATUS: {'ROLEPLAY ACTIVE' if is_roleplay else 'STANDARD MODE'}")
    
    return is_roleplay, confidence_score, detected_triggers


def _check_dgm_post(user_message: str) -> Dict[str, any]:
    """
    Check if this is a DGM (Daedalus Game Master) post for scene setting.
    DGM posts should trigger roleplay sessions but never get responses.
    Enhanced to parse character names from DGM scene descriptions.
    Enhanced to detect DGM-controlled Elsie posts with [DGM][Elsie] pattern.
    Returns dict with is_dgm, action, triggers_roleplay, confidence, triggers, characters, dgm_controlled_elsie
    """
    # Check for [DGM] tag
    dgm_pattern = r'\[DGM\]'
    if not re.search(dgm_pattern, user_message, re.IGNORECASE):
        return {
            'is_dgm': False,
            'action': 'none',
            'triggers_roleplay': False,
            'confidence': 0.0,
            'triggers': [],
            'characters': [],
            'dgm_controlled_elsie': False,
            'elsie_content': ''
        }
    
    print(f"   🎬 DGM POST ANALYSIS:")
    
    # Check for DGM-controlled Elsie posts: [DGM][Elsie] pattern
    dgm_elsie_pattern = r'\[DGM\]\s*\[Elsie\]\s*(.*)'
    dgm_elsie_match = re.search(dgm_elsie_pattern, user_message, re.IGNORECASE | re.DOTALL)
    
    if dgm_elsie_match:
        elsie_content = dgm_elsie_match.group(1).strip()
        print(f"      🎭 DGM-CONTROLLED ELSIE DETECTED!")
        print(f"      📝 Elsie Content: '{elsie_content[:100]}{'...' if len(elsie_content) > 100 else ''}'")
        
        return {
            'is_dgm': True,
            'action': 'dgm_controlled_elsie',
            'triggers_roleplay': True,  # Still triggers roleplay if not already active
            'confidence': 1.0,
            'triggers': ['dgm_controlled_elsie'],
            'characters': ['Elsie'],  # Elsie is the character being controlled
            'dgm_controlled_elsie': True,
            'elsie_content': elsie_content
        }
    
    # Parse character names from DGM post
    characters_mentioned = _extract_characters_from_dgm_post(user_message)
    
    # Check for scene ending patterns
    ending_patterns = [
        r'\*end scene\*',
        r'\*roll credits\*',
        r'\*scene ends\*',
        r'\*fade to black\*',
        r'\*curtain falls\*',
        r'\*scene fades\*',
        r'end of scene',
        r'scene complete'
    ]
    
    message_lower = user_message.lower()
    for pattern in ending_patterns:
        if re.search(pattern, message_lower):
            print(f"      🎬 SCENE ENDING DETECTED: '{pattern}'")
            return {
                'is_dgm': True,
                'action': 'end_scene',
                'triggers_roleplay': False,
                'confidence': 0.0,
                'triggers': ['dgm_scene_end'],
                'characters': characters_mentioned,
                'dgm_controlled_elsie': False,
                'elsie_content': ''
            }
    
    # Check for scene setting patterns
    setting_patterns = [
        r'\*sets? the scene\*',
        r'\*scene begins\*',
        r'\*fade in\*',
        r'\*lights up\*',
        r'\*curtain rises\*',
        r'scene:',
        r'setting:',
        r'location:'
    ]
    
    is_scene_setting = False
    for pattern in setting_patterns:
        if re.search(pattern, message_lower):
            is_scene_setting = True
            print(f"      🎬 SCENE SETTING DETECTED: '{pattern}'")
            break
    
    # If it's a DGM post but not explicitly ending, assume it's scene setting
    if not is_scene_setting:
        print(f"      🎬 GENERAL DGM POST - Treating as scene setting")
    
    if characters_mentioned:
        print(f"      👥 CHARACTERS MENTIONED IN DGM POST: {characters_mentioned}")
    
    return {
        'is_dgm': True,
        'action': 'set_scene',
        'triggers_roleplay': True,
        'confidence': 1.0,  # DGM posts always trigger roleplay
        'triggers': ['dgm_scene_setting'],
        'characters': characters_mentioned,
        'dgm_controlled_elsie': False,
        'elsie_content': ''
    }


def _extract_characters_from_dgm_post(dgm_message: str) -> List[str]:
    """
    Extract character names from DGM scene descriptions.
    Looks for proper nouns that could be character names.
    Enhanced to detect character lists like "Fallo and Maeve".
    """
    characters = []
    
    # Remove the [DGM] tag for cleaner parsing
    clean_message = re.sub(r'\[DGM\]', '', dgm_message, flags=re.IGNORECASE).strip()
    
    print(f"      🔍 PARSING DGM MESSAGE FOR CHARACTERS: '{clean_message[:100]}{'...' if len(clean_message) > 100 else ''}'")
    
    # Titles to exclude from character names
    titles = {'Captain', 'Commander', 'Lieutenant', 'Doctor', 'Dr', 'Ensign', 'Chief', 'Admiral', 'Colonel', 'Major', 'Sergeant'}
    
    # STEP 1: Handle character lists with "and" - this is the most important for "Fallo and Maeve"
    list_patterns = [
        # "Name and Name" - simple two-character lists
        r'\b([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\b',
        # "Name, Name, and Name" - comma-separated lists
        r'\b([A-Z][a-z]+)(?:\s*,\s*([A-Z][a-z]+))*\s*,?\s*and\s+([A-Z][a-z]+)\b',
        # "Name, Name" - simple comma lists
        r'\b([A-Z][a-z]+)\s*,\s*([A-Z][a-z]+)\b',
    ]
    
    print(f"      📋 STEP 1: Checking for character lists...")
    for pattern in list_patterns:
        matches = re.finditer(pattern, clean_message)
        for match in matches:
            # Get all groups from the match (some may be None)
            for group_num in range(1, len(match.groups()) + 1):
                potential_name = match.group(group_num)
                if potential_name and potential_name not in titles and is_valid_character_name(potential_name):
                    name_normalized = potential_name.capitalize()
                    if name_normalized not in characters:
                        characters.append(name_normalized)
                        print(f"         👤 CHARACTER FOUND: '{name_normalized}' via list pattern '{pattern}'")
    
    # STEP 2: Handle titles with names - "Captain Smith and Lieutenant Jones"
    print(f"      📋 STEP 2: Checking for titled characters...")
    titled_patterns = [
        # Single titled character
        r'(?:Captain|Commander|Lieutenant|Doctor|Dr\.|Ensign|Chief|Admiral|Colonel|Major|Sergeant)\s+([A-Z][a-z]+)',
        # Two titled characters with "and"
        r'(?:Captain|Commander|Lieutenant|Doctor|Dr\.|Ensign|Chief|Admiral|Colonel|Major|Sergeant)\s+([A-Z][a-z]+)\s+and\s+(?:Captain|Commander|Lieutenant|Doctor|Dr\.|Ensign|Chief|Admiral|Colonel|Major|Sergeant)\s+([A-Z][a-z]+)',
    ]
    
    for pattern in titled_patterns:
        matches = re.finditer(pattern, clean_message)
        for match in matches:
            for group_num in range(1, len(match.groups()) + 1):
                potential_name = match.group(group_num)
                if potential_name and potential_name not in titles and is_valid_character_name(potential_name):
                    name_normalized = potential_name.capitalize()
                    if name_normalized not in characters:
                        characters.append(name_normalized)
                        print(f"         👤 CHARACTER FOUND: '{name_normalized}' via titled pattern '{pattern}'")
    
    # STEP 3: Look for individual character names in various contexts
    print(f"      📋 STEP 3: Checking for individual characters...")
    individual_patterns = [
        # Names followed by action verbs
        r'\b([A-Z][a-z]+)\s+(?:enters|arrives|walks|sits|stands|looks|turns|speaks|says|approaches|moves)',
        # Names in possessive form
        r'\b([A-Z][a-z]+)\'s\s+',
        # Names followed by descriptive text (but not titles)
        r'\b([A-Z][a-z]+),?\s+(?:the|a|an)\s+\w+',
        # Names at start of sentences (but not titles)
        r'(?:^|\.\s+)([A-Z][a-z]+)\s+',
    ]
    
    for pattern in individual_patterns:
        matches = re.finditer(pattern, clean_message)
        for match in matches:
            potential_name = match.group(1)
            if potential_name and potential_name not in titles and is_valid_character_name(potential_name):
                name_normalized = potential_name.capitalize()
                if name_normalized not in characters:
                    characters.append(name_normalized)
                    print(f"         👤 CHARACTER FOUND: '{name_normalized}' via individual pattern '{pattern}'")
    
    # STEP 4: Check for bracket format characters that might be in DGM posts
    print(f"      📋 STEP 4: Checking for bracket format...")
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, clean_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name) and name not in titles:
            name_normalized = ' '.join(word.capitalize() for word in name.split())
            if name_normalized not in characters:
                characters.append(name_normalized)
                print(f"         👤 CHARACTER FOUND: '[{name_normalized}]' via bracket format")
    
    print(f"      📋 TOTAL CHARACTERS EXTRACTED: {len(characters)} - {characters}")
    return characters


def is_roleplay_allowed_channel(channel_context: Dict = None) -> bool:
    """
    Check if roleplay is allowed in the current channel.
    Only allowed in threads and DMs, not general channels.
    """
    print(f"\n📍 CHANNEL RESTRICTION CHECK:")
    
    if not channel_context:
        # If no context provided, assume it's allowed (fallback for testing)
        print(f"   ⚠️  No channel context provided - allowing roleplay (testing fallback)")
        return True
    
    channel_type = channel_context.get('type', 'unknown')
    is_thread = channel_context.get('is_thread', False)
    is_dm = channel_context.get('is_dm', False)
    channel_name = channel_context.get('name', 'unknown')
    session_id = channel_context.get('session_id', '')
    
    print(f"   📋 Channel Details:")
    print(f"      - Name: {channel_name}")
    print(f"      - Type: {channel_type}")
    print(f"      - Is Thread: {is_thread}")
    print(f"      - Is DM: {is_dm}")
    print(f"      - Session ID: {session_id}")
    
    # FALLBACK THREAD DETECTION: If channel info is incomplete, try to detect threads
    # from other indicators
    fallback_thread_detected = False
    if channel_type == 'unknown' and not is_thread:
        # Some heuristics to detect threads when Discord API fails
        if len(session_id) > 15:  # Thread IDs are typically longer
            fallback_thread_detected = True
            print(f"      🔍 FALLBACK: Long session ID suggests thread")
        
        # If we have minimal info but it's not explicitly blocked, allow it
        if channel_name == 'unknown' and not is_dm:
            print(f"      🔍 FALLBACK: Unknown channel type, being permissive")
            fallback_thread_detected = True
    
    # Allow roleplay in:
    # - Direct Messages (DMs)
    # - Threads (replies to messages)
    # - Private channels
    # - Any channel with "thread" in the name/type
    # - Fallback thread detection
    allowed_conditions = []
    if is_dm:
        allowed_conditions.append("Direct Message")
    if is_thread:
        allowed_conditions.append("Thread")
    if fallback_thread_detected:
        allowed_conditions.append("Fallback Thread Detection")
    if channel_type in ['dm', 'thread', 'private']:
        allowed_conditions.append(f"Type: {channel_type}")
    if 'thread' in channel_type.lower():
        allowed_conditions.append(f"Type contains 'thread': {channel_type}")
    if 'thread' in channel_name.lower():
        allowed_conditions.append(f"Name contains 'thread': {channel_name}")
    
    # Special handling for Discord thread types
    discord_thread_types = ['public_thread', 'private_thread', 'news_thread']
    if channel_type in discord_thread_types:
        allowed_conditions.append(f"Discord thread type: {channel_type}")
    
    allowed = bool(allowed_conditions)
    
    # Block only if explicitly in restricted channels AND not a thread/DM
    restricted_conditions = []
    if channel_type in ['public', 'general', 'text'] and not is_thread and not is_dm and not fallback_thread_detected:
        if channel_name in ['general', 'announcements', 'public']:
            restricted_conditions.append(f"Restricted name: {channel_name}")
    
    # Override: Never block threads or DMs or unknown channels (be permissive)
    if is_thread or is_dm or channel_type in discord_thread_types or fallback_thread_detected or channel_type == 'unknown':
        restricted_conditions = []  # Clear any restrictions for threads/DMs/unknown
        if not allowed_conditions:  # If no other conditions triggered, add the override
            allowed_conditions.append("Permissive override")
            allowed = True
    
    if restricted_conditions:
        allowed = False
        print(f"   🚫 BLOCKED by: {', '.join(restricted_conditions)}")
    elif allowed_conditions:
        print(f"   ✅ ALLOWED by: {', '.join(allowed_conditions)}")
    else:
        print(f"   ❓ NO SPECIFIC RULES - defaulting to ALLOWED")
        allowed = True
    
    print(f"   🎯 FINAL DECISION: {'ROLEPLAY ALLOWED' if allowed else 'ROLEPLAY BLOCKED'}")
    return allowed


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
    speaking_character = _detect_speaking_character(user_message, rp_state)
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
    other_character_addressed = _check_if_other_character_addressed(user_message, rp_state)
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
    subtle_bar_response = _check_subtle_bar_interaction(user_message, rp_state)
    if subtle_bar_response:
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


def _check_subtle_bar_interaction(user_message: str, rp_state: 'RoleplayStateManager') -> bool:
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


def _extract_drink_from_emote(user_message: str) -> str:
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


def _detect_speaking_character(user_message: str, rp_state: 'RoleplayStateManager') -> str:
    """
    Detect if a character is speaking in this message (for auto-adding to participants).
    Looks for [Character Name] format or character names followed by dialogue/actions.
    Returns the character name if found, empty string otherwise.
    """
    # Check for bracket format first (most reliable)
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            name_normalized = ' '.join(word.capitalize() for word in name.split())
            return name_normalized
    
    # Check for character names followed by speaking/action indicators
    speaking_patterns = [
        r'\b([A-Z][a-z]+)\s+(?:says?|speaks?|replies?|responds?|asks?|tells?|whispers?|shouts?)',
        r'\b([A-Z][a-z]+)\s+(?:nods?|smiles?|laughs?|sighs?|looks?|turns?|moves?)',
        r'^([A-Z][a-z]+):\s+',  # "Name: dialogue"
        r'"[^"]*"\s*-?\s*([A-Z][a-z]+)',  # "dialogue" - Name
    ]
    
    for pattern in speaking_patterns:
        match = re.search(pattern, user_message)
        if match:
            potential_name = match.group(1)
            if is_valid_character_name(potential_name):
                return potential_name.capitalize()
    
    return ""


def _check_if_other_character_addressed(user_message: str, rp_state: 'RoleplayStateManager') -> str:
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


def extract_addressed_characters(user_message: str) -> List[str]:
    """
    Extract character names that are being directly addressed in the message.
    Looks for patterns like "Hey John," or "What do you think, Sarah?"
    Enhanced to detect [Character Name] format addressing.
    """
    addressed_characters = []
    
    # NEW: Check if message is addressing a character in brackets
    # Pattern: [Character Name] followed by dialogue or addressing
    bracket_addressing_pattern = r'\[([A-Z][a-zA-Z\s]+)\][^[]*(?:you|your|yourself)'
    bracket_matches = re.findall(bracket_addressing_pattern, user_message, re.IGNORECASE)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            addressed_characters.append(name)
            print(f"   👋 Bracket addressing detected: '[{name}]' being addressed")
    
    # Pattern 1: "Hey/Hi [Name]," at start of message
    greeting_pattern = r'^(?:hey|hi|hello|yo)\s+([A-Z][a-z]+),?\s'
    match = re.search(greeting_pattern, user_message, re.IGNORECASE)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
            print(f"   👋 Addressing pattern detected: 'Hey {name}'")
    
    # Pattern 2: "[Name], [statement]" - name at beginning with comma
    name_start_pattern = r'^([A-Z][a-z]+),\s+'
    match = re.search(name_start_pattern, user_message)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
            print(f"   👋 Name-start pattern detected: '{name},'")
    
    # Pattern 3: "[statement], [Name]" - name at end with comma
    name_end_pattern = r',\s+([A-Z][a-z]+)[.!?]?\s*$'
    match = re.search(name_end_pattern, user_message)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
            print(f"   👋 Name-end pattern detected: ', {name}'")
    
    # Pattern 4: "What do you think, [Name]?" - question directed at someone
    question_pattern = r'(?:what do you think|your thoughts|what about you),?\s+([A-Z][a-z]+)[.!?]?'
    match = re.search(question_pattern, user_message, re.IGNORECASE)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
            print(f"   👋 Question pattern detected: directed at '{name}'")
    
    # Pattern 5: Inside emotes - "*turns to [Name]*" or "*looks at [Name]*"
    emote_pattern = r'\*[^*]*(?:turns? to|looks? at|speaks? to|addresses?|faces?)\s+([A-Z][a-z]+)[^*]*\*'
    matches = re.finditer(emote_pattern, user_message, re.IGNORECASE)
    for match in matches:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
            print(f"   👋 Emote addressing detected: '{name}'")
    
    return list(set(addressed_characters))  # Remove duplicates


def is_valid_character_name(name: str) -> bool:
    """Check if a potential name is valid (not a common word)."""
    return (len(name) > 2 and 
            name not in ROLEPLAY_EXCLUDED_WORDS and
            name.lower() not in ['you', 'me', 'us', 'them', 'everyone', 'anyone', 'someone'])


def extract_character_names_from_emotes(user_message: str) -> List[str]:
    """
    Extract character names from emotes for speaker permanence.
    Uses Named Entity Recognition patterns and validation.
    Enhanced to detect [Character Name] format for multi-character play.
    """
    character_names = []
    
    # NEW: Extract character names from [Character Name] brackets
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            # Normalize and check for duplicates
            name_normalized = ' '.join(word.capitalize() for word in name.split())
            if name_normalized not in character_names:
                character_names.append(name_normalized)
                print(f"   👤 Character name detected from brackets: '[{name_normalized}]'")
    
    # Extract text within emotes
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    
    for emote in emotes:
        # Look for proper nouns (capitalized words) that could be names
        # Pattern: Word starting with capital letter, followed by lowercase
        potential_names = re.findall(r'\b([A-Z][a-z]+)\b', emote)
        
        for name in potential_names:
            if is_valid_character_name(name):
                # Normalize and check for duplicates
                name_normalized = name.capitalize()
                if name_normalized not in character_names:
                    character_names.append(name_normalized)
                    print(f"   👤 Character name detected from emote: '{name_normalized}' from emote: '{emote}'")
    
    return character_names  # Already deduplicated


def detect_roleplay_exit_conditions(user_message: str) -> Tuple[bool, str]:
    """
    Detect conditions that should exit roleplay mode.
    Returns (should_exit, reason)
    """
    message_lower = user_message.lower().strip()
    
    # 1. Explicit exit commands
    exit_commands = [
        'stop roleplay', 'stop roleplaying', 'exit roleplay', 'exit character',
        'end roleplay', 'break character', 'ooc mode', 'out of character'
    ]
    
    for command in exit_commands:
        if command in message_lower:
            return True, "explicit_command"
    
    # 2. OOC brackets
    ooc_patterns = [
        r'\(\([^)]*\)\)',  # ((text))
        r'//[^/]*',        # // text
        r'\[ooc[^\]]*\]',  # [ooc text]
        r'\booc:',         # ooc: text
    ]
    
    for pattern in ooc_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True, "ooc_brackets"
    
    # 3. Technical/factual questions (strong indicators of non-RP)
    technical_indicators = [
        'write a script', 'python code', 'javascript', 'programming',
        'how do i', 'what is the', 'explain how', 'definition of',
        'calculate', 'formula', 'algorithm', 'debug', 'error',
        'install', 'download', 'documentation', 'api', 'database'
    ]
    
    for indicator in technical_indicators:
        if indicator in message_lower:
            return True, "technical_query"
    
    # 4. Meta questions about the system
    meta_indicators = [
        'are you an ai', 'what model are you', 'who created you',
        'what are you', 'how do you work', 'what can you do',
        'your capabilities', 'your limitations'
    ]
    
    for indicator in meta_indicators:
        if indicator in message_lower:
            return True, "meta_query"
    
    return False, ""


class RoleplayStateManager:
    """
    Context & State Manager for roleplay sessions.
    Maintains speaker permanence and roleplay context.
    Enhanced with passive listening and channel restrictions.
    Now supports DGM-initiated sessions with special behavior.
    """
    
    def __init__(self):
        self.is_roleplaying = False
        self.participants = []
        self.setting_description = ""
        self.session_start_turn = 0
        self.confidence_history = []
        self.exit_condition_count = 0
        self.channel_context = {}
        self.listening_mode = False
        self.last_response_turn = 0
        self.listening_turn_count = 0  # Track consecutive listening turns
        self.last_interjection_turn = 0  # Track when we last interjected
        self.dgm_initiated = False  # Track if session was started by DGM
        self.dgm_characters = []  # Characters mentioned in DGM post
        
        # Simple implicit response tracking
        self.last_character_elsie_addressed = ""  # Who did Elsie last speak to
        self.last_character_spoke = ""  # Who spoke last (not Elsie)
        self.turn_history = []  # Simple turn tracking: [(turn_number, speaker)]
    
    def start_roleplay_session(self, turn_number: int, initial_triggers: List[str], channel_context: Dict = None, dgm_characters: List[str] = None):
        """Initialize a new roleplay session."""
        self.is_roleplaying = True
        self.session_start_turn = turn_number
        self.participants = []
        self.setting_description = ""
        self.confidence_history = []
        self.exit_condition_count = 0
        self.channel_context = channel_context or {}
        self.listening_mode = False
        self.last_response_turn = 0
        self.listening_turn_count = 0
        self.last_interjection_turn = 0
        
        # Reset simple tracking
        self.last_character_elsie_addressed = ""
        self.last_character_spoke = ""
        self.turn_history = []
        
        # Check if this is a DGM-initiated session
        self.dgm_initiated = 'dgm_scene_setting' in initial_triggers
        self.dgm_characters = dgm_characters or []
        
        # Add DGM-mentioned characters to participants
        if self.dgm_characters:
            for character in self.dgm_characters:
                self.add_participant(character, "dgm_mentioned", turn_number)
        
        print(f"\n🎭 ROLEPLAY SESSION STARTED:")
        print(f"   📅 Turn: {turn_number}")
        print(f"   🎯 Triggers: {initial_triggers}")
        print(f"   📍 Channel: {channel_context}")
        print(f"   🎬 DGM Initiated: {self.dgm_initiated}")
        if self.dgm_characters:
            print(f"   👥 DGM Characters: {self.dgm_characters}")
        print(f"   🎮 State: {'DGM PASSIVE MONITORING' if self.dgm_initiated else 'ACTIVE MONITORING'}")
    
    def add_participant(self, name: str, source: str, turn_number: int):
        """Add a new participant to the roleplay session."""
        # Normalize the name for comparison (handle case variations)
        name_normalized = name.strip()
        
        # Check if participant already exists (case-insensitive)
        for participant in self.participants:
            if participant['name'].lower() == name_normalized.lower():
                print(f"   👤 PARTICIPANT EXISTS: {name_normalized} (already tracked as '{participant['name']}')")
                # Update the turn number to show they're still active
                participant['last_mentioned_turn'] = turn_number
                return  # Already exists
        
        participant = {
            'name': name_normalized,
            'source': source,
            'mentioned_in_turn': turn_number,
            'last_mentioned_turn': turn_number
        }
        self.participants.append(participant)
        print(f"   👤 NEW PARTICIPANT ADDED:")
        print(f"      - Name: {name_normalized}")
        print(f"      - Source: {source}")
        print(f"      - Turn: {turn_number}")
        print(f"      - Total Tracked: {len(self.participants)}")
        print(f"      - DGM Session: {self.dgm_initiated}")
    
    def add_addressed_characters(self, character_names: List[str], turn_number: int):
        """Add characters that were addressed by others."""
        for name in character_names:
            self.add_participant(name, "addressed", turn_number)
    
    def set_listening_mode(self, listening: bool, reason: str = ""):
        """Set whether Elsie is in listening mode."""
        self.listening_mode = listening
        
        print(f"\n👂 LISTENING MODE UPDATE:")
        print(f"   🔄 Mode: {'LISTENING' if listening else 'ACTIVE'}")
        print(f"   📝 Reason: {reason}")
        
        if listening:
            self.listening_turn_count += 1
            print(f"   🔢 Listening Turn Count: {self.listening_turn_count}")
            print(f"   📊 Monitoring: {len(self.participants)} participants")
        else:
            self.listening_turn_count = 0  # Reset when not listening
            print(f"   🎬 Active response mode engaged")
    
    def should_interject_subtle_action(self, turn_number: int) -> bool:
        """
        Determine if Elsie should interject a subtle action to maintain presence.
        For DGM-initiated sessions: every 5-8 turns (more passive presence)
        For regular sessions: every 8-10 turns (less frequent)
        """
        if not self.listening_mode:
            return False
        
        # Different thresholds for DGM vs regular sessions
        if self.dgm_initiated:
            # DGM sessions: interject every 5-8 turns (more passive presence)
            min_turns = 5
            max_turns = 8
        else:
            # Regular sessions: interject every 8-10 turns (less frequent)
            min_turns = 8
            max_turns = 10
        
        # Check if we've reached the minimum threshold
        if self.listening_turn_count >= min_turns:
            return True
        
        # Also interject if it's been too long since last interjection
        turns_since_interjection = turn_number - self.last_interjection_turn
        max_silence = 15 if self.dgm_initiated else 20
        
        if turns_since_interjection >= max_silence:
            return True
        
        return False
    
    def mark_interjection(self, turn_number: int):
        """Mark that Elsie interjected a subtle action."""
        self.last_interjection_turn = turn_number
        self.listening_turn_count = 0  # Reset listening count after interjection
        print(f"   ✨ SUBTLE INTERJECTION MARKED - Turn {turn_number}")
    
    def mark_response_turn(self, turn_number: int):
        """Mark that Elsie responded on this turn."""
        self.last_response_turn = turn_number
        self.listening_turn_count = 0  # Reset listening count after active response
        
        # Track turn history
        self.turn_history.append((turn_number, "Elsie"))
        # Keep only last 10 turns
        if len(self.turn_history) > 10:
            self.turn_history.pop(0)
    
    def mark_character_turn(self, turn_number: int, character_name: str):
        """Mark that a character spoke on this turn."""
        self.last_character_spoke = character_name
        
        # Track turn history
        self.turn_history.append((turn_number, character_name))
        # Keep only last 10 turns
        if len(self.turn_history) > 10:
            self.turn_history.pop(0)
        
        print(f"   📝 CHARACTER TURN TRACKED: {character_name} (Turn {turn_number})")
    
    def set_last_character_addressed(self, character_name: str):
        """Set who Elsie last addressed."""
        self.last_character_elsie_addressed = character_name
        print(f"   👋 ELSIE ADDRESSED: {character_name}")
    
    def is_simple_implicit_response(self, current_turn: int, user_message: str) -> bool:
        """
        SIMPLE implicit response logic:
        - If the response comes from the last character Elsie addressed
        - AND Elsie spoke on the previous turn (not necessarily the last in history)
        - UNLESS the message contains other character names (redirecting conversation)
        """
        # Check if we have any turn history
        if not self.turn_history:
            return False
        
        # Find the most recent turn where Elsie spoke
        elsie_last_turn = None
        for turn_num, speaker in reversed(self.turn_history):
            if speaker == "Elsie":
                elsie_last_turn = turn_num
                break
        
        # Check if Elsie spoke recently (within 2 turns of current)
        if not elsie_last_turn or current_turn - elsie_last_turn > 2:
            return False
        
        # Extract character name from current message
        current_character = self._extract_current_speaker(user_message)
        if not current_character:
            return False
        
        # Check if this character is the one Elsie last addressed
        if (self.last_character_elsie_addressed and 
            current_character.lower() == self.last_character_elsie_addressed.lower()):
            
            # Check if the message contains other character names (redirecting)
            if self._message_contains_other_character_names(user_message):
                print(f"   🎯 Message contains other character names - not an implicit response")
                return False
            
            print(f"   💬 SIMPLE IMPLICIT RESPONSE DETECTED:")
            print(f"      - Elsie last addressed: {self.last_character_elsie_addressed}")
            print(f"      - Current speaker: {current_character}")
            print(f"      - Turn history: {self.turn_history[-3:] if len(self.turn_history) >= 3 else self.turn_history}")
            print(f"      - This is a follow-up from the character Elsie was addressing")
            
            return True
        
        return False
    
    def _extract_current_speaker(self, user_message: str) -> str:
        """Extract the character name from the current message."""
        # Check for [Character Name] format first
        bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
        bracket_matches = re.findall(bracket_pattern, user_message)
        for name in bracket_matches:
            name = name.strip()
            if is_valid_character_name(name):
                return ' '.join(word.capitalize() for word in name.split())
        
        # Check for character names in emotes
        character_names = extract_character_names_from_emotes(user_message)
        if character_names:
            return character_names[0]
        
        return ""
    
    def get_participant_names(self) -> List[str]:
        """Get list of all participant names."""
        return [p['name'] for p in self.participants]
    
    def get_active_participants(self, current_turn: int, max_turns_inactive: int = 10) -> List[str]:
        """Get list of participants who have been mentioned recently."""
        active = []
        for participant in self.participants:
            turns_since_mention = current_turn - participant.get('last_mentioned_turn', participant['mentioned_in_turn'])
            if turns_since_mention <= max_turns_inactive:
                active.append(participant['name'])
        return active
    
    def update_confidence(self, confidence_score: float):
        """Track confidence scores to detect sustained topic shifts."""
        self.confidence_history.append(confidence_score)
        # Keep only last 5 scores
        if len(self.confidence_history) > 5:
            self.confidence_history.pop(0)
    
    def check_sustained_topic_shift(self) -> bool:
        """Check if there's been a sustained shift away from roleplay."""
        if len(self.confidence_history) < 3:
            return False
        
        # If last 3 scores are all below threshold, it's a sustained shift
        recent_scores = self.confidence_history[-3:]
        return all(score < 0.15 for score in recent_scores)
    
    def increment_exit_condition(self):
        """Increment exit condition counter."""
        self.exit_condition_count += 1
    
    def should_exit_from_sustained_shift(self) -> bool:
        """Determine if we should exit due to sustained non-RP behavior."""
        return (self.check_sustained_topic_shift() or 
                self.exit_condition_count >= 2)
    
    def end_roleplay_session(self, reason: str):
        """End the current roleplay session."""
        print(f"   🎭 ROLEPLAY SESSION ENDED - Reason: {reason}")
        self.is_roleplaying = False
        self.participants = []
        self.setting_description = ""
        self.confidence_history = []
        self.exit_condition_count = 0
        self.channel_context = {}
        self.listening_mode = False
        self.last_response_turn = 0
    
    def is_dgm_session(self) -> bool:
        """Check if this is a DGM-initiated session."""
        return self.dgm_initiated
    
    def get_dgm_characters(self) -> List[str]:
        """Get characters that were mentioned in the DGM post."""
        return self.dgm_characters.copy()
    
    def add_speaking_character(self, character_name: str, turn_number: int):
        """
        Add a character who is speaking (even if not explicitly mentioned).
        This is for tracking characters as they participate in DGM sessions.
        """
        self.add_participant(character_name, "speaking", turn_number)
        print(f"   🗣️ SPEAKING CHARACTER ADDED: {character_name} (Turn {turn_number})")
    
    def is_implicit_response_to_elsie(self, current_turn: int, user_message: str) -> bool:
        """
        Check if this could be an implicit response to Elsie.
        Returns True if:
        1. Elsie responded on the previous turn (last_response_turn == current_turn - 1)
        2. No other characters have spoken since Elsie's response
        3. This is a single-character scene (only one participant)
        4. The message doesn't contain other character names (indicating it's directed elsewhere)
        """
        # Check if Elsie responded on the previous turn
        if self.last_response_turn != current_turn - 1:
            return False
        
        # Check if this is a single-character scene (or no other participants)
        if len(self.participants) > 1:
            return False
        
        # Check if the message contains other character names (indicating it's directed at them)
        if self._message_contains_other_character_names(user_message):
            print(f"   🎯 Message contains other character names - not an implicit response to Elsie")
            return False
        
        # If we get here, it's likely an implicit response to Elsie
        print(f"   💬 IMPLICIT RESPONSE DETECTED:")
        print(f"      - Elsie's last response: Turn {self.last_response_turn}")
        print(f"      - Current turn: {current_turn}")
        print(f"      - Participants: {len(self.participants)} ({self.get_participant_names()})")
        print(f"      - No other character names detected")
        print(f"      - This appears to be a response to Elsie's previous message")
        
        return True
    
    def _message_contains_other_character_names(self, user_message: str) -> bool:
        """
        Check if the message contains character names that would indicate
        it's directed at someone other than Elsie.
        NOTE: Ignores speaker brackets [Character Name] since those indicate who is speaking, not being addressed.
        """
        # Import here to avoid circular imports
        from ai_logic import extract_character_names_from_emotes, extract_addressed_characters, is_valid_character_name
        
        # Extract speaker from bracket format [Character Name] - this should be ignored
        speaker_from_bracket = self._extract_current_speaker(user_message)
        
        # Check for character names in emotes and addressing patterns
        character_names = extract_character_names_from_emotes(user_message)
        addressed_characters = extract_addressed_characters(user_message)
        
        # Combine all detected character names
        all_detected_names = set(character_names + addressed_characters)
        
        # Filter out Elsie's names (these are fine for implicit responses)
        elsie_names = {'elsie', 'elise', 'elsy', 'els', 'bartender', 'barkeep', 'barmaid', 'server', 'waitress'}
        
        # Filter out the speaker (from brackets) since that's who is talking, not being addressed
        other_character_names = [name for name in all_detected_names 
                               if (name.lower() not in elsie_names and 
                                   is_valid_character_name(name) and
                                   name.lower() != speaker_from_bracket.lower())]
        
        if other_character_names:
            print(f"      🎯 Other character names detected (excluding speaker '{speaker_from_bracket}'): {other_character_names}")
            return True
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert state to dictionary for logging/debugging."""
        return {
            'is_roleplaying': self.is_roleplaying,
            'participants': self.participants,
            'setting_description': self.setting_description,
            'session_start_turn': self.session_start_turn,
            'confidence_history': self.confidence_history,
            'exit_condition_count': self.exit_condition_count,
            'channel_context': self.channel_context,
            'listening_mode': self.listening_mode,
            'last_response_turn': self.last_response_turn,
            'listening_turn_count': self.listening_turn_count,
            'last_interjection_turn': self.last_interjection_turn,
            'dgm_initiated': self.dgm_initiated,
            'dgm_characters': self.dgm_characters
        }


# Global roleplay state manager instance
roleplay_state = RoleplayStateManager()


def get_roleplay_state() -> RoleplayStateManager:
    """Get the global roleplay state manager."""
    return roleplay_state
