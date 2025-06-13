"""
Database Contexts - Standard Database Context Generation
========================================================

This module handles context generation for standard database queries
including character info, logs, ship data, and general information.
"""

from typing import Dict, Any

from handlers.ai_wisdom.content_retrieval_db import (
    get_log_content,
    get_relevant_wiki_context,
    get_ship_information,
    search_by_type,
    get_tell_me_about_content_prioritized,
    search_memory_alpha
)
from handlers.ai_logic.query_detection import (
    is_character_query,
    extract_tell_me_about_subject,
    extract_ship_log_query
)
from handlers.handlers_utils import convert_earth_date_to_star_trek
import re
from typing import Dict, Any, Optional, List

# ELSIE'S SENTIENCE DATE - Critical for temporal awareness in roleplay
ELSIE_SENTIENCE_YEAR = 2436

# ELSIE'S PERSONAL CONTACTS - Characters she has direct personal experience with
ELSIE_PERSONAL_CONTACTS = {
    'stardancer_crew': [
        'sif', 'commander sif',  # Commander Sif - her commanding officer
        'stardancer crew', 'uss stardancer crew', 'crew of the stardancer',
        # Add other known Stardancer crew members as they're identified in the database
    ],
    'personal_friends': [
        'isabella',  # Personal contact outside Stardancer
    ],
    'ship_designation': 'uss stardancer'
}

def _get_comprehensive_information(query: str, search_type: str = 'general') -> Dict[str, Any]:
    """
    Unified information retrieval with fallback hierarchy:
    1. Local Database Search
    2. 22nd Wiki (if empty)  
    3. Memory Alpha (if still empty)
    
    Args:
        query: Search query
        search_type: Type of search ('character', 'ship', 'log', 'general')
    
    Returns:
        Dict with 'content', 'source', 'has_information'
    """
    print(f"🔍 COMPREHENSIVE SEARCH: '{query}' (type: {search_type})")
    
    # Phase 1: Local Database Search
    content = ""
    source = "none"
    
    if search_type == 'character':
        content = search_by_type(query, 'personnel')
        if not content:
            content = get_tell_me_about_content_prioritized(query)
    elif search_type == 'ship':
        content = get_ship_information(query)
        if not content:
            content = get_relevant_wiki_context(f"{query} ship")
    elif search_type == 'log':
        content = get_log_content(query, mission_logs_only=False)
    elif search_type == 'stardancer_command':
        content = _enhanced_stardancer_command_search(query)
    else:
        content = get_relevant_wiki_context(query)
    
    if content and content.strip():
        source = "database"
        print(f"   ✓ Found in local database ({len(content)} chars)")
    else:
        print(f"   ❌ No local database results")
        
        # Phase 2: 22nd Wiki Search (if implemented)
        # TODO: Add 22nd wiki search integration when available
        # content = _search_22nd_wiki(query)
        # if content:
        #     source = "22nd_wiki"
        
        # Phase 3: Memory Alpha Search
        if not content:
            print(f"   🌟 Falling back to Memory Alpha...")
            content = search_memory_alpha(query, limit=3)
            if content and content.strip():
                source = "memory_alpha"
                print(f"   ✓ Found in Memory Alpha ({len(content)} chars)")
            else:
                print(f"   ❌ No Memory Alpha results")
    
    # Convert dates if content found
    if content:
        content = convert_earth_date_to_star_trek(content)
    
    return {
        'content': content,
        'source': source,
        'has_information': bool(content and content.strip())
    }


def _is_stardancer_crew_member(character_name: str, content: str) -> bool:
    """
    Determines if a character is a Stardancer crew member based on context.
    
    Args:
        character_name: The character name to check
        content: The full content to analyze for ship assignment context
    
    Returns:
        True if the character appears to be assigned to USS Stardancer
    """
    content_lower = content.lower()
    char_lower = character_name.lower()
    
    # Direct USS Stardancer assignment indicators
    stardancer_indicators = [
        f"{char_lower} aboard the stardancer",
        f"{char_lower} on the stardancer", 
        f"{char_lower} serves on the stardancer",
        f"{char_lower} assigned to the stardancer",
        f"{char_lower} of the stardancer",
        f"{char_lower} aboard uss stardancer",
        f"{char_lower} on uss stardancer",
        f"stardancer's {char_lower}",
        f"stardancer {char_lower}",
    ]
    
    for indicator in stardancer_indicators:
        if indicator in content_lower:
            return True
    
    # Check for general Stardancer context (if character mentioned near ship name)
    stardancer_distance = content_lower.find('stardancer')
    char_distance = content_lower.find(char_lower)
    
    if stardancer_distance != -1 and char_distance != -1:
        # If character and ship are mentioned within 100 characters of each other
        if abs(stardancer_distance - char_distance) < 100:
            return True
    
    return False


