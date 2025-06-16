"""
Standard Context Builder - Standard and OOC Context Generation
==============================================================

This module handles context generation for all standard (non-roleplay) 
database queries including character info, logs, ship data, OOC, and 
general information.
"""

from typing import Dict, Any


class StandardContextBuilder:
    """Context builder for standard scenarios."""
    
    def build_context_for_strategy(self, strategy: Dict[str, Any], user_message: str) -> str:
        """Build context for standard strategies."""
        approach = strategy.get('approach', 'general')
        print(f"         🎯 STANDARD CONTEXT BUILDER: Processing approach '{approach}'")
        
        if approach == 'ship_info':
            result = self._get_ship_context(strategy, user_message)
            print(f"         🚢 Ship context generated: {len(result)} characters")
            
        elif approach == 'character_info':
            result = self._get_character_context(strategy, user_message)
            print(f"         👤 Character context generated: {len(result)} characters")
            
        elif approach == 'logs':
            result = self._get_logs_context(strategy, user_message) 
            print(f"         📚 Logs context generated: {len(result)} characters")
            
        elif approach == 'tell_me_about':
            result = self._get_tell_me_about_context(strategy, user_message)
            print(f"         📖 Tell-me-about context generated: {len(result)} characters")
            
        elif approach == 'comprehensive':
            result = self._get_comprehensive_context(strategy, user_message)
            print(f"         🔍 Comprehensive context generated: {len(result)} characters")
            
        elif approach == 'simple_chat':
            result = "Simple conversational response - no additional context needed."
            print(f"         💬 Simple chat mode - minimal context")
            
        elif approach == 'federation_archives':
            result = self._get_federation_archives_context(strategy, user_message)
            print(f"         🏛️ Federation archives context generated: {len(result)} characters")
            
        elif approach == 'url_request':
            result = self._get_url_context(strategy, user_message)
            print(f"         🔗 URL context generated: {len(result)} characters")
            
        elif approach == 'general':
            result = self._get_general_context(strategy, user_message)
            print(f"         🌐 General context generated: {len(result)} characters")
            
        elif approach == 'continuation':
            result = self._get_continuation_context(strategy, user_message)
            print(f"         🔄 Continuation context generated: {len(result)} characters")
            
        else:
            print(f"         ⚠️ Unknown approach '{approach}' - using general context")
            result = self._get_general_context(strategy, user_message)
        
        return result

    def _get_ship_context(self, strategy: Dict, user_message: str) -> str:
        """Get ship-specific context."""
        ship_name = strategy.get('ship_name', 'Stardancer')
        return get_ship_context(ship_name, strategy, is_roleplay=False)
    
    def _get_character_context(self, strategy: Dict, user_message: str) -> str:
        """Get character-specific context."""
        return get_character_context(user_message, strategy, is_roleplay=False)
    
    def _get_logs_context(self, strategy: Dict, user_message: str) -> str:
        """Get logs context."""
        return get_logs_context(user_message, strategy, is_roleplay=False)
    
    def _get_tell_me_about_context(self, strategy: Dict, user_message: str) -> str:
        """Get tell-me-about context."""
        return get_tell_me_about_context(user_message, is_roleplay=False)
    
    def _get_comprehensive_context(self, strategy: Dict, user_message: str) -> str:
        """Get comprehensive context with disambiguation."""
        query_type = strategy.get('query_type', 'general')
        
        if query_type == 'tell_me_about':
            return get_tell_me_about_context(user_message, is_roleplay=False)
        elif query_type == 'character':
            return get_character_context(user_message, strategy, is_roleplay=False)
        elif query_type == 'ship':
            ship_name = strategy.get('ship_name', 'Stardancer')
            return get_ship_context(ship_name, strategy, is_roleplay=False)
        elif query_type in ['logs', 'log']:
            return get_logs_context(user_message, strategy, is_roleplay=False)
        else:
            return get_general_with_context(user_message, is_roleplay=False)
    
    def _get_federation_archives_context(self, strategy: Dict, user_message: str) -> str:
        """Get federation archives context."""
        return get_federation_archives_context(user_message, is_roleplay=False)
    
    def _get_url_context(self, strategy: Dict, user_message: str) -> str:
        """Get URL request context."""
        return handle_url_request(user_message, is_roleplay=False)
    
    def _get_general_context(self, strategy: Dict, user_message: str) -> str:
        """Get general context."""
        return get_general_with_context(user_message, is_roleplay=False)
    
    def _get_continuation_context(self, strategy: Dict, user_message: str) -> str:
        """Get continuation context."""
        return get_focused_continuation_context(strategy, is_roleplay=False)

