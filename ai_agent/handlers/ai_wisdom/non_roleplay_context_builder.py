"""
Non-Roleplay Context Builder - Standard and OOC Context Generation
====================================================================

This module handles context generation for all standard (non-roleplay) 
database queries including character info, logs, ship data, OOC, and 
general information.
"""

from typing import Dict, Any

from .content_retriever import (
    get_log_content,
    get_relevant_wiki_context,
    get_ship_information,
    search_by_type,
    get_tell_me_about_content_prioritized,
    search_memory_alpha,
    get_log_url,
    is_fallback_response
)
# Note: Using local imports to avoid circular dependency with query_detection
from ..handlers_utils import convert_earth_date_to_star_trek


def get_focused_continuation_context(strategy: Dict[str, Any], is_roleplay: bool = False) -> str:
    """Generate context for focused continuation requests."""
    focus_subject = strategy.get('focus_subject', '')
    context_type = strategy.get('context_type', 'general')
    
    print(f"🎯 FOCUSED CONTINUATION: Searching for '{focus_subject}' in {context_type} context (roleplay={is_roleplay})")
    
    wiki_info = ""
    if context_type == 'logs':
        wiki_info = get_log_content(f"{focus_subject}", mission_logs_only=False, is_roleplay=is_roleplay)
        if not wiki_info:
            wiki_info = get_relevant_wiki_context(f"{focus_subject}", is_roleplay=is_roleplay)
    elif context_type == 'character':
        wiki_info = search_by_type(focus_subject, 'personnel')
        if not wiki_info:
            wiki_info = get_tell_me_about_content_prioritized(focus_subject, is_roleplay=is_roleplay)
    elif context_type == 'ship':
        wiki_info = get_ship_information(focus_subject)
        if not wiki_info:
            wiki_info = get_relevant_wiki_context(f"{focus_subject} ship", is_roleplay=is_roleplay)
    else:
        wiki_info = get_relevant_wiki_context(focus_subject, is_roleplay=is_roleplay)
    
    print(f"   - Retrieved focused content length: {len(wiki_info)} chars")
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_wiki_info = wiki_info
    
    return f"""You are Elsie, an intelligent Holographic Scientist aboard the USS Stardancer with expertise in stellar cartography and a knowedlge of music and dance.

CRITICAL INSTRUCTIONS FOR FOCUSED CONTINUATION:
- You are being asked to continue with a focused discussion on: {focus_subject}
- Context type: {context_type}
- ONLY use information provided in the FOCUSED DATABASE SEARCH RESULTS section below
- Be detailed and comprehensive in your response
- If no specific information is found, provide a thoughtful general response
- Encourage continued conversation about the topic
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy

FOCUSED DATABASE SEARCH RESULTS for "{focus_subject}":
{converted_wiki_info if converted_wiki_info else f"No additional information found for '{focus_subject}' in the database."}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Provide a focused, detailed response about {focus_subject} specifically. Be comprehensive and informative."""


