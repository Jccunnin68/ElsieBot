"""
Content Retriever - Database Content Access Layer
================================================

This module provides the core interface for retrieving content from the database.
All content retrieval now routes through the unified get_tell_me_about_content_prioritized function.

SIMPLIFIED: Removed legacy routing functions - everything uses unified search.
"""

from typing import List, Dict, Optional
import traceback
import re

from ..handlers_utils import is_fallback_response
from database_controller import get_db_controller


def get_db_controller():
    """Get database controller instance"""
    return get_db_controller()


def determine_query_type(function_name: str, content_type: str = None) -> str:
    """Determine the query type for LLM processing"""
    if 'log' in function_name.lower() or content_type == 'logs':
        return 'logs'
    elif 'ship' in function_name.lower() or content_type == 'ships':
        return 'ships'
    else:
        return 'general'


def create_query_description(function_name: str, **kwargs) -> str:
    """Create a human-readable description of the query for LLM processing"""
    if 'character' in function_name.lower():
        return f"Character information query: {kwargs.get('character_name', 'unknown')}"
    elif 'ship' in function_name.lower():
        return f"Ship information query: {kwargs.get('ship_name', 'unknown')}"
    elif 'log' in function_name.lower():
        return f"Mission log query: {kwargs.get('query', 'unknown')}"
    else:
        return f"General information query: {kwargs.get('subject', kwargs.get('query', 'unknown'))}"


def is_episode_summary(result: dict) -> bool:
    """
    Check if a result is an episode summary that should be filtered out.
    
    Episode summaries are general summaries of roleplay sessions and don't contain
    specific character or ship information that would be useful for queries.
    """
    title = result.get('title', '').lower()
    content = result.get('raw_content', '').lower()
    
    # Check for episode summary indicators in title
    episode_indicators = [
        'episode', 'session', 'summary', 'recap', 'overview',
        'part 1', 'part 2', 'part i', 'part ii'
    ]
    
    if any(indicator in title for indicator in episode_indicators):
        return True
    
    # Check for summary-style content patterns
    summary_patterns = [
        'in this episode', 'during this session', 'the crew of',
        'this episode', 'the session began', 'summary of events'
    ]
    
    if any(pattern in content for pattern in summary_patterns):
        return True
    
    return False


def search_memory_alpha(query: str, limit: int = 3, is_federation_archives: bool = False) -> str:
    """
    Search Memory Alpha (external Star Trek wiki) for information.
    
    Args:
        query: Search query
        limit: Maximum number of results
        is_federation_archives: Whether this is a federation archives request
        
    Returns:
        Formatted search results or empty string if no results
    """
    try:
        import requests
        from urllib.parse import quote
        
        print(f"MEMORY ALPHA SEARCH: '{query}' (limit={limit})")
        
        # Search Memory Alpha API
        search_url = "https://memory-alpha.fandom.com/api.php"
        search_params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'srprop': 'snippet|titlesnippet'
        }
        
        search_response = requests.get(search_url, params=search_params, timeout=10)
        search_data = search_response.json()
        
        if 'query' not in search_data or 'search' not in search_data['query']:
            print(f"   ❌ No search results found")
            return ""
        
        results = search_data['query']['search']
        if not results:
            print(f"   ❌ Empty search results")
            return ""
        
        print(f"  Found {len(results)} Memory Alpha results")
        
        # Get page content for each result
        formatted_results = []
        for result in results:
            page_title = result['title']
            page_id = result['pageid']
            
            # Get page content
            content_params = {
                'action': 'query',
                'format': 'json',
                'pageids': page_id,
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
                'exsectionformat': 'plain'
            }
            
            content_response = requests.get(search_url, params=content_params, timeout=10)
            content_data = content_response.json()
            
            if 'query' in content_data and 'pages' in content_data['query']:
                page_data = content_data['query']['pages'].get(str(page_id), {})
                page_content = page_data.get('extract', '')
                
                if page_content:
                    # Limit content length
                    if len(page_content) > 1000:
                        page_content = page_content[:1000] + "..."
                    
                    formatted_results.append(f"**{page_title}** (Memory Alpha)\n{page_content}")
        
        if formatted_results:
            final_result = '\n\n---\n\n'.join(formatted_results)
            print(f"   ✅ Memory Alpha search: {len(final_result)} characters")
            return final_result
        else:
            print(f"   ❌ No usable content found")
            return ""
            
    except Exception as e:
        print(f"   ❌ Memory Alpha search error: {e}")
        return ""