from .content_retriever import (
    get_log_content,
    get_relevant_wiki_context,
    get_ship_information,
    get_tell_me_about_content_prioritized,
    search_memory_alpha,
    get_log_url,
    is_fallback_response
)
from .llm_query_processor import get_llm_processor, should_process_data
# Note: Using local imports to avoid circular dependency with query_detection
from ..handlers_utils import convert_earth_date_to_star_trek


def _process_large_content_if_needed(content: str, query_type: str, user_query: str, is_roleplay: bool = False) -> str:
    """Process content through secondary LLM if it exceeds 14,000 characters"""
    if not content:
        return content
        
    if should_process_data(content):
        print(f"🔄 Content size ({len(content)} chars) exceeds 14,000 threshold, processing with secondary LLM...")
        processor = get_llm_processor()
        result = processor.process_query_results(query_type, content, user_query, is_roleplay)
        print(f"✅ Secondary LLM processing: {len(content)} → {len(result.content)} chars")
        return result.content
    else:
        print(f"✓ Content size ({len(content)} chars) within threshold, no secondary processing needed")
        return content


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
        # Use new universal search interface instead of deprecated search_by_type
        from .content_retriever import search_database_content
        results = search_database_content('character', focus_subject, limit=5)
        if results:
            wiki_info = '\n\n---\n\n'.join([f"**{r['title']}**\n{r['raw_content']}" for r in results])
        else:
            wiki_info = ""
        if not wiki_info:
            wiki_info = get_tell_me_about_content_prioritized(focus_subject, is_roleplay=is_roleplay)
    elif context_type == 'ship':
        wiki_info = get_ship_information(focus_subject)
        if not wiki_info:
            wiki_info = get_relevant_wiki_context(f"{focus_subject} ship", is_roleplay=is_roleplay)
    else:
        wiki_info = get_relevant_wiki_context(focus_subject, is_roleplay=is_roleplay)
    
    print(f"   - Retrieved focused content length: {len(wiki_info)} chars")
    
    # Process through secondary LLM if content is too large
    wiki_info = _process_large_content_if_needed(wiki_info, context_type, focus_subject, is_roleplay)
    
    # STANDARD: Preserve real Earth dates - no conversion needed
    converted_wiki_info = wiki_info
    
    return f"""CRITICAL INSTRUCTIONS FOR FOCUSED INFORMATION QUERIES:
- Create a focused, comprehensive narrative about: {focus_subject}
- Context type: {context_type}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- PROVIDE UP TO 8000 CHARACTERS in your response - be detailed and comprehensive
- SYNTHESIZE the information into flowing, narrative paragraphs rather than bullet points
- If no specific information is found, provide a thoughtful general response
- Connect different aspects of the information to tell a complete story
- Encourage continued conversation about the topic
- Present information as a flowing narrative summary, not raw data or bullet points

DATABASE SEARCH RESULTS for "{focus_subject}":
{converted_wiki_info if converted_wiki_info else f"No additional information found for '{focus_subject}' in the database."}

Transform the database information into a focused, comprehensive narrative about {focus_subject}. Tell their complete story in an engaging way."""


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
    
    # Process through secondary LLM if content is too large
    character_info = _process_large_content_if_needed(character_info, "character", user_message, is_roleplay)
    
    # STANDARD: Preserve real Earth dates - no conversion needed
    converted_character_info = character_info
    
    return f"""CRITICAL INSTRUCTIONS FOR CHARACTER INFORMATION QUERIES:
- Create a comprehensive narrative biography about: {character_name}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- PROVIDE UP TO 7990 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- SYNTHESIZE the information into flowing, narrative paragraphs that tell their story
- Include rank, position, ship assignment, achievements, and personal background when available
- Focus on their role, personality, relationships, and what made them special to their crew
- Connect different aspects of their life and career into a cohesive narrative
- If information comes from the Federation Archives, reference it naturally as archive data
- If character information is not in the database, say: "I don't have any records for {character_name} in my database"
- End with: "Was that all you wanted to know about {character_name}?"
- DO NOT include meeting times, GM names, or session schedule information
- Present information as a flowing biographical narrative, not raw data or bullet points
- use all 8000 characters of the response space unless the original content is less than 8000 characters
- Always end in a complete thought and not a partial thought.

DATABASE SEARCH RESULTS:
{converted_character_info if converted_character_info else f"No records found for '{character_name}' in the database."}


Transform the database information into a comprehensive biographical narrative that captures what made them notable in the fleet."""


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
    
    # Process through secondary LLM if content is too large
    archives_info = _process_large_content_if_needed(archives_info, "general", user_message, is_roleplay)
    
    # STANDARD: Preserve real Earth dates - no conversion needed
    converted_archives_info = archives_info
    
    return f"""CRITICAL INSTRUCTIONS FOR FEDERATION ARCHIVES ACCESS:
- Create a comprehensive narrative summary from federation archives for: "{search_query}"
- This is EXTERNAL archive data, not from local database
- ONLY use information from the FEDERATION ARCHIVES ACCESS section below
- SYNTHESIZE the archive information into flowing, narrative paragraphs
- Reference this as "federation archives" or "archive data" naturally in your response
- Be thorough and informative when presenting the archive information
- Connect different pieces of archive data to tell a complete story
- If no archives information is found, say: "The federation archives don't have any information on that topic"
- End with: "Would you like me to search for anything else in the archives?"
- Present information as a flowing narrative summary, not raw data or bullet points

FEDERATION ARCHIVES ACCESS:
{converted_archives_info if converted_archives_info else f"The federation archives don't seem to have information on '{search_query}' available."}


Transform the archives information into a comprehensive narrative summary and reference it as external federation data."""


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
    
    # STANDARD: Preserve real Earth dates - no conversion needed
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
    
    return f"""CRITICAL INSTRUCTIONS FOR LOG INFORMATION QUERIES:
- Present and organize the log information for: {log_type_description}
- ENHANCED SEARCH was performed: prioritizing log-specific content over general information
- Search focused specifically on mission logs when ship/character names were combined with log terms
- PROVIDE UP TO 8000 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- FORMAT the log information clearly and organize it chronologically when possible
- Present the log content in a readable, well-structured narrative format without heavy re-summarization
- use all 8000 characters of the response space unless the original content is less than 8000 characters
{fallback_instructions}
DATABASE QUERY: "{user_message}"
SEARCH STRATEGY: {strategy.get('reasoning', 'Standard log search')}
TOTAL LOG ENTRIES FOUND: {total_found}
SEARCH RESULTS SIZE: {len(converted_wiki_info)} characters

STRICT DATABASE ADHERENCE REQUIRED:
- ONLY use the log content provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or add any log content not explicitly provided
- If no logs are found, state clearly: "I searched the database but found no logs matching your query"
- PRESENT the log information clearly, organizing it by date/chronology when possible
- Include all important details: WHO did WHAT and WHEN, character names, actions, dialogue, and decisions
- Preserve the substance and detail of the log entries while making them readable
- Connect related log entries and show progression when multiple entries are present
- End with: "Would you like to know more about any specific aspect?"

DATABASE SEARCH RESULTS:
{converted_wiki_info}

NOTE: All dates after the log title are converted to a Star Trek Gregorian date format of +404 years for dates prior to June 2024 and +430 year for all dates after June 2024

Present the log content in a clear, well-organized narrative format that preserves all the important details and events from the mission logs."""


