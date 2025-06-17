"""
Content Retriever - Simplified Single-Function Interface
========================================================

This module provides a single unified interface for retrieving content from the database.
All content retrieval now routes through the single get_content function.

SIMPLIFIED: Single get_content function replaces all legacy routing functions.
"""

from typing import List, Dict, Optional
import traceback
import re

from ..handlers_utils import is_fallback_response
from database_controller import get_db_controller


def get_content(query: str, content_type: str = 'general', 
                temporal_selector: Optional[str] = None,
                ship_name: Optional[str] = None) -> str:
    """
    Single unified content retrieval method.
    
    Args:
        query: Search query
        content_type: 'logs', 'ships', 'characters', 'general'
        temporal_selector: 'latest', 'first', 'random', etc. (for logs only)
        ship_name: Optional ship filter
    
    Returns:
        Formatted content ready for LLM processing
    """
    try:
        controller = get_db_controller()
        print(f"🔍 UNIFIED CONTENT RETRIEVAL: '{query}' (type={content_type}, temporal={temporal_selector}, ship={ship_name})")
        
        # Determine categories and search parameters based on content type
        categories = None
        order_by = 'relevance'
        limit = 10
        
        if content_type == 'logs':
            categories = controller.get_log_categories()
            if temporal_selector:
                if temporal_selector == 'latest':
                    order_by = 'chronological'
                    limit = 1
                elif temporal_selector == 'first':
                    order_by = 'id_asc'
                    limit = 1
                elif temporal_selector == 'random':
                    order_by = 'random'
                    limit = 1
                else:
                    order_by = 'chronological'
                    limit = 3
        elif content_type == 'ships':
            categories = controller.get_ship_categories()
            limit = 5
        elif content_type == 'characters':
            categories = controller.get_character_categories()
            limit = 5
        else:  # general
            limit = 15
        
        # Perform the unified search
        results = controller.search(
            query=query,
            categories=categories,
            limit=limit,
            order_by=order_by,
            ship_name=ship_name
        )
        
        print(f"   📊 Found {len(results)} results")
        
        if not results:
            return f"I searched the database but found no {content_type} matching your query '{query}'."
        
        # Format results based on content type
        if content_type == 'logs':
            return _format_log_results(results, controller, temporal_selector, query)
        else:
            return _format_general_results(results, content_type, query)
        
    except Exception as e:
        print(f"   ❌ Error in unified content retrieval: {e}")
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return f"I encountered an error while searching for {content_type}: {str(e)}"


def _format_log_results(results: List[Dict], controller, temporal_selector: Optional[str], query: str) -> str:
    """Format log results with proper titles and LLM processing"""
    log_parts = []
    
    for result in results:
        # Use the database controller's helper to format the log title
        log_title = controller.format_log_title(result)
        content = result['raw_content']
        
        # Add temporal context to title if specified
        if temporal_selector:
            log_title += f" ({temporal_selector.title()})"
        
        log_parts.append(f"**{log_title}**\n{content}")
    
    final_content = '\n\n---\n\n'.join(log_parts)
    print(f"   [OK] Log content: {len(final_content)} characters")
    
    # Always process logs through LLM for better formatting and narrative structure
    from .llm_query_processor import get_llm_processor
    print(f"   [PROCESS] Processing logs through secondary LLM...")
    processor = get_llm_processor()
    result = processor.process_query_results('logs', final_content, query)
    print(f"   [OK] LLM processed: {len(final_content)} → {len(result.content)} chars")
    return result.content