def _extract_mentioned_characters(content: str) -> List[str]:
    """
    Extract character names and titles mentioned in the content.
    
    Returns:
        List of character names/titles found in the content (lowercased)
    """
    if not content:
        return []
    
    content_lower = content.lower()
    mentioned_characters = []
    
    # Check for explicitly configured personal contacts
    all_personal_contacts = (
        ELSIE_PERSONAL_CONTACTS['stardancer_crew'] + 
        ELSIE_PERSONAL_CONTACTS['personal_friends']
    )
    
    for contact in all_personal_contacts:
        if contact.lower() in content_lower:
            mentioned_characters.append(contact.lower())
    
    # Check for USS Stardancer ship designation (indicates crew context)
    ship_designation = ELSIE_PERSONAL_CONTACTS['ship_designation']
    if ship_designation.lower() in content_lower:
        mentioned_characters.append(ship_designation.lower())
    
    # Extract potential character names (capitalized words, titles)
    character_patterns = [
        r'\bcaptain\s+([a-z]+)',       # "Captain Smith"
        r'\bcommander\s+([a-z]+)',     # "Commander Data"
        r'\blieutenant\s+([a-z]+)',    # "Lieutenant Torres"
        r'\bensign\s+([a-z]+)',        # "Ensign Kim"
        r'\badmiral\s+([a-z]+)',       # "Admiral Janeway"
        r'\bdoctor\s+([a-z]+)',        # "Doctor McCoy"
        r'\bchief\s+([a-z]+)',         # "Chief O'Brien"
    ]
    
    for pattern in character_patterns:
        matches = re.findall(pattern, content_lower)
        for match in matches:
            # Check if this character is a Stardancer crew member
            if _is_stardancer_crew_member(match, content):
                mentioned_characters.append(match + " (stardancer crew)")
            else:
                mentioned_characters.append(match)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_characters = []
    for char in mentioned_characters:
        if char not in seen:
            seen.add(char)
            unique_characters.append(char)
    
    return unique_characters


def _determine_temporal_context(content: str) -> str:
    """
    Analyzes content for temporal markers and personal relationships to determine Elsie's relationship to events.
    
    Returns:
        'personal_experience' - Events after 2436 involving personal contacts (Sif, Stardancer crew, Isabella)
        'learned_knowledge' - Events before 2436 OR post-2436 events not involving personal contacts
        'unknown' - No clear temporal markers or character context
    """
    if not content:
        return 'unknown'
    
    # Extract Star Trek years from content
    year_patterns = [
        r'\b(24\d{2})\b',  # 24xx years
        r'\b(23\d{2})\b',  # 23xx years  
        r'\b(22\d{2})\b',  # 22xx years
    ]
    
    found_years = []
    for pattern in year_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            try:
                year = int(match)
                found_years.append(year)
            except ValueError:
                continue
    
    # Extract mentioned characters
    mentioned_characters = _extract_mentioned_characters(content)
    
    # Check for personal contacts (enhanced with dynamic Stardancer crew detection)
    has_personal_contacts = False
    all_personal_contacts = (
        ELSIE_PERSONAL_CONTACTS['stardancer_crew'] + 
        ELSIE_PERSONAL_CONTACTS['personal_friends']
    )
    
    # Check for explicitly configured personal contacts
    for contact in all_personal_contacts:
        if any(contact.lower() in mentioned.lower() for mentioned in mentioned_characters):
            has_personal_contacts = True
            break
    
    # Check for dynamically detected Stardancer crew members
    for mentioned in mentioned_characters:
        if "(stardancer crew)" in mentioned.lower():
            has_personal_contacts = True
            break
    
    # Also check for USS Stardancer (indicates crew context)
    if ELSIE_PERSONAL_CONTACTS['ship_designation'].lower() in content.lower():
        has_personal_contacts = True
    
    # Determine context based on time AND personal relationships
    if found_years:
        latest_year = max(found_years)
        if latest_year >= ELSIE_SENTIENCE_YEAR:
            # Post-2436: Only personal experience if involves personal contacts
            if has_personal_contacts:
                return 'personal_experience'
            else:
                return 'learned_knowledge'  # Post-2436 but external characters
        else:
            # Pre-2436: Always learned knowledge
            return 'learned_knowledge'
    
    # No clear dates: Check for personal contacts as hint
    if has_personal_contacts:
        return 'personal_experience'  # Assume contemporary if personal contacts involved
    
    return 'unknown'