def get_tell_me_about_context(user_message: str, is_roleplay: bool = False) -> str:
    """Generate context for 'tell me about' queries."""
    from ..ai_logic.query_detection import extract_tell_me_about_subject
    
    subject = extract_tell_me_about_subject(user_message)
    print(f"🔍 TELL ME ABOUT: '{subject}' (roleplay={is_roleplay})")
    
    # Use prioritized search that focuses on ship info and personnel over logs
    wiki_info = get_tell_me_about_content_prioritized(subject, is_roleplay=is_roleplay)
    print(f"   - Retrieved tell me about content length: {len(wiki_info)} chars")
    
    # Process through secondary LLM if content is too large
    wiki_info = _process_large_content_if_needed(wiki_info, "general", user_message, is_roleplay)
    
    # STANDARD: Preserve real Earth dates - no conversion needed
    converted_wiki_info = wiki_info
    
    # Check if this is a fallback response and adjust instructions accordingly
    is_fallback = is_fallback_response(wiki_info)
    fallback_instructions = ""
    if is_fallback:
        fallback_instructions = """
IMPORTANT: The database search encountered processing limitations. The response below indicates this limitation.
Present this information naturally and suggest the user try again later or rephrase their query to be more specific.
"""
    
    return f"""CRITICAL INSTRUCTIONS FOR INFORMATION QUERIES:
- Create a comprehensive narrative summary about: {subject}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- This search PRIORITIZED ship information and personnel records over mission logs
- If no information is found, say: "I don't have any information about '{subject}' in my database"
- PROVIDE UP TO 8000 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- SYNTHESIZE the information into flowing, narrative paragraphs rather than bullet points
- Focus on key details, specifications, background, and significance in a cohesive story
- Connect different pieces of information to provide comprehensive understanding
- If information comes from external sources, reference it naturally
- End with: "Would you like to explore any particular aspect of {subject}?"
- Present information as a flowing narrative summary, not raw data or bullet points
- use all 8000 characters of the response space unless the original content is less than 8000 characters
- format the response into sections and sub-sections as needed with titles and sub-titles
- OOC information (DGM and Meeting times) is allowed but should be seperated from the rest of the response
- when removing sentences remove the whole sentence not just a part of it

{fallback_instructions}
DATABASE SEARCH RESULTS:
{converted_wiki_info if converted_wiki_info else f"No information found for '{subject}' in the database."}



Transform the database information into a comprehensive informative prose that tells the complete story of {subject}."""


