"""AI logic for intent detection, guard rails, and conversation flow management"""

import re
from datetime import datetime
from typing import Optional, Tuple, Dict

from config import (
    estimate_token_count,
    OOC_PREFIX, OOC_KEYWORDS,
    MEETING_INFO_PATTERNS,
    SHIP_LOG_PATTERNS, SHIP_NAMES, LOG_SEARCH_KEYWORDS,
    CHARACTER_PATTERNS, CHARACTER_KEYWORDS, COMMON_CHARACTER_NAMES
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
