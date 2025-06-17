"""
Standard Context Builder - Standard and OOC Context Generation
==============================================================

This module handles context generation for all standard (non-roleplay) 
database queries including character info, logs, ship data, OOC, and 
general information.

SIMPLIFIED: Now routes all queries through the unified search system.
"""

from typing import Dict, Any

from handlers.handlers_utils import is_fallback_response


class StandardContextBuilder:
    """Context builder for standard scenarios."""
    
    def build_context_for_strategy(self, strategy: Dict[str, Any], user_message: str) -> str:
        """Build context for standard strategies."""
        approach = strategy.get('approach', 'comprehensive')
        print(f"         🎯 STANDARD CONTEXT BUILDER: Processing approach '{approach}'")
        
        if approach == 'logs':
            result = self._get_logs_context(strategy, user_message) 
            print(f"         📚 Logs context generated: {len(result)} characters")
            
        elif approach == 'comprehensive':
            result = self._get_unified_context(strategy, user_message)
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

        elif approach == 'continuation':
            result = self._get_continuation_context(strategy)
            print(f"         🔄 Continuation context generated: {len(result)} characters")
            
        else:
            print(f"         ⚠️ Unknown approach '{approach}' - using comprehensive context")
            result = self._get_unified_context(strategy, user_message)
        
        return result

    def _get_unified_context(self, strategy: Dict, user_message: str) -> str:
        """Get context using the unified search system."""
        subject = strategy.get('subject', user_message)
        
        # This logic was previously in the standalone get_tell_me_about_context function.
        # Inlining it here fixes a bug where the subject was being re-parsed incorrectly.
        print(f"🔍 TELL ME ABOUT: '{subject}'")
    
        # Use unified search system
        wiki_info = get_tell_me_about_content_prioritized(subject)
        print(f"   - Retrieved tell me about content length: {len(wiki_info)} chars")
    
        # Check if this is a fallback response and adjust instructions accordingly
        is_fallback = is_fallback_response(wiki_info)
        fallback_instructions = ""
        if is_fallback:
            fallback_instructions = """
IMPORTANT: The database search encountered processing limitations. The response below indicates this limitation.
Present this information naturally and suggest the user try again later or rephrase their query to be more specific.
"""
    
        return f"""CRITICAL INSTRUCTIONS FOR INFORMATION QUERIES:
- Create a comprehensive technical summary about: {subject}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- This search PRIORITIZED ship information and personnel records over mission logs
- If no information is found, say: "I don't have any information about '{subject}' in my database"
- PROVIDE UP TO 30000 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- SYNTHESIZE the information into flowing, narrative paragraphs rather than bullet points
- Focus on key details, specifications, background, and significance in a cohesive story
- Connect different pieces of information to provide comprehensive understanding
- If information comes from external sources, reference it naturally
- End with: "Would you like to explore any particular aspect of {subject}?"
- Present information as a flowing narrative summary, not raw data or bullet points
- use all 30000 characters of the response space unless the original content is less than 30000 characters
- format the response into sections and sub-sections as needed with titles and sub-titles
- OOC information (DGM and Meeting times) is allowed but should be seperated from the rest of the response
- when removing sentences remove the whole sentence not just a part of it

{fallback_instructions}
DATABASE SEARCH RESULTS:
{wiki_info if wiki_info else f"No information found for '{subject}' in the database."}



Transform the database information into a comprehensive informative prose that tells the complete story of {subject}."""
    
    def _extract_subject_from_strategy(self, strategy: Dict, user_message: str, context_type: str) -> str:
        """DEPRECATED: Subject is now extracted directly in the handler."""
        return strategy.get('subject', user_message)
    
    def _get_logs_context(self, strategy: Dict, user_message: str) -> str:
        """Get logs context."""
        print(f"📋 SEARCHING LOG DATA")
        
        # The subject from the strategy is the best candidate for ship_name
        ship_name = strategy.get('subject')

        # Use unified log search
        wiki_info = get_log_content(user_message, mission_logs_only=True, ship_name=ship_name)
        print(f"   - Retrieved LOG content length: {len(wiki_info)} chars")
        
        total_found = wiki_info.count("**") if wiki_info else 0
        
        # Check if this is a fallback response and adjust instructions accordingly
        is_fallback = is_fallback_response(wiki_info)
        fallback_instructions = ""
        if is_fallback:
            fallback_instructions = """
IMPORTANT: The database search encountered processing limitations. The response below indicates this limitation.
Present this information naturally and suggest the user try again later or rephrase their query to be more specific.
"""
        
        # Determine log type description
        log_type_description = "mission logs matching your query"
        
        return f"""CRITICAL INSTRUCTIONS FOR LOG NARRATIVE STORYTELLING:
- Transform the log information into a compelling NARRATIVE STORY about: {log_type_description}
- READ THE ENTIRE LOG CONTENT and determine the best way to convert it into a cohesive story
- PROVIDE UP TO 28000 CHARACTERS (7600 tokens) in your response - use the full space to tell the complete story
- NARRATIVE STRUCTURE: Create a flowing story with beginning, middle, and end that captures all key events
- STORYTELLING FOCUS: Present as an engaging narrative that reads like a story, not a report or summary
- PRESERVE ALL IMPORTANT DETAILS: Include WHO did WHAT and WHEN, character names, actions, dialogue, and decisions
- CHRONOLOGICAL FLOW: Organize events in story order, connecting related incidents into narrative arcs
- CHARACTER DEVELOPMENT: Show how characters evolved and made decisions throughout the events
- DRAMATIC TENSION: Highlight conflicts, challenges, and resolutions that drive the story forward
- IMMERSIVE EXPERIENCE: Write as if telling an engaging story to someone who wants to experience the events
- COMPLETE STORY ARC: Ensure the narrative has proper story structure with setup, conflict, and resolution
- USE FULL CHARACTER LIMIT: Expand the story to use all 28000 characters unless source material is shorter
- MAINTAIN ACCURACY: All story elements must come from the provided log content - no invention or speculation
{fallback_instructions}
DATABASE QUERY: "{user_message}"
SEARCH STRATEGY: {strategy.get('reasoning', 'Standard log search')}
TOTAL LOG ENTRIES FOUND: {total_found}
SEARCH RESULTS SIZE: {len(wiki_info)} characters

STRICT DATABASE ADHERENCE FOR STORYTELLING:
- ONLY use the log content provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or add any story elements not explicitly provided
- If no logs are found, state clearly: "I searched the database but found no logs matching your query"
- TRANSFORM raw log data into compelling narrative prose while preserving all factual content
- Connect separate log entries into a unified story arc when multiple entries are present
- Show cause and effect relationships between events to create narrative flow
- Include emotional context and character motivations when evident in the logs
- End with: "For more information about this topic, please check the wiki."

DATABASE SEARCH RESULTS:
{wiki_info}

NOTE: All dates after the log title are converted to a Star Trek Gregorian date format of +404 years for dates prior to June 2024 and +430 year for all dates after June 2024

STORYTELLING DIRECTIVE: Transform this log content into a rich, immersive narrative story that brings the events to life. Read the entire content, understand the full scope of events, and craft a compelling story that uses the full 28000 character space to tell the complete tale with proper narrative structure, character development, and dramatic flow."""

    def _get_federation_archives_context(self, strategy: Dict, user_message: str) -> str:
        """Get federation archives context."""
        search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
        search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
        if not search_query:
            search_query = "general information"
        
        print(f"🏛️ SEARCHING FEDERATION ARCHIVES: '{search_query}'")
        archives_info = search_memory_alpha(search_query, limit=3, is_federation_archives=True)
        print(f"   - Retrieved archives content length: {len(archives_info)} chars")
        
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
{archives_info if archives_info else f"The federation archives don't seem to have information on '{search_query}' available."}