def _format_general_results(results: List[Dict], content_type: str, query: str) -> str:
    """Format general results with category indicators and optional LLM processing"""
    # Filter out episode summaries for better results
    filtered_results = [r for r in results if not _is_episode_summary(r)]
    if len(filtered_results) < len(results):
        print(f"   🧹 Filtered out {len(results) - len(filtered_results)} episode summaries")
        results = filtered_results
    
    if not results:
        return f"I don't have any specific {content_type} information about '{query}' in my database."
    
    # Format results with category indicators
    content_parts = []
    for result in results:
        title = result['title']
        content = result['raw_content']
        categories = result.get('categories', [])
        
        # Add category indicator
        category_indicator = ""
        if categories:
            if content_type == 'ships' and any('ship' in cat.lower() for cat in categories):
                category_indicator = " [Ship Information]"
            elif content_type == 'characters' and 'Characters' in categories:
                category_indicator = " [Personnel File]"
            elif categories:
                category_indicator = f" [{categories[0]}]"
        
        content_parts.append(f"**{title}{category_indicator}**\n{content}")
    
    final_content = '\n\n---\n\n'.join(content_parts)
    print(f"   ✅ {content_type.title()} content: {len(final_content)} characters")
    
    # Process through LLM if needed
    from .llm_query_processor import should_process_data, get_llm_processor
    if should_process_data(final_content):
        print(f"   🔄 Processing content through secondary LLM...")
        processor = get_llm_processor()
        query_type = 'ships' if content_type == 'ships' else 'general'
        result = processor.process_query_results(query_type, final_content, query)
        print(f"   ✅ LLM processed: {len(final_content)} → {len(result.content)} chars")
        return result.content
    
    return final_content


def _is_episode_summary(result: dict) -> bool:
    """
    Check if a result is an episode summary that should be filtered out.
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
        
        print(f"[WEB] MEMORY ALPHA SEARCH: '{query}' (limit={limit})")
        
        # Search Memory Alpha API
        search_url = f"https://memory-alpha.fandom.com/api.php"
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
            print(f"   [ERROR] No search results found")
            return ""
        
        results = search_data['query']['search']
        if not results:
            print(f"   [ERROR] Empty search results")
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
            print(f"   [ERROR] No usable content found")
            return ""
            
    except Exception as e:
        print(f"   [ERROR] Memory Alpha search error: {e}")
        return ""


# ==============================================================================
# LEGACY COMPATIBILITY FUNCTIONS - Route to unified get_content
# ==============================================================================

def get_log_content(query: str, mission_logs_only: bool = False, ship_name: Optional[str] = None) -> str:
    """Legacy function - routes to unified get_content"""
    return get_content(query, content_type='logs', ship_name=ship_name)

def get_tell_me_about_content_prioritized(subject: str) -> str:
    """Legacy function - routes to unified get_content"""
    return get_content(subject, content_type='general')

def get_relevant_wiki_context(query: str, mission_logs_only: bool = False) -> str:
    """Legacy function - routes to unified get_content"""
    content_type = 'logs' if mission_logs_only else 'general'
    return get_content(query, content_type=content_type)

def get_ship_information(ship_name: str) -> str:
    """Legacy function - routes to unified get_content"""
    return get_content(ship_name, content_type='ships')

def get_character_context(character_name: str) -> str:
    """Legacy function - routes to unified get_content"""
    return get_content(character_name, content_type='characters')

def get_recent_logs(ship_name: Optional[str] = None, limit: int = 10) -> str:
    """Legacy function - routes to unified get_content"""
    query = f"recent logs {ship_name}" if ship_name else "recent logs"
    return get_content(query, content_type='logs', temporal_selector='latest', ship_name=ship_name)

def get_tell_me_about_content(subject: str) -> str:
    """Legacy function - routes to unified get_content"""
    return get_content(subject, content_type='general')

def get_random_log_content(ship_name: Optional[str] = None) -> str:
    """Legacy function - routes to unified get_content"""
    query = f"random log {ship_name}" if ship_name else "random log"
    return get_content(query, content_type='logs', temporal_selector='random', ship_name=ship_name)

def get_temporal_log_content(selection_type: str, ship_name: Optional[str] = None, limit: int = 5) -> str:
    """Legacy function - routes to unified get_content"""
    query = f"{selection_type} logs {ship_name}" if ship_name else f"{selection_type} logs"
    return get_content(query, content_type='logs', temporal_selector=selection_type, ship_name=ship_name)

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
        return controller.search(search_term, limit=limit)
    except Exception as e:
        print(f"❌ Error in search_titles_containing: {e}")
        return [] 