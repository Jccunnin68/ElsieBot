"""
Context Coordinator - Wisdom Layer Orchestrator
==============================================

This module coordinates between different context builders and provides
the appropriate context based on the response strategy.

ENHANCED: Supports different response modes:
- quick_single_result: For roleplay (single best match)
- comprehensive_with_disambiguation: For non-roleplay (summary + disambiguation)
"""

from typing import Any, Dict, List, Optional
import traceback


def _detect_roleplay_context(strategy: Dict[str, Any]) -> bool:
    """Detect if we're in a roleplay context for LLM processor integration"""
    approach = strategy.get('approach', '')
    
    # Direct roleplay approaches
    if approach and approach.startswith('roleplay'):
        return True
    
    # Check for roleplay indicators in strategy
    roleplay_indicators = [
        'roleplay', 'character_interaction', 'in_character', 
        'listening_mode', 'character_response'
    ]
    
    for key, value in strategy.items():
        if isinstance(value, str) and any(indicator in value.lower() for indicator in roleplay_indicators):
            return True
    
    # Check for roleplay state from state manager
    try:
        from ..ai_attention.state_manager import get_roleplay_state
        rp_state = get_roleplay_state()
        return rp_state.is_roleplaying
    except:
        pass
    
    return False

def get_context_for_strategy(strategy: Dict, user_message: str) -> str:
    """
    Enhanced context coordinator that handles different response modes.
    
    Routes to appropriate context builders based on strategy and response mode.
    
    Args:
        strategy: Strategy dictionary with approach and response mode
        user_message: Original user message
        
    Returns:
        Formatted context string appropriate for the response mode
    """
    try:
        print(f"   🧠 CONTEXT COORDINATOR - Processing strategy")
        print(f"      Approach: {strategy.get('approach', 'unknown')}")
        
        response_mode = strategy.get('response_mode', 'standard')
        print(f"      Response Mode: {response_mode}")
        
        # Route based on response mode
        if response_mode == 'quick_single_result':
            return _get_quick_single_result(strategy, user_message)
        elif response_mode == 'comprehensive_with_disambiguation':
            return _get_comprehensive_with_disambiguation(strategy, user_message)
        else:
            return _get_standard_context(strategy, user_message)
            
    except Exception as e:
        print(f"   ❌ ERROR in context coordinator: {e}")
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return f"I encountered an issue processing your request: {e}"


def _get_quick_single_result(strategy: Dict, user_message: str) -> str:
    """
    Quick response for roleplay - return single best match immediately.
    
    This maintains roleplay flow by providing immediate, relevant results
    without overwhelming the user with choices.
    """
    print(f"      🚀 QUICK SINGLE RESULT MODE")
    
    query_type = strategy.get('query_type', 'unknown')
    subject = strategy.get('subject')
    
    try:
        if query_type == 'character':
            return _get_character_quick(subject, strategy.get('valid_categories', []))
        elif query_type == 'ship':
            return _get_ship_quick(subject, strategy.get('valid_categories', []))
        elif query_type in ['ship_log', 'character_log', 'log']:
            return _get_log_quick(strategy, user_message)
        elif query_type == 'tell_me_about':
            return _get_title_search_quick(subject)
        else:
            print(f"         ⚠️  Unknown query type for quick mode: {query_type}")
            return "I need a moment to process that request."
            
    except Exception as e:
        print(f"         ❌ Error in quick single result: {e}")
        return "I'm having trouble accessing that information right now."


def _get_comprehensive_with_disambiguation(strategy: Dict, user_message: str) -> str:
    """
    Comprehensive response for non-roleplay with summary + disambiguation.
    
    This provides thorough information with options when multiple results exist.
    Uses enhanced context builders to include proper instructions.
    """
    print(f"      📚 COMPREHENSIVE WITH DISAMBIGUATION MODE")
    print(f"         🔄 Delegating to enhanced context builders for proper instructions")
    
    # Use the enhanced context builders instead of raw search functions
    # This ensures we get the proper context instructions (like 8000 character limit)
    return _get_standard_context(strategy, user_message)


def _get_standard_context(strategy: Dict, user_message: str) -> str:
    """
    Standard context handling for existing approaches.
    
    This maintains compatibility with existing context builders.
    """
    print(f"      🔄 STANDARD CONTEXT MODE")
    
    try:
        # Import context builders
        from .roleplay_context_builder import RoleplayContextBuilder
        from .non_roleplay_context_builder import NonRoleplayContextBuilder
        
        approach = strategy.get('approach', 'general')
        print(f"         🎯 CONTEXT COORDINATOR: Building context for approach '{approach}'")
        
        # Determine which context builder to use
        # Check for non-roleplay approaches first (more specific)
        if approach.startswith('non_roleplay') or approach in ['tell_me_about', 'character_info', 'logs', 'ship_info', 'federation_archives', 'ship_logs', 'url_request', 'general_with_context']:
            print(f"         📋 Using NonRoleplayContextBuilder")
            context_builder = NonRoleplayContextBuilder()
            result = context_builder.build_context_for_strategy(strategy, user_message)
        elif 'roleplay' in approach:
            print(f"         🎭 Using RoleplayContextBuilder")
            context_builder = RoleplayContextBuilder()
            result = context_builder.build_context_for_strategy(strategy, user_message)
        else:
            print(f"         📋 Using NonRoleplayContextBuilder (default)")
            context_builder = NonRoleplayContextBuilder()
            result = context_builder.build_context_for_strategy(strategy, user_message)
        
        print(f"         ✅ Context generated: {len(result)} characters")
        return result
            
    except Exception as e:
        print(f"         ❌ Error in standard context: {e}")
        return f"I need to gather information to respond to that: {e}"