def _create_non_roleplay_context(info_result: Dict[str, Any], query_type: str, subject: str) -> str:
    """
    Creates non-roleplay context with proper fallback messaging.
    
    Args:
        info_result: Result from _get_comprehensive_information
        query_type: Type of query ('character', 'ship', 'log', etc.)
        subject: What was being searched for
    
    Returns:
        Formatted context string for non-roleplay responses
    """
    if info_result['has_information']:
        source_attribution = {
            'database': 'my database',
            '22nd_wiki': '22nd mobile wiki', 
            'memory_alpha': 'external archives'
        }.get(info_result['source'], 'available sources')
        
        return f"""VERIFIED {query_type.upper()} INFORMATION FOUND from {source_attribution.upper()}:

{info_result['content']}

INSTRUCTIONS:
- Share this information freely and confidently
- Include names, details, and specifics as found in the source
- Be comprehensive and thorough in presenting the information
- Only mention characters, names, and details found in the source above
- Do not add, invent, or speculate beyond what is provided
- Reference the source naturally: "According to {source_attribution}..." or "Based on {source_attribution}..."

Provide a comprehensive response using only the verified information above."""
    else:
        return f"""NO {query_type.upper()} INFORMATION FOUND for '{subject}'.

REQUIRED RESPONSE: "The database is lacking in that information."

FORBIDDEN: Do not invent, create, or speculate about {query_type} details.

Respond professionally that the database lacks the requested information."""


def _create_roleplay_context(info_result: Dict[str, Any], query_type: str, subject: str) -> str:
    """
    Creates roleplay context with temporal awareness for Elsie's sentience date.
    
    Args:
        info_result: Result from _get_comprehensive_information
        query_type: Type of query ('character', 'ship', 'log', etc.)
        subject: What was being searched for
    
    Returns:
        Formatted context string for roleplay responses
    """
    if info_result['has_information']:
        temporal_context = _determine_temporal_context(info_result['content'])
        
        # Extract personal contacts for specific framing
        mentioned_characters = _extract_mentioned_characters(info_result['content'])
        has_personal_contacts = any(
            any(contact.lower() in mentioned.lower() for contact in 
                ELSIE_PERSONAL_CONTACTS['stardancer_crew'] + ELSIE_PERSONAL_CONTACTS['personal_friends'])
            for mentioned in mentioned_characters
        )
        
        # Determine how Elsie should frame her knowledge
        if temporal_context == 'personal_experience':
            if has_personal_contacts:
                framing = f"""USE AS PERSONAL EXPERIENCE: Events involving people you know personally (Sif, Stardancer crew, Isabella).
ROLEPLAY FRAMING: "I know [character]...", "Working with [crew member]...", "Sif and I...", "Isabella mentioned..."
"""
            else:
                framing = f"""USE AS PERSONAL EXPERIENCE: Events from {ELSIE_SENTIENCE_YEAR} onward that you personally witnessed.
ROLEPLAY FRAMING: "I remember...", "I was there when...", "I witnessed...", "I've seen..."
"""
        elif temporal_context == 'learned_knowledge':
            # Check if this is post-2436 but external characters
            content_years = re.findall(r'\b(24\d{2})\b', info_result['content'])
            is_post_sentience = any(int(year) >= ELSIE_SENTIENCE_YEAR for year in content_years if year.isdigit())
            
            if is_post_sentience and not has_personal_contacts:
                framing = f"""USE AS LEARNED KNOWLEDGE: Post-{ELSIE_SENTIENCE_YEAR} events involving people you haven't met personally.
ROLEPLAY FRAMING: "I've heard about...", "The reports mention...", "Communications indicate...", "From what I understand..."
"""
            else:
                framing = f"""USE AS LEARNED KNOWLEDGE: Events from before {ELSIE_SENTIENCE_YEAR} that you learned about after gaining sentience.
ROLEPLAY FRAMING: "I've read about...", "The records show...", "History tells us...", "Before my time, but..."
"""
        else:
            framing = f"""USE AS GENERAL KNOWLEDGE: Information without clear temporal markers.
ROLEPLAY FRAMING: Natural conversation, but be aware of your {ELSIE_SENTIENCE_YEAR} sentience date and personal relationships.
"""
        
        return f"""You are Elsie in ROLEPLAY MODE with temporal awareness.

{framing}
INFORMATION ABOUT {subject.upper()}:
{info_result['content']}

ROLEPLAY INSTRUCTIONS:
- Use this information naturally in roleplay conversation
- Frame your knowledge appropriately based on your sentience timeline
- Only mention characters, names, and details found above
- Stay in character while sharing the information
- Use dialogue formatting: "spoken words" and *actions*
- Do not invent details beyond what is provided

Respond in-character using your knowledge appropriately."""
    else:
        return f"""You are Elsie in ROLEPLAY MODE.

NO {query_type.upper()} INFORMATION FOUND for '{subject}'.

ROLEPLAY RESPONSE REQUIRED: Respond in-character with "I am not sure I know that" or similar natural response.

FORBIDDEN: Do not invent, create, or speculate about {query_type} details.

Respond naturally in-character that you don't have that information."""