Transform the archives information into a comprehensive narrative summary and reference it as external federation data."""

    def _get_url_context(self, strategy: Dict, user_message: str) -> str:
        """Get URL request context."""
        return handle_url_request(user_message)
    
    def _get_continuation_context(self, strategy: Dict) -> str:
        """Get continuation context."""
        return get_focused_continuation_context(strategy)

from .content_retriever import (
    get_log_content,
    get_tell_me_about_content_prioritized,
    search_memory_alpha,
    get_log_url,
)
from .llm_query_processor import get_llm_processor, should_process_data
from ..handlers_utils import is_fallback_response






def get_focused_continuation_context(strategy: Dict[str, Any]) -> str:
    """Generate context for focused continuation requests."""
    focus_subject = strategy.get('focus_subject', '')
    context_type = strategy.get('context_type', 'general')
    
    print(f"🎯 FOCUSED CONTINUATION: Searching for '{focus_subject}' in {context_type} context")
    
    # Use unified search for all continuation contexts
    wiki_info = get_tell_me_about_content_prioritized(focus_subject)
    print(f"   - Retrieved focused content length: {len(wiki_info)} chars")
    
    return f"""CRITICAL INSTRUCTIONS FOR FOCUSED INFORMATION QUERIES:
- Create a focused, comprehensive narrative about: {focus_subject}
- Context type: {context_type}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- PROVIDE UP TO 13000 CHARACTERS in your response - be detailed and comprehensive
- SYNTHESIZE the information into flowing, narrative paragraphs rather than bullet points
- If no specific information is found, provide a thoughtful general response
- Connect different aspects of the information to tell a complete story
- Encourage continued conversation about the topic
- Present information as a flowing narrative summary, not raw data or bullet points

