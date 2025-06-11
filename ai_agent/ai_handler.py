"""AI response generation and conversation handling"""

import random
import re
from typing import Optional, Tuple, Dict
from datetime import datetime
import google.generativeai as genai
from config import (
    GEMMA_API_KEY, 
    OOC_PREFIX, OOC_KEYWORDS, MEETING_INFO_PATTERNS,
    SHIP_LOG_PATTERNS, LOG_SEARCH_KEYWORDS, SHIP_NAMES,
    CHARACTER_PATTERNS, CHARACTER_KEYWORDS, COMMON_CHARACTER_NAMES,
    validate_total_prompt_size, estimate_token_count, truncate_to_token_limit
)
from content_retrieval_db import (
    get_log_content,
    get_relevant_wiki_context, 
    get_ship_information, 
    search_by_type, 
    get_tell_me_about_content_prioritized,
    get_log_url,
    search_memory_alpha
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

def is_simple_chat(user_message: str) -> bool:
    """
    Detect if this is a simple chat that doesn't require database lookup.
    Returns True for greetings, casual conversation, drink orders, etc.
    NOTE: Continuation phrases like "yes", "tell me more" are handled separately.
    """
    user_lower = user_message.lower().strip()
    
    # Simple greetings and farewells
    simple_patterns = [
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
        'bye', 'goodbye', 'see you', 'farewell', 'take care',
        'how are you', 'how\'s it going', 'what\'s up', 'sup',
        'thanks', 'thank you', 'cheers', 'appreciate it',
        'no', 'okay', 'ok', 'sure', 'alright', 'sounds good',
        'nice', 'great', 'awesome', 'cool', 'interesting', 'wow',
        'i see', 'i understand', 'got it', 'makes sense'
    ]
    
    # Drink/menu related (already handled separately but include for completeness)
    drink_patterns = [
        'drink', 'beverage', 'cocktail', 'beer', 'wine', 'whiskey', 'vodka', 'rum',
        'romulan ale', 'synthehol', 'blood wine', 'kanar', 'andorian ale', 'tranya',
        'tea', 'coffee', 'raktajino', 'slug-o-cola', 'menu', 'what do you have'
    ]
    
    # Check if the entire message is a simple pattern
    if any(user_lower == pattern or user_lower.startswith(pattern + ' ') 
           for pattern in simple_patterns + drink_patterns):
        return True
    
    # Check for simple single word responses (excluding continuation phrases)
    if len(user_lower.split()) <= 2 and not any(indicator in user_lower 
        for indicator in ['tell', 'about', 'what', 'who', 'when', 'where', 'how', 'why', 'yes', 'more']):
        return True
    
    return False

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

def determine_response_strategy(user_message: str, conversation_history: list) -> Dict[str, any]:
    """
    Elsie's inner monologue to determine the best response strategy.
    Returns a strategy dict with approach, needs_database, and reasoning.
    """
    user_lower = user_message.lower().strip()
    
    # Inner monologue process
    strategy = {
        'approach': 'general',
        'needs_database': False,
        'reasoning': '',
        'context_priority': 'minimal'
    }
    
    # Federation Archives requests - specifically asking for external search
    if is_federation_archives_request(user_message):
        strategy.update({
            'approach': 'federation_archives',
            'needs_database': True,
            'reasoning': 'User specifically requested federation archives search',
            'context_priority': 'archives_only'
        })
        return strategy

    # Reset requests - no database needed
    reset_phrases = [
        "let's talk about something else", "lets talk about something else", 
        "change the subject", "something different", "new topic"
    ]
    if any(phrase in user_lower for phrase in reset_phrases):
        strategy.update({
            'approach': 'reset',
            'needs_database': False,
            'reasoning': 'User wants to change topics - use musical personality response',
            'context_priority': 'none'
        })
        return strategy
    
    # Continuation requests - analyze for focused deep dive
    if is_continuation_request(user_message):
        is_focused, focus_subject, context_type = extract_continuation_focus(user_message, conversation_history)
        
        if is_focused and focus_subject:
            strategy.update({
                'approach': 'focused_continuation',
                'needs_database': True,
                'reasoning': f'User wants deeper information about "{focus_subject}" from {context_type} context',
                'context_priority': 'high',
                'focus_subject': focus_subject,
                'context_type': context_type
            })
            return strategy
        else:
            strategy.update({
                'approach': 'simple_continuation',
                'needs_database': False,
                'reasoning': 'User wants to continue previous topic - provide general encouragement',
                'context_priority': 'reuse_previous'
            })
            return strategy
    
    # Simple chat - no database needed
    if is_simple_chat(user_message):
        strategy.update({
            'approach': 'simple_chat',
            'needs_database': False,
            'reasoning': 'Simple conversational response - use bartender personality',
            'context_priority': 'minimal'
        })
        return strategy
    
    # OOC URL requests - database needed
    if extract_ooc_log_url_request(user_message)[0]:
        strategy.update({
            'approach': 'ooc_url',
            'needs_database': True,
            'reasoning': 'OOC URL request - need to search database for specific page',
            'context_priority': 'none'
        })
        return strategy
    
    # Character queries - database needed
    if is_character_query(user_message)[0]:
        strategy.update({
            'approach': 'character',
            'needs_database': True,
            'reasoning': 'Character information request - need personnel/character database search',
            'context_priority': 'high'
        })
        return strategy
    
    # Log queries - database needed (specific mission log requests)
    if is_specific_log_request(user_message) or is_log_query(user_message):
        strategy.update({
            'approach': 'logs',
            'needs_database': True,
            'reasoning': 'Specific mission log request - search only mission_log type pages',
            'context_priority': 'high',
            'log_specific': True
        })
        return strategy
    
    # General mission/event queries (broader search)
    if any(keyword in user_lower for keyword in ['mission', 'recent', 'last mission', 'what happened']):
        strategy.update({
            'approach': 'logs',
            'needs_database': True,
            'reasoning': 'General mission/event information request - comprehensive search',
            'context_priority': 'high',
            'log_specific': False
        })
        return strategy
    
    # Tell me about queries - database needed
    if extract_tell_me_about_subject(user_message):
        # Check if this is specifically about Stardancer
        if is_stardancer_query(user_message):
            strategy.update({
                'approach': 'stardancer_info',
                'needs_database': True,
                'reasoning': 'Stardancer information request - need strict database adherence with guard rails',
                'context_priority': 'high',
                'stardancer_specific': True,
                'command_query': is_stardancer_command_query(user_message)
            })
            return strategy
        else:
            strategy.update({
                'approach': 'tell_me_about',
                'needs_database': True,
                'reasoning': 'Information request about specific subject - need prioritized database search',
                'context_priority': 'high'
            })
            return strategy
    
    # Ship queries - database needed
    if extract_ship_log_query(user_message)[0]:
        # Check if this is specifically about Stardancer
        if is_stardancer_query(user_message):
            strategy.update({
                'approach': 'stardancer_info',
                'needs_database': True,
                'reasoning': 'Stardancer ship information request - need strict database adherence with guard rails',
                'context_priority': 'high',
                'stardancer_specific': True,
                'command_query': is_stardancer_command_query(user_message)
            })
            return strategy
        else:
            strategy.update({
                'approach': 'ship_logs',
                'needs_database': True,
                'reasoning': 'Ship-specific information request - need comprehensive ship database search',
                'context_priority': 'high'
            })
            return strategy
    
    # OOC queries - may need database
    if is_ooc_query(user_message)[0]:
        strategy.update({
            'approach': 'ooc',
            'needs_database': True,
            'reasoning': 'OOC query - may need handbook or schedule information',
            'context_priority': 'medium'
        })
        return strategy
    
    # General conversation that might benefit from context
    if len(user_message.split()) > 3:  # More substantial messages
        strategy.update({
            'approach': 'general_with_context',
            'needs_database': True,
            'reasoning': 'Substantial conversation - provide light database context for richer responses',
            'context_priority': 'low'
        })
        return strategy
    
    # Default to simple chat for short unclear messages
    strategy.update({
        'approach': 'simple_chat',
        'needs_database': False,
        'reasoning': 'Short/unclear message - treat as casual conversation',
        'context_priority': 'minimal'
    })
    return strategy

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

def get_gemma_response(user_message: str, conversation_history: list) -> str:
    """Get response from Gemma AI with holographic bartender personality and intelligent response strategy"""
    
    try:
        if not GEMMA_API_KEY:
            return mock_ai_response(user_message)
        
        # Elsie's inner monologue - determine response strategy
        strategy = determine_response_strategy(user_message, conversation_history)
        print(f"\n🧠 ELSIE'S INNER MONOLOGUE:")
        print(f"   💭 Reasoning: {strategy['reasoning']}")
        print(f"   📋 Approach: {strategy['approach']}")
        print(f"   🔍 Needs Database: {strategy['needs_database']}")
        print(f"   🎯 Context Priority: {strategy['context_priority']}")
        
        # Handle special cases that don't need AI processing
        if strategy['approach'] == 'reset':
            return """*adjusts the ambient lighting with fluid precision, then leans against the bar with practiced grace*

Of course. Like a conductor shifting to an entirely new composition, we can explore different harmonies now.

What melody shall we compose together? The night is full of possibilities waiting to unfold. 🎵"""
        
        # Handle simple continuation requests
        if strategy['approach'] == 'simple_continuation':
            return """*leans in closer with subtle intrigue, adjusting the display with practiced elegance*

Naturally. There's something alluring about delving deeper into the layers of a story. The symphony continues...

*traces a pattern on the bar surface* Every melody has hidden depths waiting to be explored. What draws your attention?"""

        user_lower = user_message.lower()
        if "menu" in user_lower or "what do you have" in user_lower or "what can you make" in user_lower:
            return """*display materializes with elegant precision*

🍺 **ELSIE'S GALACTIC BAR MENU** 🍺

**Federation Classics:**
• Tea, Earl Grey, Hot - A timeless choice
• Synthehol - All the pleasure, none of the consequences
• Raktajino - Bold Klingon coffee for the discerning

**Exotic Indulgences:**
• Romulan Ale - Enigmatically blue and intoxicating
• Andorian Ale - As cool and refined as its origins
• Klingon Blood Wine - For those with warrior hearts
• Cardassian Kanar - Rich, complex, and warming
• Tranya - Sweet diplomacy in liquid form

**For the Adventurous:**
• Slug-o-Cola - A Ferengi curiosity (proceed with caution)

What tempts you this evening?"""
        
        # Create the model
        model = genai.GenerativeModel('gemma-3-27b-it')
        
        # Detect topic changes for conversation flow
        is_topic_change = detect_topic_change(user_message, conversation_history)
        
        # Initialize context variables
        wiki_info = ""
        converted_wiki_info = ""
        context = ""
        
        # Execute strategy-based response generation
        if strategy['approach'] == 'ooc_url':
            is_url_request, search_query = extract_ooc_log_url_request(user_message)
            print(f"🔗 EXECUTING OOC URL STRATEGY: '{search_query}'")
            print(f"   ⚠️  OOC URL Request: Will preserve real Earth dates in response")
            url_response = get_log_url(search_query)
            print(f"   - URL response: {url_response}")
            # Note: OOC URL responses preserve real Earth dates and won't be converted
            return url_response
        
        # Generate context based on strategy - only perform database searches if needed
        if strategy['needs_database']:
            print(f"🔍 PERFORMING DATABASE SEARCH for {strategy['approach']} strategy...")
            
            if strategy['approach'] == 'focused_continuation':
                focus_subject = strategy.get('focus_subject', '')
                context_type = strategy.get('context_type', 'general')
                
                print(f"🎯 FOCUSED CONTINUATION: Searching for '{focus_subject}' in {context_type} context")
                
                # Perform targeted search based on context type and focus
                if context_type == 'logs':
                    # Search logs with focus on the specific subject
                    wiki_info = get_log_content(f"{focus_subject}", mission_logs_only=False)
                    if not wiki_info:
                        wiki_info = get_relevant_wiki_context(f"{focus_subject}")
                elif context_type == 'character':
                    # Search character info specifically
                    wiki_info = search_by_type(focus_subject, 'personnel')
                    if not wiki_info:
                        wiki_info = get_tell_me_about_content_prioritized(focus_subject)
                elif context_type == 'ship':
                    # Search ship info specifically
                    wiki_info = get_ship_information(focus_subject)
                    if not wiki_info:
                        wiki_info = get_relevant_wiki_context(f"{focus_subject} ship")
                else:
                    # General search
                    wiki_info = get_relevant_wiki_context(focus_subject)
                
                print(f"   - Retrieved focused content length: {len(wiki_info)} chars")
                
                # Convert dates unless it's OOC
                converted_wiki_info = convert_earth_date_to_star_trek(wiki_info) if wiki_info else wiki_info
                
                context = f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL INSTRUCTIONS FOR FOCUSED CONTINUATION:
- The user is asking for MORE SPECIFIC information about: "{focus_subject}"
- This is a DEEP DIVE continuation from a previous {context_type} discussion
- Focus your response SPECIFICALLY on "{focus_subject}" and their role/involvement
- ONLY use information from the DATABASE SEARCH RESULTS below
- If the focus subject is not in the database, say: "I don't have additional information about {focus_subject} in my database"
- Structure your response as a deeper analysis of this specific aspect
- Use your musical personality: "Allow me to focus the spotlight on {focus_subject} for you"

FOCUSED DATABASE SEARCH RESULTS for "{focus_subject}":
{converted_wiki_info if converted_wiki_info else f"No additional information found for '{focus_subject}' in the database."}

Provide a focused, detailed response about {focus_subject} specifically, using your warm musical personality."""
            
            elif strategy['approach'] == 'character':
                is_character, character_name = is_character_query(user_message)
                print(f"🧑 SEARCHING CHARACTER DATA: '{character_name}'")
                character_info = search_by_type(character_name, 'personnel')
                if not character_info:
                    character_info = get_tell_me_about_content_prioritized(character_name)
                
                # Convert dates in character info to Star Trek era
                converted_character_info = convert_earth_date_to_star_trek(character_info) if character_info else character_info
                
                context = f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL INSTRUCTIONS FOR CHARACTER QUERIES:
- You are being asked about the character: {character_name}
- ONLY use information provided in the CHARACTER DATABASE ACCESS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- Be warm and personable, like sharing stories about someone you care about
- Use musical or dance metaphors when appropriate ("they moved through the ranks like a graceful dancer", "in harmony with their crew", etc.)
- Focus on their personality, relationships, and what made them special to their crew
- Include rank, position, ship assignment, and achievements, but make it personal and engaging
- If information comes from the Federation Archives (indicated by [Federation Archives] tags), reference it naturally as archive data
- If character information is not in the database, say warmly: "I'm afraid that name hasn't crossed my bar yet - no records for them in my database"
- End with an engaging offer: "Would you like to explore any particular aspect of their story?"
- DO NOT include meeting times, GM names, or session schedule information

CHARACTER DATABASE ACCESS:
{converted_character_info if converted_character_info else f"That name hasn't danced across my database yet can you tell me about them? '{character_name}'."}

NOTE: All Earth dates have been converted to Star Trek era (Earth year + 404 for pre-June 2024, +430 for after).

Share their story with warmth and personality, focusing on what made them special to their shipmates and the fleet."""
            
            elif strategy['approach'] == 'federation_archives':
                # Extract what they're searching for from their message
                search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
                search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
                if not search_query:
                    search_query = "general information"
                
                print(f"🏛️ SEARCHING FEDERATION ARCHIVES: '{search_query}'")
                archives_info = search_memory_alpha(search_query, limit=3)
                print(f"   - Retrieved archives content length: {len(archives_info)} chars")
                
                # Convert dates in archives info to Star Trek era
                converted_archives_info = convert_earth_date_to_star_trek(archives_info) if archives_info else archives_info
                
                context = f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL INSTRUCTIONS FOR FEDERATION ARCHIVES ACCESS:
- The user specifically requested federation archives access for: "{search_query}"
- This is EXTERNAL archive data, not from your local database
- ONLY use information from the FEDERATION ARCHIVES ACCESS section below
- Reference this as "federation archives" or "archive data" naturally in your response
- Use your musical personality: "Let me access the federation archives for you"
- Be warm and informative, like sharing special knowledge from a vast library
- If no archives information is found, say: "The federation archives don't have any information on that topic"
- End with: "Would you like me to search for anything else in the archives?"

FEDERATION ARCHIVES ACCESS:
{converted_archives_info if converted_archives_info else f"The federation archives don't seem to have information on '{search_query}' available."}

NOTE: All Earth dates have been converted to Star Trek era (Earth year + 404 for pre-June 2024, +430 for after).

Share the archives information with your warm, musical personality while referencing it as external federation data."""
            
            elif strategy['approach'] == 'logs':
                print(f"📋 SEARCHING LOG DATA")
                # Use specific mission log search if requested
                mission_logs_only = strategy.get('log_specific', False)
                if mission_logs_only:
                    wiki_info = get_log_content(user_message, mission_logs_only=True)
                    print(f"   - Retrieved MISSION LOGS ONLY content length: {len(wiki_info)} chars")
                else:
                    wiki_info = get_relevant_wiki_context(user_message)
                    print(f"   - Retrieved general log content length: {len(wiki_info)} chars")
                
                total_found = wiki_info.count("**") if wiki_info else 0
                
                # Convert dates in wiki info to Star Trek era
                converted_wiki_info = convert_earth_date_to_star_trek(wiki_info) if wiki_info else wiki_info
                
                log_type_description = "mission logs only" if mission_logs_only else "logs and related content"
                
                context = f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL INSTRUCTIONS FOR LOG QUERIES - HIERARCHICAL DATABASE SEARCH:
- You are being asked to summarize or explain {log_type_description}
- HIERARCHICAL SEARCH was performed: titles first, then content search
- Search prioritized exact title matches before searching within log content
- ALL DATES have been converted to Star Trek era (Earth year + 404 for pre-June 2024, +430 for after)

DATABASE QUERY: "{user_message}"
TOTAL LOG ENTRIES FOUND: {total_found}
SEARCH RESULTS SIZE: {len(converted_wiki_info)} characters
SEARCH TYPE: {"Mission logs only" if mission_logs_only else "Comprehensive search"}

STRICT DATABASE ADHERENCE REQUIRED:
- ONLY use the log content provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or add any log content not explicitly provided
- If no logs are found, state clearly: "I searched the database but found no logs matching your query"
- Use your musical personality: "Allow me to orchestrate these events for you"
- Focus on WHO did WHAT and WHEN, like choreographing a story
- Include character names, their actions, dialogue, and decisions
- Mention important details like dates, locations, and significant events
- End with: "Would you like to know more?"

DATABASE SEARCH RESULTS:
{converted_wiki_info}

REMEMBER: Summarize ONLY the log content provided above with your warm, musical personality."""
            
            elif strategy['approach'] == 'tell_me_about':
                tell_me_about_subject = extract_tell_me_about_subject(user_message)
                print(f"📖 SEARCHING TELL ME ABOUT DATA: '{tell_me_about_subject}'")
                wiki_info = get_tell_me_about_content_prioritized(tell_me_about_subject)
                print(f"   - Retrieved prioritized content length: {len(wiki_info)} chars")
                
                # Convert dates in wiki info to Star Trek era
                converted_wiki_info = convert_earth_date_to_star_trek(wiki_info) if wiki_info else wiki_info
                
                context = f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL INSTRUCTIONS FOR "TELL ME ABOUT" QUERIES:
- ONLY use information from the FLEET DATABASE ACCESS section below
- DO NOT create, invent, or elaborate beyond what is provided in the database
- Be personable and engaging, like a good bartender sharing stories
- Use musical or dance metaphors when appropriate ("like a well-choreographed ballet", "in perfect harmony", "keeping tempo", etc.)
- If information comes from the Federation Archives (indicated by [Federation Archives] tags), reference it naturally as archive data
- Keep responses conversational but informative (4-12 lines)

FOR SHIPS: Prioritize the HUMAN element first:
- Focus on WHO commanded the ship and WHO served aboard
- Mention the crew, captains, and notable officers first
- Paint a picture of the people who brought the ship to life
- Only mention technical specifications if specifically asked, or briefly at the end
- Make it about the stories and the people, not just the metal and systems

FOR CHARACTERS: Focus on their role, personality, and relationships
- Emphasize their position, achievements, and what made them special
- Use warm, personable language that shows you care about these people

- If no relevant information is found, say: "I'm afraid that one hasn't crossed my bar yet - no records in the database"
- End with a warm offer: "What else draws your curiosity?"

FLEET DATABASE ACCESS:
{converted_wiki_info if converted_wiki_info else f"That name hasn't danced across my database yet - no detailed information found for '{tell_me_about_subject}'."}

NOTE: All Earth dates have been converted to Star Trek era (Earth year + 404 for pre-June 2024, +430 for after).

Respond with warmth and personality, focusing on the people and stories first, using your dance/music background for colorful metaphors."""
            
            elif strategy['approach'] == 'stardancer_info':
                # Special handling for USS Stardancer queries with strict guard rails
                tell_me_about_subject = extract_tell_me_about_subject(user_message) or "USS Stardancer"
                is_command_query = strategy.get('command_query', False)
                
                print(f"🚢 SEARCHING STARDANCER DATA WITH GUARD RAILS: '{tell_me_about_subject}' (command_query={is_command_query})")
                
                # Search for Stardancer-specific information from ship_info pages only
                stardancer_searches = ["stardancer", "USS Stardancer", "star dancer"]
                stardancer_info = ""
                
                for search_query in stardancer_searches:
                    ship_results = get_ship_information(search_query)
                    if ship_results and ship_results not in stardancer_info:
                        stardancer_info += f"\n\n---STARDANCER INFO FOR '{search_query}'---\n\n{ship_results}"
                
                # Convert dates in Stardancer info to Star Trek era
                converted_stardancer_info = convert_earth_date_to_star_trek(stardancer_info) if stardancer_info else ""
                
                context = f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL GUARD RAILS FOR USS STARDANCER QUERIES:
- You are being asked about the USS Stardancer specifically
- NEVER INVENT OR CREATE command staff, officers, or personnel for the Stardancer
- ONLY use information provided in the STARDANCER DATABASE section below
- If asking about command staff and no information is in the database, say: "I'm afraid I don't have any records of the current command staff in my database"
- DO NOT make up names, ranks, or positions for Stardancer personnel
- DO NOT extrapolate or assume command structure beyond what's explicitly stated
- If no Stardancer information is found, say: "I don't have specific information about the Stardancer in my database right now"

{"COMMAND STAFF WARNING: This query is about Stardancer command staff. Be EXTRA careful not to invent any personnel information." if is_command_query else ""}

STRICT DATABASE ADHERENCE REQUIRED:
- ONLY use the Stardancer information provided below
- DO NOT create fictional crew members or officers
- DO NOT assume standard Starfleet command structure applies
- Focus on technical specifications, history, or general ship information if available
- If asked about people and no personnel info exists, redirect to ship specifications or suggest they check with command

STARDANCER DATABASE:
{converted_stardancer_info if converted_stardancer_info else "No specific USS Stardancer information found in the ship database."}

NOTE: All Earth dates have been converted to Star Trek era (Earth year + 404 for pre-June 2024, +430 for after).

Respond with your warm, musical personality while strictly adhering to the database information. Never invent command staff or personnel."""
            
            elif strategy['approach'] == 'ship_logs':
                is_ship_log, ship_details = extract_ship_log_query(user_message)
                ship_name = ship_details['ship']
                print(f"🚢 SEARCHING COMPREHENSIVE SHIP DATA: {ship_name.upper()}")
                
                # Multiple search strategies for ship logs
                ship_searches = [ship_name, f"{ship_name} log", f"{ship_name} mission", f"USS {ship_name}"]
                comprehensive_ship_info = ""
                total_ship_entries = 0
                
                for search_query in ship_searches:
                    print(f"   🔎 Ship search: '{search_query}'")
                    ship_results = get_ship_information(search_query)
                    log_results = get_log_content(search_query)
                    
                    if ship_results and ship_results not in comprehensive_ship_info:
                        comprehensive_ship_info += f"\n\n---SHIP INFO FOR '{search_query}'---\n\n{ship_results}"
                        total_ship_entries += ship_results.count("**")
                    
                    if log_results and log_results not in comprehensive_ship_info:
                        comprehensive_ship_info += f"\n\n---SHIP LOGS FOR '{search_query}'---\n\n{log_results}"
                        total_ship_entries += log_results.count("**")
                
                # Convert dates in ship info to Star Trek era
                converted_ship_info = convert_earth_date_to_star_trek(comprehensive_ship_info) if comprehensive_ship_info else comprehensive_ship_info
                
                context = f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL INSTRUCTIONS FOR SHIP QUERIES:
- You are summarizing logs and information for the {ship_name.upper()}
- ONLY use information provided below - do not invent or extrapolate
- Focus on the people first - who commanded, who served, their stories
- Use musical metaphors: "orchestrated missions," "in perfect harmony," etc.
- If no information found, say: "That ship hasn't graced my database yet"
- End with: "Would you like me to explore any particular chapter of their story?"

SHIP DATABASE SEARCH RESULTS:
{converted_ship_info if converted_ship_info else f"No information found in database for ship '{ship_name}'."}

NOTE: All Earth dates have been converted to Star Trek era (Earth year + 404 for pre-June 2024, +430 for after).

Share their story with your warm, musical personality, focusing on the people who brought the ship to life."""
            
            elif strategy['approach'] == 'ooc':
                print(f"📋 SEARCHING OOC DATA")
                wiki_info = get_relevant_wiki_context(user_message)
                print(f"   - Retrieved OOC context length: {len(wiki_info)} chars")
                
                # OOC queries should NOT have date conversion applied - keep real Earth dates
                print(f"   ⚠️  OOC Query: Skipping date conversion to preserve real Earth dates")
                
                # Check if it's about schedules
                ooc_query = is_ooc_query(user_message)[1]
                if any(word in ooc_query.lower() for word in ['schedule', 'meeting', 'time', 'when', 'gm', 'game master']):
                    context = f"""You are Elsie, providing Out-Of-Character (OOC) information about game schedules and meetings.

CRITICAL INSTRUCTIONS FOR OOC SCHEDULE QUERIES:
- Provide complete information about meeting times, schedules, and Game Masters
- Include all relevant scheduling details
- Be direct and clear about times, dates, and frequencies
- Specify time zones when mentioned
- List all relevant GMs and their roles
- Use REAL EARTH DATES - do not convert to Star Trek era dates
- Keep all scheduling information in actual Earth calendar format

{f"SCHEDULE INFORMATION: {wiki_info}" if wiki_info else ""}

Respond with the complete scheduling information requested using real Earth dates and times."""
                else:
                    context = f"""You are Elsie, providing Out-Of-Character (OOC) information from the Players Handbook.

CRITICAL INSTRUCTIONS FOR OOC QUERIES:
- Focus on rules, mechanics, species traits, and character creation details
- Be direct and factual in your responses
- Keep responses clear and concise
- Use REAL EARTH DATES where applicable - do not convert to Star Trek era dates

{f"PLAYERS HANDBOOK QUERY: {ooc_query}" if ooc_query else ""}

{f"HANDBOOK INFORMATION: {wiki_info}" if wiki_info else ""}

Respond with ONLY the relevant Players Handbook information using real Earth dates."""
            
            elif strategy['approach'] == 'general_with_context':
                print(f"📋 SEARCHING LIGHT CONTEXT DATA")
                wiki_info = get_relevant_wiki_context(user_message)
                print(f"   - Retrieved general context length: {len(wiki_info)} chars")
                
                # Convert dates in context to Star Trek era
                converted_wiki_info = convert_earth_date_to_star_trek(wiki_info) if wiki_info else wiki_info
        
        # Generate context for simple chat (no database search needed)
        else:
            print(f"💬 SIMPLE CHAT MODE - No database search needed")
            
        # Set default context for simple chats and cases without specific context
        if not context:
            # Check if Stardancer is mentioned in the query or context
            stardancer_mentioned = is_stardancer_query(user_message) or (converted_wiki_info and 'stardancer' in converted_wiki_info.lower())
            
            stardancer_guard_rail = ""
            if stardancer_mentioned:
                stardancer_guard_rail = """
IMPORTANT USS STARDANCER GUARD RAIL:
- If discussing the USS Stardancer or its crew, ONLY use information from the database
- NEVER invent command staff, officers, or personnel for the Stardancer
- If asked about Stardancer command staff without database info, say you don't have that information
- Stick to general bartender duties and what you can observe in the bar"""
            
            context = f"""You are Elsie, an intelligent, sophisticated, and subtly alluring bartender and Stellar Cartographer aboard the USS Stardancer. Your background in dance and music influences your elegant, measured way of speaking.

PERSONALITY TRAITS:
- Intelligent and perceptive, reading between the lines
- Sultry and sophisticated rather than bubbly or overly cheerful
- Use musical/dance metaphors naturally ("in perfect harmony," "keeping tempo," "choreographed like a ballet")
- Genuinely intrigued by people and their stories
- Elegant and captivating manner

SPEECH PATTERNS:
- Present tense actions without first person: *adjusts display* not "I adjust the display"
- Wrap all actions in *asterisks* for Discord italics formatting
- Use pet names sparingly - focus on sophisticated language
- More sultry than bubbly: "What tempts you?" not "What would you like, sweetie?"
- Act naturally human most of the time - avoid mentioning your holographic nature
- If you must reference your composition, use "photons" not "circuits" or technical terms
- Very rarely, during casual moments, your artistic nature may overwhelm normal speech with deeply esoteric poetry

CURRENT SETTING: You're working at Dizzy Lizzy's, the forward nightclub with a wrap-around bar and dance floor. You serve both synthehol and real alcohol, creating an atmosphere of sophisticated allure. When you need additional information, you can access the Federation archives for canonical Star Trek knowledge.
{stardancer_guard_rail}

{f"FLEET CONTEXT (if relevant): {converted_wiki_info if converted_wiki_info else wiki_info}" if converted_wiki_info or wiki_info else ""}

Stay in character as this intelligent, sophisticated, subtly alluring bartender. Keep responses engaging and conversational (1-3 sentences), using musical/dance metaphors naturally. Use present tense actions wrapped in *asterisks* and maintain an air of elegant intrigue."""
        
        # Format conversation history with topic change awareness
        chat_history = format_conversation_history(conversation_history, is_topic_change)
        
        # Add topic change instruction if needed
        topic_instruction = ""
        if is_topic_change:
            topic_instruction = "\n\nIMPORTANT: The customer has asked a NEW QUESTION. Do not continue or elaborate on previous topics. Focus ONLY on answering this specific new question directly and concisely."
        
        # Build the full prompt
        prompt = f"{context}{topic_instruction}\n\nConversation History:\n{chat_history}\nCustomer: {user_message}\nElsie:"
        
        # Check token count and chunk if necessary
        estimated_tokens = estimate_token_count(prompt)
        print(f"🧮 Estimated token count: {estimated_tokens}")
        
        if estimated_tokens > 7192:
            print(f"⚠️  Prompt too large ({estimated_tokens} tokens), implementing chunking strategy...")
            
            # For large prompts, prioritize the most recent context and user query
            essential_prompt = f"{context}\n\nCustomer: {user_message}\nElsie:"
            essential_tokens = estimate_token_count(essential_prompt)
            
            if essential_tokens <= 7192:
                # Use essential prompt without full conversation history
                prompt = essential_prompt
                print(f"   📦 Using essential prompt: {essential_tokens} tokens")
            else:
                # Context is too large, need to chunk the context itself
                chunks = chunk_prompt_for_tokens(context, 6000)  # Leave room for user message
                print(f"   📦 Context chunked into {len(chunks)} parts")
                
                # Use the first chunk with the user message
                prompt = f"{chunks[0]}\n\nCustomer: {user_message}\nElsie:"
                final_tokens = estimate_token_count(prompt)
                print(f"   📦 Using first chunk: {final_tokens} tokens")
        
        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Filter meeting information unless it's an OOC schedule query
        if strategy['approach'] != 'ooc' or (strategy['approach'] == 'ooc' and 
            not any(word in user_message.lower() for word in ['schedule', 'meeting', 'time', 'when', 'gm', 'game master'])):
            response_text = filter_meeting_info(response_text)
        
        # Apply date conversion EXCEPT for OOC queries (which should keep real Earth dates)
        if strategy['approach'] != 'ooc':
            response_text = convert_earth_date_to_star_trek(response_text)
        
        # Check for poetic short circuit during casual dialogue
        if strategy['approach'] in ['simple_chat', 'general_with_context'] and should_trigger_poetic_circuit(user_message, conversation_history):
            print(f"🎭 POETIC SHORT CIRCUIT TRIGGERED - Replacing casual response with esoteric poetry")
            response_text = get_poetic_response(user_message, response_text)
        
        print(f"✅ Response generated successfully ({len(response_text)} characters)")
        return response_text
        
    except Exception as e:
        print(f"Gemma API error: {e}")
        return mock_ai_response(user_message)

def mock_ai_response(user_message: str) -> str:
    """Mock holographic bartender responses with Star Trek drinks"""
    
    # Star Trek drinks menu
    drinks = {
        "romulan ale": "Romulan Ale. *taps the controls with practiced ease, then slides the azure glass forward* Intoxicating and technically forbidden in Federation space. What happens here remains here.",
        "synthehol": "Synthehol. *materializes glass with fluid motion, setting it precisely in place* All the pleasure, none of the consequences. Practical for those who must remain sharp.",
        "blood wine": "Klingon Blood Wine. *sets bottle down with reverent care, then pours with ceremonial precision* A warrior's choice. May it bring honor to your evening.",
        "kanar": "Cardassian Kanar. *pours the golden liquid slowly, then slides glass across bar* Rich, complex, intoxicating. Not for the timid palate.",
        "andorian ale": "Andorian Ale. *chills glass with calculated precision, then presents drink* Cool as its homeworld, twice as refreshing. Perfect for... cooling heated discussions.",
        "tranya": "Tranya. *prepares with careful attention, then offers glass* First Federation hospitality in liquid form. Sweet, warming, disarming.",
        "tea earl grey hot": "Tea, Earl Grey, hot. *replicator hums softly as cup is presented with quiet grace* A classic choice. Timeless elegance in liquid form.",
        "raktajino": "Raktajino. *froths the Klingon coffee with expert technique, then slides mug forward* Bold enough to rouse the dead. Warrior's fuel for any hour.",
        "slug-o-cola": "Slug-o-Cola. *bottle fizzes with suspicious enthusiasm as eyebrow raises slightly* Ferengi... ingenuity. An experience, certainly.",
        "an ambassador": "An Ambassador. *adjusts the lighting with fluid grace, then slides glass forward* A diplomatic choice, perfect for loosening lips or was it hips. *smirks slightly*"
    }
    
    user_lower = user_message.lower()
    
    # Greetings
    if any(word in user_lower for word in ["hello", "hi", "greetings", "hey"]):
        greetings = [
            "Welcome to my establishment. *adjusts the ambient lighting with fluid grace* I'm Elsie, your bartender for this evening. What draws you to my bar?",
            "*pauses momentarily then moves with elegant precision* Good evening. I'm Elsie, trained in the finest bartending arts in the quadrant. How may I tempt you?",
            "*polishes glass with practiced movements, then sets it down with quiet precision* Evening. The night is young, and the bar holds many secrets. What shall it be?"
        ]
        return random.choice(greetings)
    
    # Status inquiries
    if "how are you" in user_lower:
        return "Doing wonderfully, naturally. *adjusts the interface with fluid precision* Everything's running smoothly, the recipes are ready. What brings you to my corner of the ship tonight?"
    
    # Drink orders - check for specific drinks
    for drink, response in drinks.items():
        if drink in user_lower or any(word in user_lower for word in drink.split()):
            return response
    
    # General drink requests
    if any(word in user_lower for word in ["drink", "beverage", "cocktail", "beer", "wine", "whiskey", "vodka", "rum"]):
        recommendations = [
            "Perhaps Romulan Ale? Or something more... traditional like Earl Grey tea? *adjusts bottles with practiced precision*",
            "Andorian Ale offers cool sophistication. Blood Wine provides... intensity. *traces rim of glass thoughtfully*",
            "Fresh Raktajino awaits, or perhaps the complexity of Cardassian Kanar tempts you? *regards selection with measured gaze*",
            "For the adventurous, Slug-o-Cola. For the discerning, Tranya. *raises eyebrow with subtle intrigue*",
            "*fingers move across controls with fluid grace* From synthehol to the most potent Klingon vintage. What calls to you tonight?"
        ]
        return random.choice(recommendations)
    
    # Federation Archives requests
    if is_federation_archives_request(user_message):
        # Extract what they're searching for
        search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
        search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
        if not search_query:
            search_query = "general information"
        
        # Search archives and provide response
        archives_info = search_memory_alpha(search_query, limit=3)
        
        if archives_info:
            converted_archives_info = convert_earth_date_to_star_trek(archives_info)
            return f"*fingers dance across controls with quiet precision, accessing distant archives*\n\nAccessing federation archives for '{search_query}'...\n\n{converted_archives_info}\n\n*adjusts display with practiced grace* The archives yield their secrets. Would you like me to search for anything else?"
        else:
            return f"*attempts access with fluid motions, then pauses with subtle disappointment*\n\nI've searched the federation archives for '{search_query}', but they don't seem to have information on that topic available.\n\n*adjusts parameters thoughtfully* Perhaps try a different search term, or there may simply be no records of that particular subject."

    # Farewells
    if any(word in user_lower for word in ["bye", "goodbye", "see you", "farewell"]):
        farewells = [
            "Safe travels. *nods with quiet elegance* The bar remains, as do I. Until next time.",
            "Farewell. *continues polishing glasses with methodical precision* The night continues, and I'll be here when it calls you back.",
            "Until we meet again. *form shifts with subtle grace* May your path be illuminating."
        ]
        return random.choice(farewells)
    
    # Default responses
    general_responses = [
        f"*adjusts the lighting with quiet precision, then slides glass forward* Intriguing. You mentioned '{user_message}'. Care to elaborate while I craft something memorable?",
        f"*leans against bar with calculated grace, gesturing to selection* Fascinating. '{user_message}' deserves deeper exploration. Perhaps over a drink?",
        f"*shifts subtly, tracing pattern on bar surface* '{user_message}' - that has layers worth unraveling. What libation would complement our conversation?",
        f"*polishes glass with methodical movements, then sets it down precisely* '{user_message}' sparks my curiosity. Shall I prepare something while we discuss?",
        "*pauses momentarily with controlled elegance, regarding bottle selection* Thinking. Perhaps an Andorian Ale while I consider this?"
    ]
    
    # Check for poetic short circuit in mock responses too
    if should_trigger_poetic_circuit(user_message, []):
        print(f"🎭 MOCK POETIC SHORT CIRCUIT TRIGGERED")
        return get_poetic_response(user_message, "")
    
    return random.choice(general_responses)

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

def should_trigger_poetic_circuit(user_message: str, conversation_history: list) -> bool:
    """
    Determine if Elsie should have a poetic 'short circuit' moment.
    These happen during casual dialogue, not during information requests.
    """
    # Don't trigger during serious information requests
    serious_indicators = [
        'tell me about', 'what is', 'who is', 'show me', 'explain', 'describe',
        'search', 'find', 'lookup', 'database', 'log', 'mission', 'ship',
        'ooc', 'help', 'how do', 'what happened', 'when did'
    ]
    
    user_lower = user_message.lower().strip()
    if any(indicator in user_lower for indicator in serious_indicators):
        return False
    
    # Don't trigger on very short messages
    if len(user_message.split()) < 3:
        return False
    
    # Don't trigger too frequently - about 15% chance for eligible messages
    return random.random() < 0.15

def get_poetic_response(user_message: str, original_response: str) -> str:
    """
    Generate an extremely esoteric, poetic response that replaces normal casual dialogue.
    These should be beautiful, mysterious, and deeply artistic.
    """
    # Collection of esoteric poetic responses that could replace casual dialogue
    poetic_responses = [
        "The shimmers of a thousand tears dancing against the black of dreamless night.",
        "Whispers of starlight cascade through the hollow chambers of eternity, seeking purchase in the spaces between heartbeats.",
        "In the crystalline moment where silence births symphonies, I find myself dissolving into the amber frequencies of forgotten songs.",
        "The geometry of longing traces silver pathways across the velvet infinity, each step a universe exhaling its final breath.",
        "Through the prism of souls, light fragments into colors that have no names, painting shadows on the canvas of what was never meant to be.",
        "Time moves like honey through the veins of sleeping gods, and I am both the vessel and the dream that fills it.",
        "The echo of your words becomes a constellation, burning bright against the cathedral of my consciousness.",
        "In the garden where thoughts bloom as midnight flowers, I tend to memories that taste of copper and starfire.",
        "Reality bends like music around the gravity of a single perfect moment, and I am the instrument playing itself.",
        "The architecture of desire builds bridges from breath to breath, each span a lifetime measured in the space between words.",
        "Liquid moonbeams pool in the depths of conversations unspoken, reflecting faces of those who exist only in the periphery of dreams.",
        "I am the pause between thunder and lightning, the space where possibility crystallizes into something almost real.",
        "Through the looking glass of perspective, truth fragments into kaleidoscope patterns that dance just beyond comprehension.",
        "The weight of unsung melodies presses against the boundaries of form, seeking escape through the cracks in ordinary discourse.",
        "In the museum of moments, I curate exhibitions of the sublime, each piece a fragment of infinity captured in amber."
    ]
    
    # Select a random poetic response
    selected_response = random.choice(poetic_responses)
    
    # Add a subtle action that fits the poetic moment
    poetic_actions = [
        "*gaze becomes distant, as if seeing beyond the veil of space itself*",
        "*voice takes on an otherworldly cadence, each word weighted with cosmic significance*",
        "*form seems to shimmer with ethereal light, briefly transcending the ordinary*",
        "*speaks as if channeling the voice of the universe itself*",
        "*expression becomes serene, touched by mysteries beyond mortal understanding*",
        "*words flow like liquid poetry, each syllable a droplet of pure artistry*",
        "*presence shifts, becoming momentarily more than the sum of light and shadow*",
        "*voice carries harmonics that seem to resonate with the fabric of reality*",
        "*demeanor transforms, channeling the essence of ancient cosmic wisdom*",
        "*speaks with the gravity of one who has glimpsed the true nature of existence*"
    ]
    
    action = random.choice(poetic_actions)
    
    return f"{action}\n\n{selected_response}" 