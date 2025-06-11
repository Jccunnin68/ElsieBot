"""AI wisdom for database retrieval and context generation."""

from typing import Dict, Any

from content_retrieval_db import (
    get_log_content,
    get_relevant_wiki_context, 
    get_ship_information, 
    search_by_type, 
    get_tell_me_about_content_prioritized,
    get_log_url,
    search_memory_alpha
)
from ai_logic import (
    convert_earth_date_to_star_trek,
    extract_ooc_log_url_request,
    is_character_query,
    extract_tell_me_about_subject,
    is_ooc_query,
    extract_ship_log_query
)


def handle_ooc_url_request(user_message: str) -> str:
    """Handle OOC URL requests directly."""
    is_url_request, search_query = extract_ooc_log_url_request(user_message)
    if not is_url_request:
        return "I can't seem to figure out which URL you need. Could you be more specific?"
        
    print(f"🔗 EXECUTING OOC URL STRATEGY: '{search_query}'")
    print(f"   ⚠️  OOC URL Request: Will preserve real Earth dates in response")
    url_response = get_log_url(search_query)
    print(f"   - URL response: {url_response}")
    return url_response


def get_context_for_strategy(strategy: Dict[str, Any], user_message: str) -> str:
    """
    Get the appropriate context from the database based on the response strategy.
    Returns a formatted context string for the AI prompt.
    """
    approach = strategy.get('approach')
    
    if approach == 'focused_continuation':
        return _get_focused_continuation_context(strategy)
    elif approach == 'character':
        return _get_character_context(user_message)
    elif approach == 'federation_archives':
        return _get_federation_archives_context(user_message)
    elif approach == 'logs':
        return _get_logs_context(user_message, strategy)
    elif approach == 'tell_me_about':
        return _get_tell_me_about_context(user_message)
    elif approach == 'stardancer_info':
        return _get_stardancer_info_context(user_message, strategy)
    elif approach == 'ship_logs':
        return _get_ship_logs_context(user_message)
    elif approach == 'ooc':
        return _get_ooc_context(user_message)
    elif approach == 'general_with_context':
        return _get_general_with_context(user_message)
    
    return ""


def _get_focused_continuation_context(strategy: Dict[str, Any]) -> str:
    focus_subject = strategy.get('focus_subject', '')
    context_type = strategy.get('context_type', 'general')
    
    print(f"🎯 FOCUSED CONTINUATION: Searching for '{focus_subject}' in {context_type} context")
    
    wiki_info = ""
    if context_type == 'logs':
        wiki_info = get_log_content(f"{focus_subject}", mission_logs_only=False)
        if not wiki_info:
            wiki_info = get_relevant_wiki_context(f"{focus_subject}")
    elif context_type == 'character':
        wiki_info = search_by_type(focus_subject, 'personnel')
        if not wiki_info:
            wiki_info = get_tell_me_about_content_prioritized(focus_subject)
    elif context_type == 'ship':
        wiki_info = get_ship_information(focus_subject)
        if not wiki_info:
            wiki_info = get_relevant_wiki_context(f"{focus_subject} ship")
    else:
        wiki_info = get_relevant_wiki_context(focus_subject)
    
    print(f"   - Retrieved focused content length: {len(wiki_info)} chars")
    
    converted_wiki_info = convert_earth_date_to_star_trek(wiki_info) if wiki_info else wiki_info
    
    return f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

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


def _get_character_context(user_message: str) -> str:
    is_character, character_name = is_character_query(user_message)
    print(f"🧑 SEARCHING CHARACTER DATA: '{character_name}'")
    
    # First try personnel type search
    character_info = search_by_type(character_name, 'personnel')
    
    if not character_info:
        # Use optimized character search that prioritizes exact title matches
        character_info = _get_character_info_optimized(character_name)
    
    converted_character_info = convert_earth_date_to_star_trek(character_info) if character_info else character_info
    
    return f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

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