def _get_character_quick(character_name: str, valid_categories: List[str]) -> str:
    """Quick character search with category intersection for roleplay."""
    try:
        from .content_retriever import search_database_content
        
        print(f"         🧑 Quick character search: {character_name}")
        print(f"         📂 Valid categories: {valid_categories}")
        
        # Search for character with category intersection
        results = search_database_content(
            search_type='character',
            search_term=character_name,
            categories=valid_categories,
            limit=1  # Only get the best match
        )
        
        if results:
            result = results[0]
            print(f"         ✅ Found character: {result['title']}")
            
            # Return full content (no truncation)
            content = result['raw_content']
            
            return f"**{result['title']}**\n\n{content}"
        else:
            print(f"         ❌ No character found: {character_name}")
            return f"I don't have information about a character named '{character_name}' in my database."
            
    except Exception as e:
        print(f"         ❌ Error in character quick search: {e}")
        return f"I'm having trouble finding information about '{character_name}'."


def _get_ship_quick(ship_name: str, valid_categories: List[str]) -> str:
    """Quick ship search with category intersection for roleplay."""
    try:
        from .content_retriever import search_database_content
        
        print(f"         🚢 Quick ship search: {ship_name}")
        print(f"         📂 Valid categories: {valid_categories}")
        
        # Search for ship with category intersection
        results = search_database_content(
            search_type='ship',
            search_term=ship_name,
            categories=valid_categories,
            limit=1  # Only get the best match
        )
        
        if results:
            result = results[0]
            print(f"         ✅ Found ship: {result['title']}")
            
            # Return full content (no truncation)
            content = result['raw_content']
            
            return f"**{result['title']}**\n\n{content}"
        else:
            print(f"         ❌ No ship found: {ship_name}")
            return f"I don't have information about a ship named '{ship_name}' in my database."
            
    except Exception as e:
        print(f"         ❌ Error in ship quick search: {e}")
        return f"I'm having trouble finding information about '{ship_name}'."


def _get_log_quick(strategy: Dict, user_message: str) -> str:
    """Quick log search for roleplay."""
    try:
        from .content_retriever import search_database_content
        
        query_type = strategy.get('query_type')
        subject = strategy.get('subject')
        log_type = strategy.get('log_type')
        
        print(f"         📋 Quick log search: {query_type} - {subject} - {log_type}")
        
        # Build search parameters
        search_params = {
            'search_type': 'logs',
            'limit': 1  # Only get the best match
        }
        
        if subject:
            search_params['search_term'] = subject
        if log_type:
            search_params['log_type'] = log_type
        
        results = search_database_content(**search_params)
        
        if results:
            result = results[0]
            print(f"         ✅ Found log: {result['title']}")
            
            # Return full content (no truncation)
            content = result['raw_content']
            
            return f"**{result['title']}**\n\n{content}"
        else:
            print(f"         ❌ No logs found for: {subject}")
            return f"I don't have any logs matching that request in my database."
            
    except Exception as e:
        print(f"         ❌ Error in log quick search: {e}")
        return f"I'm having trouble accessing log information right now."


def _get_title_search_quick(search_term: str) -> str:
    """Quick title search for roleplay."""
    try:
        from .content_retriever import search_titles_containing
        
        print(f"         📖 Quick title search: {search_term}")
        
        results = search_titles_containing(search_term, limit=1)
        
        if results:
            result = results[0]
            print(f"         ✅ Found title: {result['title']}")
            
            # Return full content (no truncation)
            content = result['raw_content']
            
            return f"**{result['title']}**\n\n{content}"
        else:
            print(f"         ❌ No titles found for: {search_term}")
            return f"I don't have information about '{search_term}' in my database."
            
    except Exception as e:
        print(f"         ❌ Error in title quick search: {e}")
        return f"I'm having trouble finding information about '{search_term}'."