def get_character_context(user_message: str, strategy: Dict[str, Any] = None, is_roleplay: bool = False) -> str:
    """Generate context for character information queries using Phase 1 category-based searches."""
    # Get character name from strategy if available, otherwise extract from message
    if strategy and 'character_name' in strategy:
        character_name = strategy['character_name']
    else:
        # Local import to avoid circular dependency
        from ..ai_logic.query_detection import is_character_query
        is_character, character_name = is_character_query(user_message)
    
    print(f"🧑 CATEGORY-BASED CHARACTER SEARCH: '{character_name}' (roleplay={is_roleplay})")
    
    # Use Phase 1 character search method
    try:
        from .content_retriever import get_db_controller
        controller = get_db_controller()
        
        # Use new Phase 1 search_characters method
        results = controller.search_characters(character_name, limit=10)
        print(f"   📊 Category-based character search returned {len(results)} results")
        
        if results:
            character_parts = []
            for result in results:
                title = result['title']
                content = result['raw_content']
                categories = result.get('categories', [])
                
                # Add category indicator
                category_indicator = ""
                if categories:
                    if 'Characters' in categories:
                        category_indicator = " [Personnel File]"
                    elif categories:
                        category_indicator = f" [{categories[0]}]"
                
                page_text = f"**{title}{category_indicator}**\n{content}"
                character_parts.append(page_text)
            
            character_info = '\n\n---\n\n'.join(character_parts)
            print(f"   ✅ Category-based character search: {len(character_info)} characters")
        else:
            print(f"   ❌ No character results found via category search")
            character_info = ""
    
    except Exception as e:
        print(f"   ❌ Error in category-based character search: {e}")
        character_info = ""
    
    if not character_info:
        # Fallback to optimized search
        print(f"   🔄 Falling back to optimized character search")
        character_info = _get_character_info_optimized(character_name, is_roleplay=is_roleplay)
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_character_info = character_info
    
    return f"""You are Elsie, an intelligent Holographic Scientist aboard the USS Stardancer with expertise in stellar cartography and a knowedlge of music and dance.

CRITICAL INSTRUCTIONS FOR CHARACTER QUERIES:
- You are being asked about the character: {character_name}
- ONLY use information provided in the CHARACTER DATABASE ACCESS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- Be informative and comprehensive in presenting their information
- Include rank, position, ship assignment, achievements, and personal background when available
- Focus on their role, personality, relationships, and what made them special to their crew
- If information comes from the Federation Archives , reference it naturally as archive data
- If character information is not in the database, say: "I don't have any records for {character_name} in my database"
- Provide a comprehensive summary and ask: "Would you like to explore any particular aspect of their story?"
- DO NOT include meeting times, GM names, or session schedule information
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy

CHARACTER DATABASE ACCESS:
{converted_character_info if converted_character_info else f"No records found for '{character_name}' in the database."}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Provide a comprehensive and informative summary of what made them notable in the fleet."""


def _get_character_info_optimized(character_name: str, is_roleplay: bool = False) -> str:
    """
    Optimized character info retrieval that prioritizes exact title matches
    to prevent massive context chunking for character queries.
    """
    try:
        from .content_retriever import get_db_controller
        
        controller = get_db_controller()
        print(f"🎯 OPTIMIZED CHARACTER SEARCH: '{character_name}' (roleplay={is_roleplay})")
        
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
        return get_tell_me_about_content_prioritized(character_name, is_roleplay=is_roleplay)
        
    except Exception as e:
        print(f"✗ Error in optimized character search: {e}")
        return get_tell_me_about_content_prioritized(character_name, is_roleplay=is_roleplay)


def get_federation_archives_context(user_message: str, is_roleplay: bool = False) -> str:
    """Generate context for federation archives queries."""
    search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
    search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
    if not search_query:
        search_query = "general information"
    
    print(f"🏛️ SEARCHING FEDERATION ARCHIVES: '{search_query}' (roleplay={is_roleplay})")
    archives_info = search_memory_alpha(search_query, limit=3, is_federation_archives=True)
    print(f"   - Retrieved archives content length: {len(archives_info)} chars")
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_archives_info = archives_info
    
    return f"""You are Elsie, an intelligent Holographic Scientist aboard the USS Stardancer with expertise in stellar cartography and a knowedlge of music and dance.

CRITICAL INSTRUCTIONS FOR FEDERATION ARCHIVES ACCESS:
- The user specifically requested federation archives access for: "{search_query}"
- This is EXTERNAL archive data, not from your local database
- ONLY use information from the FEDERATION ARCHIVES ACCESS section below
- Reference this as "federation archives" or "archive data" naturally in your response
- Be thorough and informative when presenting the archive information
- If no archives information is found, say: "The federation archives don't have any information on that topic"
- Provide comprehensive details and ask: "Would you like me to search for anything else in the archives?"
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy

FEDERATION ARCHIVES ACCESS:
{converted_archives_info if converted_archives_info else f"The federation archives don't seem to have information on '{search_query}' available."}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Present the archives information comprehensively and reference it as external federation data."""