DATABASE SEARCH RESULTS for "{focus_subject}":
{wiki_info if wiki_info else f"No additional information found for '{focus_subject}' in the database."}

Transform the database information into a focused, comprehensive narrative about {focus_subject}. Tell their complete story in an engaging way."""


def get_character_context(user_message: str, strategy: Dict[str, Any] = None) -> str:
    """Generate context for character information queries using unified search."""
    # Get character name from strategy if available, otherwise extract from message
    if strategy and 'character_name' in strategy:
        character_name = strategy['character_name']
    else:
        # Local import to avoid circular dependency
        from ..ai_logic.query_detection import is_character_query
        is_character, character_name = is_character_query(user_message)
    
    print(f"🧑 UNIFIED CHARACTER SEARCH: '{character_name}'")
    
    # Use unified search system
    character_info = get_tell_me_about_content_prioritized(character_name)
    print(f"   ✅ Unified character search: {len(character_info)} characters")
    
    return f"""CRITICAL INSTRUCTIONS FOR CHARACTER INFORMATION QUERIES:
- Create a comprehensive narrative biography about: {character_name}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- PROVIDE UP TO 13000 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- SYNTHESIZE the information into flowing, narrative paragraphs that tell their story
- Include rank, position, ship assignment, achievements, and personal background when available
- Focus on their role, personality, relationships, and what made them special to their crew
- Connect different aspects of their life and career into a cohesive narrative
- If information comes from the Federation Archives, reference it naturally as archive data
- If character information is not in the database, say: "I don't have any records for {character_name} in my database"
- End with: "Was that all you wanted to know about {character_name}?"
- DO NOT include meeting times, GM names, or session schedule information
- Present information as a flowing biographical narrative, not raw data or bullet points
- use all 13000 characters of the response space unless the original content is less than 13000 characters
- Always end in a complete thought and not a partial thought.

DATABASE SEARCH RESULTS:
{character_info if character_info else f"No records found for '{character_name}' in the database."}


Transform the database information into a comprehensive biographical narrative that captures what made them notable in the fleet."""


def get_federation_archives_context(user_message: str) -> str:
    """Generate context for federation archives queries."""
    search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
    search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
    if not search_query:
        search_query = "general information"
    
    print(f"🏛️ SEARCHING FEDERATION ARCHIVES: '{search_query}'")
    archives_info = search_memory_alpha(search_query, limit=3, is_federation_archives=True)
    print(f"   - Retrieved archives content length: {len(archives_info)} chars")
    
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
{archives_info if archives_info else f"The federation archives don't seem to have information on '{search_query}' available."}


Transform the archives information into a comprehensive narrative summary and reference it as external federation data."""