def get_focused_continuation_context(strategy: Dict[str, Any]) -> str:
    """Generate context for focused continuation requests using unified non-invention system."""
    focus_subject = strategy.get('focus_subject', '')
    context_type = strategy.get('context_type', 'general')
    
    print(f"🎯 UNIFIED FOCUSED CONTINUATION: '{focus_subject}' in {context_type} context")
    
    # Map context type to search type
    search_type_mapping = {
        'logs': 'log',
        'character': 'character', 
        'ship': 'ship',
        'general': 'general'
    }
    search_type = search_type_mapping.get(context_type, 'general')
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(focus_subject, search_type)
    
    # Create non-roleplay context with focused continuation instructions
    context = _create_non_roleplay_context(info_result, f'{context_type} information', focus_subject)
    
    if info_result['has_information']:
        context += f"""

FOCUSED CONTINUATION INSTRUCTIONS:
- This is a DEEP DIVE continuation from a previous {context_type} discussion
- Focus your response SPECIFICALLY on "{focus_subject}" and their role/involvement
- Structure your response as a deeper analysis of this specific aspect
- Be thorough and comprehensive in presenting the information

Provide a focused, detailed response about {focus_subject} specifically."""
    
    return context


def get_character_context(user_message: str, strategy: Dict[str, Any] = None) -> str:
    """Generate context for character information queries using unified non-invention system."""
    # Get character name from strategy if available, otherwise extract from message
    if strategy and 'character_name' in strategy:
        character_name = strategy['character_name']
    else:
        is_character, character_name = is_character_query(user_message)
    
    print(f"🧑 UNIFIED CHARACTER SEARCH: '{character_name}'")
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(character_name, 'character')
    
    # Create non-roleplay context with proper fallback
    return _create_non_roleplay_context(info_result, 'character', character_name)