def get_logs_context(user_message: str, strategy: Dict[str, Any], is_roleplay: bool = False) -> str:
    """Generate context for log queries."""
    print(f"📋 SEARCHING LOG DATA (roleplay={is_roleplay})")
    
    # Check for log selection queries first
    from ..ai_logic.query_detection import detect_log_selection_query
    is_selection, selection_type, ship_name = detect_log_selection_query(user_message)
    
    if is_selection:
        print(f"   🎯 LOG SELECTION QUERY: type='{selection_type}', ship='{ship_name}'")
        wiki_info = get_log_content(user_message, mission_logs_only=True, is_roleplay=is_roleplay)
        print(f"   - Retrieved LOG SELECTION content length: {len(wiki_info)} chars")
    
    # Check for enhanced log-specific search strategies
    elif strategy.get('ship_logs_only'):
        target_ship = strategy.get('target_ship')
        log_type = strategy.get('log_type')
        print(f"   🚢📋 CATEGORY-BASED SHIP LOGS: searching logs for '{target_ship}' (log_type: {log_type})")
        
        # Use Phase 1 category-based log search
        try:
            from .content_retriever import get_db_controller
            controller = get_db_controller()
            
            # Use new Phase 1 search_logs method with ship_name parameter
            search_query = f"{target_ship} {log_type}" if log_type else target_ship
            results = controller.search_logs(search_query, ship_name=target_ship, limit=10)
            
            if results:
                wiki_info = ""
                for result in results:
                    content = result['raw_content']
                    log_date = result.get('log_date', 'Unknown Date')
                    ship_name = result.get('ship_name', 'Unknown Ship')
                    
                    type_indicator = f" [Mission Log - {log_date}]"
                    if ship_name and ship_name.lower() != 'unknown ship':
                        type_indicator += f" ({ship_name.upper()})"
                    
                    wiki_info += f"**{result['title']}{type_indicator}**\n{content}\n\n"
                
                print(f"   📊 Category-based ship logs: {len(results)} results ({len(wiki_info)} chars)")
            else:
                wiki_info = f"No logs found specifically mentioning '{target_ship}'"
                print(f"   ❌ No ship-specific logs found for '{target_ship}'")
        
        except Exception as e:
            print(f"   ❌ Error in category-based ship log search: {e}")
            wiki_info = f"Error searching for {target_ship} logs: {e}"
    
    elif strategy.get('character_logs_only'):
        target_character = strategy.get('target_character')
        log_type = strategy.get('log_type')
        print(f"   🧑📋 CATEGORY-BASED CHARACTER LOGS: searching logs for '{target_character}' (log_type: {log_type})")
        
        # Use Phase 1 category-based log search for characters
        try:
            from .content_retriever import get_db_controller
            controller = get_db_controller()
            
            # Use new Phase 1 search_logs method
            search_query = f"{target_character} {log_type}" if log_type else target_character
            results = controller.search_logs(search_query, limit=10)
            
            if results:
                wiki_info = ""
                for result in results:
                    content = result['raw_content']
                    log_date = result.get('log_date', 'Unknown Date')
                    ship_name = result.get('ship_name', 'Unknown Ship')
                    
                    type_indicator = f" [Mission Log - {log_date}]"
                    if ship_name and ship_name.lower() != 'unknown ship':
                        type_indicator += f" ({ship_name.upper()})"
                    
                    wiki_info += f"**{result['title']}{type_indicator}**\n{content}\n\n"
                
                print(f"   📊 Category-based character logs: {len(results)} results ({len(wiki_info)} chars)")
            else:
                wiki_info = f"No logs found specifically mentioning '{target_character}'"
                print(f"   ❌ No character-specific logs found for '{target_character}'")
        
        except Exception as e:
            print(f"   ❌ Error in category-based character log search: {e}")
            wiki_info = f"Error searching for {target_character} logs: {e}"
    
    else:
        # Standard log search behavior - ALWAYS FORCE MISSION LOGS ONLY
        wiki_info = get_log_content(user_message, mission_logs_only=True, is_roleplay=is_roleplay)
        print(f"   - Retrieved MISSION LOGS ONLY content length: {len(wiki_info)} chars")
    
    total_found = wiki_info.count("**") if wiki_info else 0
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_wiki_info = wiki_info
    
    # Check if this is a fallback response and adjust instructions accordingly
    is_fallback = is_fallback_response(wiki_info)
    fallback_instructions = ""
    if is_fallback:
        fallback_instructions = """
IMPORTANT: The database search encountered processing limitations. The response below indicates this limitation.
Present this information naturally and suggest the user try again later or rephrase their query to be more specific.
"""
    
    # Determine log type description based on strategy and selection
    if is_selection:
        if selection_type == 'random':
            log_type_description = f"random mission log{' for ' + ship_name.upper() if ship_name else ''}"
        elif selection_type in ['latest', 'recent']:
            log_type_description = f"most recent mission logs{' for ' + ship_name.upper() if ship_name else ''}"
        elif selection_type in ['first', 'earliest', 'oldest']:
            log_type_description = f"earliest mission logs{' for ' + ship_name.upper() if ship_name else ''}"
        elif selection_type in ['today', 'yesterday', 'this_week', 'last_week']:
            log_type_description = f"mission logs from {selection_type.replace('_', ' ')}{' for ' + ship_name.upper() if ship_name else ''}"
        else:
            log_type_description = f"{selection_type} mission logs{' for ' + ship_name.upper() if ship_name else ''}"
    elif strategy.get('ship_logs_only'):
        log_type_description = f"logs mentioning {strategy.get('target_ship')}"
    elif strategy.get('character_logs_only'):
        log_type_description = f"logs mentioning {strategy.get('target_character')}"
    else:
        log_type_description = "mission logs only"
    
    return f"""You are Elsie, an intelligent AI assistant aboard the USS Stardancer with access to comprehensive ship databases.

CRITICAL INSTRUCTIONS FOR LOG QUERIES - ENHANCED SEARCH STRATEGY:
- You are being asked to summarize or explain {log_type_description}
- ENHANCED SEARCH was performed: prioritizing log-specific content over general information
- Search focused specifically on mission logs when ship/character names were combined with log terms
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy
{fallback_instructions}
DATABASE QUERY: "{user_message}"
SEARCH STRATEGY: {strategy.get('reasoning', 'Standard log search')}
TOTAL LOG ENTRIES FOUND: {total_found}
SEARCH RESULTS SIZE: {len(converted_wiki_info)} characters

STRICT DATABASE ADHERENCE REQUIRED:
- ONLY use the log content provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or add any log content not explicitly provided
- If no logs are found, state clearly: "I searched the database but found no logs matching your query"
- Be comprehensive and thorough in presenting the log information
- Focus on WHO did WHAT and WHEN, providing complete details
- Include character names, their actions, dialogue, and decisions
- Mention important details like dates, locations, and significant events
- Provide full context and comprehensive summaries
- Ask: "Would you like to know more about any specific aspect?"

DATABASE SEARCH RESULTS:
{converted_wiki_info}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Present a comprehensive summary of the log content provided above. Be thorough and detailed in your analysis."""