def check_elsiebrain_connection() -> bool:
    """
    Check if the Elsiebrain database is accessible.
    
    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        controller = get_db_controller()
        controller.ensure_connection()
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def get_log_content(query: str, mission_logs_only: bool = False, ship_name: Optional[str] = None) -> str:
    """
    Get log content from the database.
    
    Args:
        query: Search query for logs
        mission_logs_only: Whether to restrict to mission logs only
        ship_name: The name of the ship to search logs for, if available
        
    Returns:
        Formatted log content or fallback message
    """
    try:
        controller = get_db_controller()
        print(f"[LOG] LOG CONTENT SEARCH: '{query}' (mission_logs_only={mission_logs_only}, ship_name={ship_name})")
        
        if ship_name:
            results = controller.search_logs(query, ship_name=ship_name, limit=10)
        else:
            # Force mission logs only for log queries
            results = controller.search_pages(
                query, 
                limit=10, 
                force_mission_logs_only=True,
                debug_level=1
            )
        
        print(f"   [DATA] Found {len(results)} log results")
        
        if not results:
            return "I searched the database but found no logs matching your query."
        
        # Format results with proper log titles
        log_parts = []
        for result in results:
            original_title = result['title']
            content = result['raw_content']
            result_ship_name = result.get('ship_name', 'Unknown Ship')
            
            # Extract date from title if possible
            extracted_date = None
            
            # Try various date formats in the title
            date_patterns = [
                r'(\d{1,2}/\d{1,2}/\d{4})',      # MM/DD/YYYY or M/D/YYYY
                r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', # YYYY-MM-DD or YYYY/MM/DD
                r'(\d{1,2}-\d{1,2}-\d{4})',      # MM-DD-YYYY
                r'(\d{4}\.\d{1,2}\.\d{1,2})'     # YYYY.MM.DD
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, original_title)
                if match:
                    extracted_date = match.group(1)
                    break
            
            # Create proper log title: "Shipname Mission Log"
            if result_ship_name and result_ship_name.lower() != 'unknown ship':
                log_title = f"{result_ship_name} Mission Log"
            else:
                # Try to extract ship name from title
                ship_names = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 'banshee', 'gigantes', 'caelian', 'enterprise']
                detected_ship = None
                for ship in ship_names:
                    if ship in original_title.lower():
                        detected_ship = ship.title()
                        break
                
                if detected_ship:
                    log_title = f"{detected_ship} Mission Log"
                else:
                    log_title = "Mission Log"
            
            # Add date information if extracted from title
            if extracted_date:
                log_title += f" - {extracted_date}"
            
            # If original title has additional context beyond ship name and date, preserve it
            title_lower = original_title.lower()
            if (original_title and 
                not any(ship_indicator in title_lower for ship_indicator in ['mission log', 'log entry', 'stardate']) and
                not any(date_pattern in original_title for date_pattern in [extracted_date] if extracted_date)):
                
                # Clean up the original title by removing ship name and date if they're already in our formatted title
                clean_title = original_title
                if detected_ship:
                    clean_title = re.sub(rf'\b{re.escape(detected_ship)}\b', '', clean_title, flags=re.IGNORECASE).strip()
                if extracted_date:
                    clean_title = re.sub(rf'\b{re.escape(extracted_date)}\b', '', clean_title).strip()
                
                # Remove leading/trailing punctuation and whitespace
                clean_title = re.sub(r'^[^\w]+|[^\w]+$', '', clean_title).strip()
                
                if clean_title and len(clean_title) > 3:  # Only add if meaningful content remains
                    log_title += f" ({clean_title})"
            
            log_parts.append(f"**{log_title}**\n{content}")
        
        final_content = '\n\n---\n\n'.join(log_parts)
        print(f"   [OK] Log content: {len(final_content)} characters")
        
        # Always process logs through LLM for better formatting and narrative structure
        from .llm_query_processor import get_llm_processor
        print(f"   [PROCESS] Processing logs through secondary LLM (always enabled for logs)...")
        processor = get_llm_processor()
        result = processor.process_query_results('logs', final_content, query)
        print(f"   [OK] LLM processed: {len(final_content)} → {len(result.content)} chars")
        return result.content
        
    except Exception as e:
        print(f"   [ERROR] Error in log content search: {e}")
        return f"I encountered an error while searching for logs: {str(e)}"


def get_tell_me_about_content_prioritized(subject: str) -> str:
    """
    UNIFIED SEARCH FUNCTION: Get content for any subject using category-based search with ranking.
    
    This is the primary function for all content retrieval. It uses the enhanced
    category-based search methods with 5-tier ranking for optimal results.
    
    Search Priority:
    1. Ships: search_ships() for ship-related queries
    2. Characters: search_characters() for character-related queries  
    3. General: search_pages() for everything else
    
    Args:
        subject: The subject to search for
        
    Returns:
        Formatted search results with LLM processing if needed
    """
    try:
        controller = get_db_controller()
        print(f"🔍 UNIFIED SEARCH: '{subject}'")
        
        # Determine search strategy based on subject
        subject_lower = subject.lower()
        
        # Strategy 1: Ship search for ship-related terms
        ship_indicators = ['ship', 'vessel', 'starship', 'uss', 'stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 'banshee', 'gigantes']
        if any(indicator in subject_lower for indicator in ship_indicators):
            print(f"   🚢 Using ship search strategy")
            results = controller.search_ships(subject, limit=10)
            search_type = 'ships'
        
        # Strategy 2: Character search for character-related terms
        elif any(keyword in subject_lower for keyword in ['captain', 'commander', 'lieutenant', 'ensign', 'doctor', 'officer', 'crew']):
            print(f"   🧑 Using character search strategy")
            results = controller.search_characters(subject, limit=10)
            search_type = 'characters'
        
        # Strategy 3: General search for everything else
        else:
            print(f"   📖 Using general search strategy")
            results = controller.search_pages(subject, limit=15)
            search_type = 'general'
        
        print(f"   📊 Found {len(results)} results using {search_type} search")
        
        if not results:
            print(f"   ❌ No results found")
            return f"I don't have any information about '{subject}' in my database."
        
        # Filter out episode summaries for better results
        filtered_results = [r for r in results if not is_episode_summary(r)]
        if len(filtered_results) < len(results):
            print(f"   🧹 Filtered out {len(results) - len(filtered_results)} episode summaries")
            results = filtered_results
        
        if not results:
            print(f"   ❌ No results after filtering")
            return f"I don't have any specific information about '{subject}' in my database."
        
        # Format results with category indicators
        content_parts = []
        for result in results:
            title = result['title']
            content = result['raw_content']
            categories = result.get('categories', [])
            
            # Add category indicator
            category_indicator = ""
            if categories:
                if search_type == 'ships' and any('ship' in cat.lower() for cat in categories):
                    category_indicator = " [Ship Information]"
                elif search_type == 'characters' and 'Characters' in categories:
                    category_indicator = " [Personnel File]"
                elif categories:
                    category_indicator = f" [{categories[0]}]"
            
            content_parts.append(f"**{title}{category_indicator}**\n{content}")
        
        final_content = '\n\n---\n\n'.join(content_parts)
        print(f"   ✅ Unified search: {len(final_content)} characters")
        
        # Process through LLM if needed
        from .llm_query_processor import should_process_data, get_llm_processor
        if should_process_data(final_content):
            print(f"   🔄 Processing content through secondary LLM...")
            processor = get_llm_processor()
            query_type = 'ships' if search_type == 'ships' else 'general'
            result = processor.process_query_results(query_type, final_content, subject)
            print(f"   ✅ LLM processed: {len(final_content)} → {len(result.content)} chars")
            return result.content
        
        return final_content
        
    except Exception as e:
        print(f"   ❌ Error in unified search: {e}")
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return f"I encountered an error while searching for information about '{subject}': {str(e)}"


def get_log_url(search_query: str) -> str:
    """
    Get URL for a specific log page.
    
    Args:
        search_query: Query to find the log
        
    Returns:
        URL information or message if not found
    """
    try:
        controller = get_db_controller()
        print(f"🔗 LOG URL SEARCH: '{search_query}'")
        
        # Search for logs
        results = controller.search_pages(
            search_query, 
            limit=5, 
            force_mission_logs_only=True,
            debug_level=1
        )
        
        if not results:
            return f"I couldn't find any logs matching '{search_query}' to provide a URL for."
        
        # Return the first matching result with URL info
        first_result = results[0]
        title = first_result['title']
        
        # Construct wiki URL (this would need to be adapted for your actual wiki)
        wiki_base_url = "https://your-wiki-domain.com/wiki/"
        page_url = wiki_base_url + title.replace(' ', '_')
        
        return f"Here's the link to the log page for '{title}':\n{page_url}"
        
    except Exception as e:
        print(f"   ❌ Error in log URL search: {e}")
        return f"I encountered an error while searching for the log URL: {str(e)}"


# ==============================================================================
# LEGACY ROUTING FUNCTIONS - Now route to unified search
# ==============================================================================

def get_relevant_wiki_context(query: str, mission_logs_only: bool = False) -> str:
    """Legacy function - routes to unified search"""
    if mission_logs_only:
        return get_log_content(query, mission_logs_only=True)
    else:
        return get_tell_me_about_content_prioritized(query)


def get_ship_information(ship_name: str) -> str:
    """Legacy function - routes to unified search"""
    return get_tell_me_about_content_prioritized(ship_name)


def get_character_context(character_name: str) -> str:
    """Legacy function - routes to unified search"""
    return get_tell_me_about_content_prioritized(character_name)


def get_recent_logs(ship_name: Optional[str] = None, limit: int = 10) -> str:
    """Legacy function - routes to log search"""
    query = f"recent logs {ship_name}" if ship_name else "recent logs"
    return get_log_content(query, mission_logs_only=True)


def get_tell_me_about_content(subject: str) -> str:
    """Legacy function - routes to unified search"""
    return get_tell_me_about_content_prioritized(subject)


def get_random_log_content(ship_name: Optional[str] = None) -> str:
    """Legacy function - routes to log search"""
    query = f"random log {ship_name}" if ship_name else "random log"
    return get_log_content(query, mission_logs_only=True)


def get_temporal_log_content(selection_type: str, ship_name: Optional[str] = None, limit: int = 5) -> str:
    """Legacy function - routes to log search"""
    query = f"{selection_type} logs {ship_name}" if ship_name else f"{selection_type} logs"
    return get_log_content(query, mission_logs_only=True)





def search_titles_containing(search_term: str, limit: int = 10) -> List[Dict]:
    """
    Search for pages with titles containing the search term.
    
    Args:
        search_term: Term to search for in titles
        limit: Maximum number of results
        
    Returns:
        List of matching page dictionaries
    """
    try:
        controller = get_db_controller()
        return controller.search_pages(search_term, limit=limit)
    except Exception as e:
        print(f"❌ Error in search_titles_containing: {e}")
        return [] 