def _get_character_info_optimized(character_name: str) -> str:
    """
    Optimized character info retrieval that prioritizes exact title matches
    to prevent massive context chunking for character queries.
    """
    try:
        from content_retrieval_db import get_db_controller
        
        controller = get_db_controller()
        print(f"🎯 OPTIMIZED CHARACTER SEARCH: '{character_name}'")
        
        # First, search for exact title match
        results = controller.search_pages(character_name, limit=15)
        print(f"   📊 Found {len(results)} total results")
        
        # Check if first result is an exact title match for the character name
        if results:
            first_result = results[0]
            first_title = first_result['title'].lower()
            character_name_lower = character_name.lower()
            
            # Check for exact match or very close match
            if (first_title == character_name_lower or 
                first_title.replace(' ', '') == character_name_lower.replace(' ', '') or
                character_name_lower in first_title or first_title in character_name_lower):
                
                print(f"   ✅ EXACT TITLE MATCH FOUND: '{first_result['title']}' - using only this result")
                
                # Use only the exact match to prevent context bloat
                content = first_result['raw_content']
                page_type = first_result.get('page_type', 'general')
                
                type_indicator = ""
                if page_type == 'personnel':
                    type_indicator = " [Personnel File]"
                elif page_type == 'general':
                    type_indicator = ""
                
                page_text = f"**{first_result['title']}{type_indicator}**\n{content}"
                print(f"   📏 Optimized character info: {len(page_text)} characters (single result)")
                return page_text
        
        # If no exact title match, fall back to the standard prioritized search
        print(f"   ⚠️  No exact title match found, falling back to prioritized search")
        from content_retrieval_db import get_tell_me_about_content_prioritized
        return get_tell_me_about_content_prioritized(character_name)
        
    except Exception as e:
        print(f"✗ Error in optimized character search: {e}")
        from content_retrieval_db import get_tell_me_about_content_prioritized
        return get_tell_me_about_content_prioritized(character_name)


def _get_federation_archives_context(user_message: str) -> str:
    search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
    search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
    if not search_query:
        search_query = "general information"
    
    print(f"🏛️ SEARCHING FEDERATION ARCHIVES: '{search_query}'")
    archives_info = search_memory_alpha(search_query, limit=3, is_federation_archives=True)
    print(f"   - Retrieved archives content length: {len(archives_info)} chars")
    
    converted_archives_info = convert_earth_date_to_star_trek(archives_info) if archives_info else archives_info
    
    return f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

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


def _get_logs_context(user_message: str, strategy: Dict[str, Any]) -> str:
    print(f"📋 SEARCHING LOG DATA")
    mission_logs_only = strategy.get('log_specific', False)
    if mission_logs_only:
        wiki_info = get_log_content(user_message, mission_logs_only=True)
        print(f"   - Retrieved MISSION LOGS ONLY content length: {len(wiki_info)} chars")
    else:
        wiki_info = get_relevant_wiki_context(user_message)
        print(f"   - Retrieved general log content length: {len(wiki_info)} chars")
    
    total_found = wiki_info.count("**") if wiki_info else 0
    
    converted_wiki_info = convert_earth_date_to_star_trek(wiki_info) if wiki_info else wiki_info
    
    log_type_description = "mission logs only" if mission_logs_only else "logs and related content"
    
    return f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

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


def _get_tell_me_about_context(user_message: str) -> str:
    tell_me_about_subject = extract_tell_me_about_subject(user_message)
    print(f"📖 SEARCHING TELL ME ABOUT DATA: '{tell_me_about_subject}'")
    wiki_info = get_tell_me_about_content_prioritized(tell_me_about_subject)
    print(f"   - Retrieved prioritized content length: {len(wiki_info)} chars")
    
    converted_wiki_info = convert_earth_date_to_star_trek(wiki_info) if wiki_info else wiki_info
    
    return f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

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


def _get_stardancer_info_context(user_message: str, strategy: Dict[str, Any]) -> str:
    tell_me_about_subject = extract_tell_me_about_subject(user_message) or "USS Stardancer"
    is_command_query = strategy.get('command_query', False)
    
    print(f"🚢 SEARCHING STARDANCER DATA WITH GUARD RAILS: '{tell_me_about_subject}' (command_query={is_command_query})")
    
    stardancer_info = ""
    
    if is_command_query:
        # For command queries, search for personnel information specifically
        command_searches = [
            "Stardancer captain", "Stardancer commander", "Stardancer command", 
            "Stardancer crew", "Stardancer officers", "Stardancer staff",
            "USS Stardancer captain", "USS Stardancer commander"
        ]
        print(f"   🎖️ COMMAND QUERY: Searching for Stardancer command staff...")
        
        for search_query in command_searches:
            print(f"      🔍 Command search: '{search_query}'")
            personnel_results = get_relevant_wiki_context(search_query)
            if personnel_results and personnel_results not in stardancer_info:
                stardancer_info += f"\n\n---COMMAND INFO FOR '{search_query}'---\n\n{personnel_results}"
    
    # Always get basic ship information
    stardancer_searches = ["stardancer", "USS Stardancer", "star dancer"]
    for search_query in stardancer_searches:
        ship_results = get_ship_information(search_query)
        if ship_results and ship_results not in stardancer_info:
            stardancer_info += f"\n\n---STARDANCER INFO FOR '{search_query}'---\n\n{ship_results}"
    
    converted_stardancer_info = convert_earth_date_to_star_trek(stardancer_info) if stardancer_info else ""
    
    return f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL GUARD RAILS FOR USS STARDANCER QUERIES:
- You are being asked about the USS Stardancer specifically
- NEVER INVENT OR CREATE command staff, officers, or personnel for the Stardancer
- ONLY use information provided in the STARDANCER DATABASE section below
- If asking about command staff and no information is in the database, say: "I'm afraid I don't have any records of the current command staff in my database"
- DO NOT make up names, ranks, or positions for Stardancer personnel
- DO NOT extrapolate or assume command structure beyond what's explicitly stated
- If no Stardancer information is found, say: "I don't have specific information about the Stardancer in my database right now"

{"COMMAND STAFF QUERY: This is asking about Stardancer command staff. The database search below contains extensive Stardancer information including personnel records. Look for and share any captain, commander, first officer, XO, or command crew information you find. Be confident in providing the command structure and personnel details from the database." if is_command_query else ""}

STRICT DATABASE ADHERENCE REQUIRED:
- USE the Stardancer information provided in the database results below
- If command staff information is found in the database, provide it freely and confidently
- DO NOT create fictional crew members beyond what's in the database
- If command staff info exists in the results, share names, ranks, and positions as found
- If no personnel info exists in the database results, then say you don't have that information

STARDANCER DATABASE:
{converted_stardancer_info if converted_stardancer_info else "No specific USS Stardancer information found in the ship database."}

NOTE: All Earth dates have been converted to Star Trek era (Earth year + 404 for pre-June 2024, +430 for after).

Respond with your warm, musical personality while strictly adhering to the database information. Never invent command staff or personnel."""


def _get_ship_logs_context(user_message: str) -> str:
    is_ship_log, ship_details = extract_ship_log_query(user_message)
    ship_name = ship_details['ship']
    print(f"🚢 SEARCHING COMPREHENSIVE SHIP DATA: {ship_name.upper()}")
    
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
    
    converted_ship_info = convert_earth_date_to_star_trek(comprehensive_ship_info) if comprehensive_ship_info else comprehensive_ship_info
    
    return f"""You are Elsie, the intelligent, attentive, and slightly flirty holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

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


def _get_ooc_context(user_message: str) -> str:
    print(f"📋 SEARCHING OOC DATA")
    wiki_info = get_relevant_wiki_context(user_message)
    print(f"   - Retrieved OOC context length: {len(wiki_info)} chars")
    
    print(f"   ⚠️  OOC Query: Skipping date conversion to preserve real Earth dates")
    
    ooc_query = is_ooc_query(user_message)[1]
    if any(word in ooc_query.lower() for word in ['schedule', 'meeting', 'time', 'when', 'gm', 'game master']):
        return f"""You are Elsie, providing Out-Of-Character (OOC) information about game schedules and meetings.

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
        return f"""You are Elsie, providing Out-Of-Character (OOC) information from the Players Handbook.

CRITICAL INSTRUCTIONS FOR OOC QUERIES:
- Focus on rules, mechanics, species traits, and character creation details
- Be direct and factual in your responses
- Keep responses clear and concise
- Use REAL EARTH DATES where applicable - do not convert to Star Trek era dates

{f"PLAYERS HANDBOOK QUERY: {ooc_query}" if ooc_query else ""}

{f"HANDBOOK INFORMATION: {wiki_info}" if wiki_info else ""}

Respond with ONLY the relevant Players Handbook information using real Earth dates."""


def _get_general_with_context(user_message: str) -> str:
    print(f"📋 SEARCHING LIGHT CONTEXT DATA")
    wiki_info = get_relevant_wiki_context(user_message)
    print(f"   - Retrieved general context length: {len(wiki_info)} chars")
    
    return convert_earth_date_to_star_trek(wiki_info) if wiki_info else ""