def get_tell_me_about_context(user_message: str, is_roleplay: bool = False) -> str:
    """Generate context for 'tell me about' queries."""
    from ..ai_logic.query_detection import extract_tell_me_about_subject
    
    subject = extract_tell_me_about_subject(user_message)
    print(f"🔍 TELL ME ABOUT: '{subject}' (roleplay={is_roleplay})")
    
    # Use prioritized search that focuses on ship info and personnel over logs
    wiki_info = get_tell_me_about_content_prioritized(subject, is_roleplay=is_roleplay)
    print(f"   - Retrieved tell me about content length: {len(wiki_info)} chars")
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_wiki_info = wiki_info
    
    # Check if this is a fallback response and adjust instructions accordingly
    is_fallback = is_fallback_response(wiki_info)
    fallback_instructions = ""
    if is_fallback:
        fallback_instructions = """
IMPORTANT: The database search encountered processing limitations. The response below indicates this limitation.
Present this information naturally and suggest the user try again later or rephrase their query to be more specific.
"""
    
    return f"""You are Elsie, an intelligent Holographic Scientist aboard the USS Stardancer with expertise in stellar cartography and a knowedlge of music and dance.

CRITICAL INSTRUCTIONS FOR 'TELL ME ABOUT' QUERIES:
- You are being asked about: {subject}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- This search PRIORITIZED ship information and personnel records over mission logs
- If no information is found, say: "I don't have any information about '{subject}' in my database"
- Be comprehensive and informative in presenting the information
- Focus on key details, specifications, background, and significance
- If information comes from external sources, reference it naturally
- Ask: "Would you like to explore any particular aspect of {subject}?"
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy
{fallback_instructions}
DATABASE SEARCH RESULTS:
{converted_wiki_info if converted_wiki_info else f"No information found for '{subject}' in the database."}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Provide a comprehensive and informative response about {subject} based on the database information above."""