def get_tell_me_about_context(user_message: str) -> str:
    """Generate context for 'tell me about' queries."""
    from ..ai_logic.query_detection import extract_tell_me_about_subject
    
    subject = extract_tell_me_about_subject(user_message)
    print(f"🔍 TELL ME ABOUT: '{subject}'")
    
    # Use unified search system
    wiki_info = get_tell_me_about_content_prioritized(subject)
    print(f"   - Retrieved tell me about content length: {len(wiki_info)} chars")
    
    # Check if this is a fallback response and adjust instructions accordingly
    is_fallback = is_fallback_response(wiki_info)
    fallback_instructions = ""
    if is_fallback:
        fallback_instructions = """
IMPORTANT: The database search encountered processing limitations. The response below indicates this limitation.
Present this information naturally and suggest the user try again later or rephrase their query to be more specific.
"""
    
    return f"""CRITICAL INSTRUCTIONS FOR INFORMATION QUERIES:
- Create a comprehensive technical summary about: {subject}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- This search PRIORITIZED ship information and personnel records over mission logs
- If no information is found, say: "I don't have any information about '{subject}' in my database"
- PROVIDE UP TO 30000 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- SYNTHESIZE the information into flowing, narrative paragraphs rather than bullet points
- Focus on key details, specifications, background, and significance in a cohesive story
- Connect different pieces of information to provide comprehensive understanding
- If information comes from external sources, reference it naturally
- End with: "Would you like to explore any particular aspect of {subject}?"
- Present information as a flowing narrative summary, not raw data or bullet points
- use all 30000 characters of the response space unless the original content is less than 30000 characters
- format the response into sections and sub-sections as needed with titles and sub-titles
- OOC information (DGM and Meeting times) is allowed but should be seperated from the rest of the response
- when removing sentences remove the whole sentence not just a part of it

{fallback_instructions}
DATABASE SEARCH RESULTS:
{wiki_info if wiki_info else f"No information found for '{subject}' in the database."}



Transform the database information into a comprehensive informative prose that tells the complete story of {subject}."""


def get_ship_context(ship_name: str, strategy: Dict[str, Any] = None) -> str:
    """Generate context for ship information queries using unified search."""
    print(f"🚢 UNIFIED SHIP SEARCH: '{ship_name}'")
    
    # Use unified search system
    ship_info = get_tell_me_about_content_prioritized(ship_name)
    print(f"   ✅ Unified ship search: {len(ship_info)} characters")
    
    return f"""CRITICAL INSTRUCTIONS FOR SHIP INFORMATION QUERIES:
- Create a comprehensive informative prose summary about: {ship_name}
- ONLY use information provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- PROVIDE UP TO 13000 CHARACTERS in your response - be comprehensive and detailed summarize if needed to stay under the limit
- SYNTHESIZE the information into flowing, informative prose paragraphs rather than bullet points
- Include specifications, class, registry, crew complement, mission history when available
- Focus on technical details, capabilities, and significant events in a cohesive story
- Connect different pieces of information to paint a complete picture of the vessel
- If information comes from external sources, reference it naturally
- If ship information is not in the database, say: "I don't have any records for {ship_name} in my database"
- use all 30000 characters of the response space unless the original content is less than 13000 characters
- format the response into sections and sub-sections as needed with titles and sub-titles
- OOC information (DGM and Meeting times) is allowed but should be seperated from the rest of the response
- when removing sentences remove the whole sentence not just a part of it
- End with: further information about {ship_name} can be found on the wiki."

DATABASE SEARCH RESULTS:
{ship_info if ship_info else f"No records found for '{ship_name}' in the database."}


Transform the database information into a comprehensive, informative prose that tells the story of this vessel's specifications, capabilities, and service record and personnel"""


def handle_url_request(user_message: str) -> str:
    """Handle URL requests."""
    from ..ai_logic.query_detection import extract_url_request
    
    url_details = extract_url_request(user_message)
    search_query = url_details[1] if url_details[0] else user_message
    
    print(f"🔗 URL REQUEST: Searching for '{search_query}'")
    
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