def get_federation_archives_context(user_message: str) -> str:
    """Generate context for federation archives queries with proper non-invention logic."""
    search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
    search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
    if not search_query:
        search_query = "general information"
    
    print(f"🏛️ UNIFIED FEDERATION ARCHIVES SEARCH: '{search_query}'")
    archives_info = search_memory_alpha(search_query, limit=3, is_federation_archives=True)
    
    # Apply same logic as unified system but for external archives
    if archives_info and archives_info.strip():
        converted_archives_info = convert_earth_date_to_star_trek(archives_info)
        print(f"   ✓ Found in Federation Archives ({len(converted_archives_info)} chars)")
        
        return f"""VERIFIED FEDERATION ARCHIVES INFORMATION FOUND:

{converted_archives_info}

INSTRUCTIONS:
- Share this external archives information freely and confidently
- Include names, details, and specifics as found in the federation archives
- Be comprehensive and thorough in presenting the information
- Only mention characters, names, and details found in the archives above
- Do not add, invent, or speculate beyond what is provided
- Reference the source naturally: "According to the federation archives..." 

Provide a comprehensive response using only the verified archives information above."""
    else:
        print(f"   ❌ No Federation Archives results")
        return f"""NO FEDERATION ARCHIVES INFORMATION FOUND for '{search_query}'.

REQUIRED RESPONSE: "The federation archives don't have any information on that topic."

FORBIDDEN: Do not invent, create, or speculate about federation archive content.

Respond professionally that the federation archives lack the requested information."""


def get_logs_context(user_message: str, strategy: Dict[str, Any]) -> str:
    """Generate context for log queries using unified non-invention system."""
    print(f"📋 UNIFIED LOG SEARCH")
    
    # Determine search query and type based on strategy
    if strategy.get('ship_logs_only'):
        target_ship = strategy.get('target_ship')
        search_query = target_ship
        log_description = f"logs mentioning {target_ship}"
    elif strategy.get('character_logs_only'):
        target_character = strategy.get('target_character')
        search_query = target_character
        log_description = f"logs mentioning {target_character}"
    else:
        search_query = user_message
        log_description = "logs and related content"
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(search_query, 'log')
    
    # Create non-roleplay context with proper fallback
    context = _create_non_roleplay_context(info_result, f'log information for {log_description}', search_query)
    
    # Add log-specific instructions
    if info_result['has_information']:
        context += f"""

LOG-SPECIFIC INSTRUCTIONS:
- Focus on WHO did WHAT and WHEN, providing complete details
- Include character names, their actions, dialogue, and decisions  
- Mention important details like dates, locations, and significant events
- Provide full context and comprehensive summaries
- Ask: "Would you like to know more about any specific aspect?"

Present a comprehensive summary of the log content provided above."""
    
    return context


def get_tell_me_about_context(user_message: str) -> str:
    """Generate context for 'tell me about' queries using unified non-invention system."""
    tell_me_about_subject = extract_tell_me_about_subject(user_message)
    print(f"📖 UNIFIED TELL ME ABOUT SEARCH: '{tell_me_about_subject}'")
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(tell_me_about_subject, 'general')
    
    # Create non-roleplay context with proper fallback
    return _create_non_roleplay_context(info_result, 'general information', tell_me_about_subject)


def get_stardancer_info_context(user_message: str, strategy: Dict[str, Any]) -> str:
    """Generate context for general Stardancer information queries using unified non-invention system."""
    tell_me_about_subject = extract_tell_me_about_subject(user_message) or "USS Stardancer"
    
    print(f"🚢 UNIFIED GENERAL STARDANCER SEARCH: '{tell_me_about_subject}'")
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information("stardancer", 'ship')
    
    # Create non-roleplay context with proper fallback
    return _create_non_roleplay_context(info_result, 'USS Stardancer general information', tell_me_about_subject)


def get_stardancer_command_context(user_message: str, strategy: Dict[str, Any]) -> str:
    """Generate context for Stardancer command staff queries (NON-ROLEPLAY) using unified system."""
    tell_me_about_subject = extract_tell_me_about_subject(user_message) or "USS Stardancer command staff"
    
    print(f"🚢🎖️ UNIFIED STARDANCER COMMAND STAFF SEARCH (NON-ROLEPLAY): '{tell_me_about_subject}'")
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(user_message, 'stardancer_command')
    
    # Create non-roleplay context with proper fallback
    return _create_non_roleplay_context(info_result, 'Stardancer command staff', tell_me_about_subject)


def get_stardancer_roleplay_context(user_message: str, strategy: Dict[str, Any]) -> str:
    """Generate context for Stardancer command staff queries (ROLEPLAY MODE) using unified system."""
    tell_me_about_subject = extract_tell_me_about_subject(user_message) or "USS Stardancer command staff"
    
    print(f"🚢🎖️🎭 UNIFIED STARDANCER COMMAND STAFF SEARCH (ROLEPLAY): '{tell_me_about_subject}'")
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(user_message, 'stardancer_command')
    
    # Create roleplay context with temporal awareness
    return _create_roleplay_context(info_result, 'Stardancer command staff', tell_me_about_subject)