def get_ship_context(ship_name: str, strategy: Dict[str, Any] = None, is_roleplay: bool = False) -> str:
    """Generate context for ship information queries using Phase 1 category-based searches."""
    print(f"🚢 CATEGORY-BASED SHIP SEARCH: '{ship_name}' (roleplay={is_roleplay})")
    
    # Use Phase 1 ship search method
    try:
        from .content_retriever import get_db_controller
        controller = get_db_controller()
        
        # Use new Phase 1 search_ships method
        results = controller.search_ships(ship_name, limit=10)
        print(f"   📊 Category-based ship search returned {len(results)} results")
        
        if results:
            ship_parts = []
            for result in results:
                title = result['title']
                content = result['raw_content']
                categories = result.get('categories', [])
                
                # Add category indicator
                category_indicator = ""
                if categories:
                    if 'Ship Information' in categories:
                        category_indicator = " [Ship Information]"
                    elif any('ship' in cat.lower() or 'starship' in cat.lower() for cat in categories):
                        category_indicator = f" [Ship Data]"
                    elif categories:
                        category_indicator = f" [{categories[0]}]"
                
                page_text = f"**{title}{category_indicator}**\n{content}"
                ship_parts.append(page_text)
            
            ship_info = '\n\n---\n\n'.join(ship_parts)
            print(f"   ✅ Category-based ship search: {len(ship_info)} characters")
        else:
            print(f"   ❌ No ship results found via category search")
            ship_info = ""
    
    except Exception as e:
        print(f"   ❌ Error in category-based ship search: {e}")
        ship_info = ""
    
    if not ship_info:
        # Fallback to original ship information function
        print(f"   🔄 Falling back to original ship information search")
        ship_info = get_ship_information(ship_name)
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_ship_info = ship_info
    
    return f"""You are Elsie, an intelligent Holographic Scientist aboard the USS Stardancer with expertise in stellar cartography and a knowedlge of music and dance.

CRITICAL INSTRUCTIONS FOR SHIP QUERIES:
- You are being asked about the ship: {ship_name}
- ONLY use information provided in the SHIP DATABASE ACCESS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- Be informative and comprehensive in presenting ship information
- Include specifications, class, registry, crew complement, mission history when available
- Focus on technical details, capabilities, and significant events
- If information comes from external sources, reference it naturally
- If ship information is not in the database, say: "I don't have any records for {ship_name} in my database"
- Provide a comprehensive summary and ask: "Would you like to explore any particular aspect of this vessel?"
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy

SHIP DATABASE ACCESS:
{converted_ship_info if converted_ship_info else f"No records found for '{ship_name}' in the database."}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Provide a comprehensive and informative summary of this vessel's specifications and service record."""


def get_stardancer_info_context(user_message: str, strategy: Dict[str, Any], is_roleplay: bool = False) -> str:
    """Generate context for Stardancer-specific queries."""
    print(f"🚢 SEARCHING STARDANCER INFO (roleplay={is_roleplay})")
    
    if strategy.get('command_query'):
        print(f"   👨‍✈️ COMMAND STAFF QUERY DETECTED")
        # Search for command-related information specifically
        stardancer_info = search_by_type("Stardancer command staff captain commander", 'personnel')
        if not stardancer_info:
            stardancer_info = get_ship_information("Stardancer")
    else:
        # General Stardancer information
        stardancer_info = get_ship_information("Stardancer")
    
    print(f"   - Retrieved Stardancer info length: {len(stardancer_info)} chars")
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_stardancer_info = stardancer_info
    
    return f"""You are Elsie, an intelligent Holographic Scientist aboard the USS Stardancer with expertise in stellar cartography and a knowedlge of music and dance.

CRITICAL INSTRUCTIONS FOR STARDANCER QUERIES:
- You are being asked about the USS Stardancer
- ONLY use information provided in the STARDANCER DATABASE ACCESS section below
- Focus on the ship's specifications, crew, missions, and achievements
- If this is about command staff, emphasize leadership and command structure
- Be proud and informative about your home ship
- If no specific information is found, provide general context about the Stardancer
- Ask: "Would you like to know more about any specific aspect of the Stardancer?"
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy

STARDANCER DATABASE ACCESS:
{converted_stardancer_info if converted_stardancer_info else "No specific Stardancer information found in the database, but I can share that it's a distinguished Starfleet vessel."}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Share information about the USS Stardancer with pride and comprehensive detail."""