def _get_title_search_comprehensive(search_term: str) -> str:
    """Comprehensive title search with summary + disambiguation for non-roleplay."""
    try:
        from .content_retriever import search_titles_containing
        
        print(f"         📚 Comprehensive title search: {search_term}")
        
        results = search_titles_containing(search_term, limit=10)
        
        if not results:
            return f"I don't have information about '{search_term}' in my database."
        
        if len(results) == 1:
            # Single result - return with summary
            result = results[0]
            print(f"         ✅ Single result: {result['title']}")
            return _format_single_result_with_summary(result)
        else:
            # Multiple results - return summary + disambiguation
            print(f"         📋 Multiple results: {len(results)} found")
            return _format_disambiguation_with_summary(search_term, results)
            
    except Exception as e:
        print(f"         ❌ Error in comprehensive title search: {e}")
        return f"I encountered an issue searching for '{search_term}': {e}"


def _get_character_comprehensive(character_name: str, valid_categories: List[str]) -> str:
    """Comprehensive character search with disambiguation for non-roleplay."""
    try:
        from .content_retriever import search_database_content
        
        print(f"         🧑 Comprehensive character search: {character_name}")
        
        results = search_database_content(
            search_type='character',
            search_term=character_name,
            categories=valid_categories,
            limit=5
        )
        
        if not results:
            return f"I don't have information about a character named '{character_name}' in my database."
        
        if len(results) == 1:
            return _format_single_result_with_summary(results[0])
        else:
            return _format_disambiguation_with_summary(character_name, results)
            
    except Exception as e:
        print(f"         ❌ Error in comprehensive character search: {e}")
        return f"I'm having trouble finding information about '{character_name}': {e}"


def _get_ship_comprehensive(ship_name: str, valid_categories: List[str]) -> str:
    """Comprehensive ship search with disambiguation for non-roleplay."""
    try:
        from .content_retriever import search_database_content
        
        print(f"         🚢 Comprehensive ship search: {ship_name}")
        
        results = search_database_content(
            search_type='ship',
            search_term=ship_name,
            categories=valid_categories,
            limit=5
        )
        
        if not results:
            return f"I don't have information about a ship named '{ship_name}' in my database."
        
        if len(results) == 1:
            return _format_single_result_with_summary(results[0])
        else:
            return _format_disambiguation_with_summary(ship_name, results)
            
    except Exception as e:
        print(f"         ❌ Error in comprehensive ship search: {e}")
        return f"I'm having trouble finding information about '{ship_name}': {e}"


def _get_log_comprehensive(strategy: Dict, user_message: str) -> str:
    """Comprehensive log search with disambiguation for non-roleplay."""
    try:
        from .content_retriever import search_database_content
        
        query_type = strategy.get('query_type')
        subject = strategy.get('subject')
        log_type = strategy.get('log_type')
        
        print(f"         📋 Comprehensive log search: {query_type} - {subject}")
        
        # Build search parameters
        search_params = {
            'search_type': 'logs',
            'limit': 5
        }
        
        if subject:
            search_params['search_term'] = subject
        if log_type:
            search_params['log_type'] = log_type
        
        results = search_database_content(**search_params)
        
        if not results:
            return f"I don't have any logs matching that request in my database."
        
        if len(results) == 1:
            return _format_single_result_with_summary(results[0])
        else:
            return _format_disambiguation_with_summary(subject or 'logs', results)
            
    except Exception as e:
        print(f"         ❌ Error in comprehensive log search: {e}")
        return f"I'm having trouble accessing log information: {e}"


def _format_single_result_with_summary(result: Dict) -> str:
    """Format single result with full content for comprehensive responses."""
    try:
        title = result['title']
        content = result['raw_content']  # RETURN FULL CONTENT, NO TRUNCATION
        
        return f"**{title}**\n\n{content}"
        
    except Exception as e:
        print(f"         ❌ Error formatting single result: {e}")
        return f"Found information but couldn't format it properly: {e}"


def _format_disambiguation_with_summary(search_term: str, results: List[Dict]) -> str:
    """Format disambiguation response with full content from first result."""
    try:
        if not results:
            return f"No results found for '{search_term}'."
        
        # Return FULL content from first result instead of truncated summary
        first_result = results[0]
        title = first_result['title']
        content = first_result['raw_content']  # FULL CONTENT, NO TRUNCATION
        
        # If there's only one result, just return the full content
        if len(results) == 1:
            return f"**{title}**\n\n{content}"
        
        # For multiple results, return full first result + list of other options
        summary = f"**{title}**\n\n{content}\n\n"
        
        # Build disambiguation list for additional results
        if len(results) > 1:
            disambiguation = f"I also found these related entries:\n\n"
            for i, result in enumerate(results[1:6], 2):  # Skip first result, show next 5
                snippet = result['raw_content'][:100]
                if len(result['raw_content']) > 100:
                    snippet += "..."
                disambiguation += f"{i}. **{result['title']}** - {snippet}\n"
            
            return summary + disambiguation + "\nWould you like to know about any of the other entries?"
        else:
            return summary
        
    except Exception as e:
        print(f"         ❌ Error formatting disambiguation: {e}")
        return f"Found multiple results for '{search_term}' but couldn't format them properly: {e}"


# _get_roleplay_listening_context removed - now handled in roleplay_handler.py 