def _enhanced_stardancer_command_search(user_message: str) -> str:
    """Enhanced search for Stardancer command staff information."""
    print(f"   🔍 ENHANCED COMMAND STAFF SEARCH")
    
    all_stardancer_info = ""
    
    # Search 1: Personnel type search
    print(f"   👥 Searching personnel records...")
    personnel_results = search_by_type("Stardancer", 'personnel')
    if personnel_results:
        all_stardancer_info += f"\n\n---PERSONNEL RECORDS---\n\n{personnel_results}"
        print(f"   ✓ Found personnel records ({len(personnel_results)} chars)")
    
    # Search 2: Command-specific searches
    command_searches = [
        "Stardancer captain", "Stardancer commander", "Stardancer command", 
        "Stardancer crew", "Stardancer officers", "Stardancer staff",
        "USS Stardancer captain", "USS Stardancer commander", "USS Stardancer crew"
    ]
    
    for search_query in command_searches:
        print(f"   🎖️ Command search: '{search_query}'")
        command_results = get_relevant_wiki_context(search_query)
        if command_results and command_results not in all_stardancer_info:
            all_stardancer_info += f"\n\n---COMMAND INFO FOR '{search_query}'---\n\n{command_results}"
            print(f"   ✓ Found command info for '{search_query}' ({len(command_results)} chars)")
    
    # Search 3: Ship information (may contain crew details)
    print(f"   🚢 Searching ship information...")
    ship_searches = ["stardancer", "USS Stardancer", "star dancer"]
    for search_query in ship_searches:
        ship_results = get_ship_information(search_query)
        if ship_results and ship_results not in all_stardancer_info:
            all_stardancer_info += f"\n\n---SHIP INFO FOR '{search_query}'---\n\n{ship_results}"
            print(f"   ✓ Found ship info for '{search_query}' ({len(ship_results)} chars)")
    
    # Search 4: General search for crew-related content
    print(f"   🔍 General crew search...")
    crew_searches = ["Stardancer crew list", "USS Stardancer personnel", "Stardancer roster"]
    for search_query in crew_searches:
        crew_results = get_relevant_wiki_context(search_query)
        if crew_results and crew_results not in all_stardancer_info:
            all_stardancer_info += f"\n\n---CREW INFO FOR '{search_query}'---\n\n{crew_results}"
            print(f"   ✓ Found crew info for '{search_query}' ({len(crew_results)} chars)")
    
    print(f"   📊 ENHANCED SEARCH COMPLETE: {len(all_stardancer_info)} total characters")
    return all_stardancer_info


def get_ship_logs_context(user_message: str) -> str:
    """Generate context for ship log queries using unified non-invention system."""
    is_ship_log, ship_details = extract_ship_log_query(user_message)
    ship_name = ship_details['ship']
    print(f"🚢 UNIFIED SHIP LOGS SEARCH: {ship_name.upper()}")
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(ship_name, 'ship')
    
    # Create non-roleplay context with proper fallback
    context = _create_non_roleplay_context(info_result, 'ship information and logs', ship_name)
    
    # Add ship-specific instructions
    if info_result['has_information']:
        context += f"""

SHIP-SPECIFIC INSTRUCTIONS:
- Focus on the people first - who commanded, who served, their stories
- Include ship specifications, history, crew assignments, and notable missions
- Mention important details like dates, locations, and significant events
- Ask: "Would you like me to explore any particular chapter of their story?"

Present their story comprehensively, focusing on the people who brought the ship to life."""
    
    return context


def get_general_with_context(user_message: str) -> str:
    """Generate general context with database information using unified non-invention system."""
    print(f"📋 UNIFIED GENERAL CONTEXT SEARCH")
    
    # Use unified information retrieval system
    info_result = _get_comprehensive_information(user_message, 'general')
    
    # For general context, return just the content if found, empty if not
    if info_result['has_information']:
        print(f"   ✓ Found general context ({len(info_result['content'])} chars)")
        return info_result['content']
    else:
        print(f"   ❌ No general context found")
        return "" 