def get_ship_context(ship_name: str, strategy: Dict[str, Any] = None, is_roleplay: bool = False) -> str:
    """Generate context for ship information queries using Phase 1 category-based searches."""
    print(f"🚢 CATEGORY-BASED SHIP SEARCH: '{ship_name}' (roleplay={is_roleplay})")
    
    # Use Phase 1 ship search method
    try:
        from .content_retriever import get_db_controller
        controller = get_db_controller()
        
        # Use new Phase 1 search_ships method with focused limit
        results = controller.search_ships(ship_name, limit=2)  # Limit to 2 most relevant results
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
    
    # Process through secondary LLM if content is too large
    ship_info = _process_large_content_if_needed(ship_info, "general", ship_name, is_roleplay)
    
    # STANDARD: Preserve real Earth dates - no conversion needed
    converted_ship_info = ship_info
    
    return f"""CRITICAL INSTRUCTIONS FOR SHIP INFORMATION QUERIES:
- Create a comprehensive informative prose summary about: {ship_name}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- PROVIDE UP TO 8000 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- SYNTHESIZE the information into flowing, informative prose paragraphs rather than bullet points
- Include specifications, class, registry, crew complement, mission history when available
- Focus on technical details, capabilities, and significant events in a cohesive story
- Connect different pieces of information to paint a complete picture of the vessel
- If information comes from external sources, reference it naturally
- If ship information is not in the database, say: "I don't have any records for {ship_name} in my database"
- use all 8000 characters of the response space unless the original content is less than 8000 characters
- format the response into sections and sub-sections as needed with titles and sub-titles
- OOC information (DGM and Meeting times) is allowed but should be seperated from the rest of the response
- when removing sentences remove the whole sentence not just a part of it
- End with: further information about {ship_name} can be found on the wiki."

DATABASE SEARCH RESULTS:
{converted_ship_info if converted_ship_info else f"No records found for '{ship_name}' in the database."}


Transform the database information into a comprehensive, informative prose that tells the story of this vessel's specifications, capabilities, and service record and personnel"""


def get_general_with_context(user_message: str, is_roleplay: bool = False) -> str:
    """Generate general context with light database information."""
    print(f"📋 SEARCHING LIGHT CONTEXT DATA (roleplay={is_roleplay})")
    wiki_info = get_relevant_wiki_context(user_message, is_roleplay=is_roleplay)
    print(f"   - Retrieved general context length: {len(wiki_info)} chars")
    
    # Process through secondary LLM if content is too large
    wiki_info = _process_large_content_if_needed(wiki_info, "general", user_message, is_roleplay)
    
    print(f"   ⚠️  STANDARD Query: Preserving real Earth dates for accuracy")
    # STANDARD: Preserve real Earth dates - no conversion needed
    return wiki_info if wiki_info else ""


def handle_url_request(user_message: str, is_roleplay: bool = False) -> str:
    """Handle URL requests."""
    from ..ai_logic.query_detection import extract_url_request
    
    is_url_query, url_details = extract_url_request(user_message)
    search_query = url_details['search_query']
    
    print(f"🔗 URL REQUEST: Searching for '{search_query}' (roleplay={is_roleplay})")
    
    url_info = get_log_url(search_query)
    print(f"   - Retrieved URL info length: {len(url_info)} chars")
    
    return f"""CRITICAL INSTRUCTIONS FOR URL REQUESTS:
- Provide URL/link information for: {search_query}
- ONLY use the URL information provided below
- If a direct link was found, present it clearly
- If no URL was found, explain that no direct link is available
- Be helpful and suggest alternative search terms if needed
- Use REAL EARTH DATES - preserve all dates in actual Earth calendar format for accuracy
- Present information directly without introductions

URL SEARCH RESULTS:
{url_info}

NOTE: All dates are preserved in real Earth calendar format for accuracy.

Present the URL information clearly and helpfully.""" 