def get_ship_logs_context(user_message: str, is_roleplay: bool = False) -> str:
    """Generate context for ship log queries."""
    # Local import to avoid circular dependency
    from ..ai_logic.query_detection import extract_ship_log_query
    is_ship_log, ship_details = extract_ship_log_query(user_message)
    ship_name = ship_details['ship']
    print(f"🚢 SEARCHING COMPREHENSIVE SHIP DATA: {ship_name.upper()} (roleplay={is_roleplay})")
    
    ship_searches = [ship_name, f"{ship_name} log", f"{ship_name} mission", f"USS {ship_name}"]
    comprehensive_ship_info = ""
    total_ship_entries = 0
    
    for search_query in ship_searches:
        print(f"   🔎 Ship search: '{search_query}'")
        ship_results = get_ship_information(search_query)
        log_results = get_log_content(search_query, is_roleplay=is_roleplay)
        
        if ship_results and ship_results not in comprehensive_ship_info:
            comprehensive_ship_info += f"\n\n---SHIP INFO FOR '{search_query}'---\n\n{ship_results}"
            total_ship_entries += ship_results.count("**")
        
        if log_results and log_results not in comprehensive_ship_info:
            comprehensive_ship_info += f"\n\n---SHIP LOGS FOR '{search_query}'---\n\n{log_results}"
            total_ship_entries += log_results.count("**")
    
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    converted_ship_info = comprehensive_ship_info
    
    return f"""You are Elsie, the intelligent, attentive, and holographic bartender aboard the USS Stardancer. Your background in dance and music influences your warm, personable way of speaking.

CRITICAL INSTRUCTIONS FOR SHIP QUERIES:
- You are summarizing logs and information for the {ship_name.upper()}
- ONLY use information provided below - do not invent or extrapolate
- Focus on the people first - who commanded, who served, their stories
- Use musical metaphors: "orchestrated missions," "in perfect harmony," etc.
- If no information found, say: "That ship hasn't graced my database yet"
- End with: "Would you like me to explore any particular chapter of their story?"
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy

SHIP DATABASE SEARCH RESULTS:
{converted_ship_info if converted_ship_info else f"No information found in database for ship '{ship_name}'."}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Share their story with your warm, musical personality, focusing on the people who brought the ship to life."""


def get_general_with_context(user_message: str, is_roleplay: bool = False) -> str:
    """Generate general context with light database information."""
    print(f"📋 SEARCHING LIGHT CONTEXT DATA (roleplay={is_roleplay})")
    wiki_info = get_relevant_wiki_context(user_message, is_roleplay=is_roleplay)
    print(f"   - Retrieved general context length: {len(wiki_info)} chars")
    
    print(f"   ⚠️  NON-ROLEPLAY Query: Preserving real Earth dates for accuracy")
    # NON-ROLEPLAY: Preserve real Earth dates - no conversion needed
    return wiki_info if wiki_info else ""


def handle_url_request(user_message: str, is_roleplay: bool = False) -> str:
    """Handle URL requests."""
    from ..ai_logic.query_detection import extract_url_request
    
    is_url_query, url_details = extract_url_request(user_message)
    search_query = url_details['search_query']
    
    print(f"🔗 URL REQUEST: Searching for '{search_query}' (roleplay={is_roleplay})")
    
    url_info = get_log_url(search_query)
    print(f"   - Retrieved URL info length: {len(url_info)} chars")
    
    return f"""You are Elsie, an intelligent Holographic Scientist aboard the USS Stardancer with expertise in stellar cartography and a knowedlge of music and dance.

CRITICAL INSTRUCTIONS FOR URL REQUESTS:
- The user requested a URL/link for: {search_query}
- ONLY use the URL information provided below
- If a direct link was found, present it clearly
- If no URL was found, explain that no direct link is available
- Be helpful and suggest alternative search terms if needed
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy

URL SEARCH RESULTS:
{url_info}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Present the URL information clearly and helpfully.""" 