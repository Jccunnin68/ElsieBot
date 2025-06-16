"""Database-driven content retrieval and wiki search functionality"""

from database_controller import get_db_controller
from typing import Optional, List, Dict
import requests
from urllib.parse import quote
import re
from .log_patterns import (
    CHARACTER_CORRECTIONS, 
    resolve_character_name_with_context
)
from .llm_query_processor import get_llm_processor, should_process_data, is_fallback_response

def determine_query_type(function_name: str, content_type: str = None) -> str:
    """Map function types to LLM processor query types"""
    if 'log' in function_name.lower():
        return "logs"
    elif content_type == 'personnel' or 'character' in str(content_type or ''):
        return "character" 
    else:
        return "general"

def create_query_description(function_name: str, **kwargs) -> str:
    """Generate descriptive query for LLM processing context"""
    descriptions = {
        'get_ship_information': f"ship information for {kwargs.get('ship_name', 'unknown ship')}",
        'get_recent_logs': f"recent logs" + (f" for {kwargs.get('ship_name')}" if kwargs.get('ship_name') else ""),   
        'get_tell_me_about_content': f"information about {kwargs.get('subject', 'unknown subject')}",
        'search_memory_alpha': f"external wiki information about '{kwargs.get('query', '')}'",
        'get_random_log_content': f"random log" + (f" from {kwargs.get('ship_name')}" if kwargs.get('ship_name') else "")
    }
    return descriptions.get(function_name, "database query results")

def _get_roleplay_context_from_caller() -> bool:
    """
    Detect if we're in roleplay context by examining the call stack.
    This avoids threading roleplay parameters through all content functions.
    Enhanced to check for explicit roleplay parameters.
    """
    import inspect
    
    try:
        # Check call stack for roleplay indicators
        frame = inspect.currentframe()
        max_depth = 50  # Safety guard to prevent infinite loops in rare cases
        depth = 0
        while frame and depth < max_depth:
            frame_info = inspect.getframeinfo(frame)
            filename = frame_info.filename
            
            # Look for ai_wisdom_handler.py or context_coordinator.py in call stack
            if any(handler in filename for handler in ['ai_wisdom_handler.py', 'context_coordinator.py', 'non_roleplay_context_builder.py']):
                # Check if the calling function has roleplay context
                local_vars = frame.f_locals
                if 'is_roleplay' in local_vars:
                    return local_vars['is_roleplay']
                # Also check for other roleplay indicators
                if 'roleplay' in str(local_vars.get('context', '')).lower():
                    return True
                break
            frame = frame.f_back
            depth += 1
        if depth >= max_depth:
            print("⚠️  Stack inspection aborted after reaching max depth to prevent infinite loop")
    except Exception:
        # If anything goes wrong with call stack inspection, default to False
        pass
    finally:
        # Clean up frame reference to prevent memory leaks
        if 'frame' in locals():
            del frame
    
    # Also check roleplay state manager as fallback
    try:
        from ..ai_attention.state_manager import get_roleplay_state
        rp_state = get_roleplay_state()
        return rp_state.is_roleplaying
    except:
        pass
    
    return False  # Default to non-roleplay

def is_episode_summary(result: dict) -> bool:
    """
    Check if a database result is an episode summary that should be filtered out.
    
    Args:
        result: Database result dictionary with 'categories' key
        
    Returns:
        True if this is an episode summary, False otherwise
    """
    categories = result.get('categories', [])
    if not categories:
        return False
    
    # Check for episode summary pattern in any category
    for cat in categories:
        if 'episode summary' in cat.lower():
            return True
    
    return False

# REMOVED: is_ship_log_title() function - replaced with category-based search
# The complex ship log detection logic has been removed in favor of using 
# real MediaWiki categories. Log detection is now handled by:
# - controller.search_logs() which uses _get_actual_log_categories_from_db()
# - Category filtering: WHERE categories && log_categories
# This eliminates ~80 lines of complex regex patterns and hardcoded ship names.




def correct_character_name(name: str, ship_context: Optional[str] = None, 
                          surrounding_text: str = "") -> str:
    """Apply character corrections and rank/title fixes with ship context awareness"""
    if not name:
        return name
    
    # Use new context-aware resolution system
    return resolve_character_name_with_context(name, ship_context, surrounding_text)

def apply_text_corrections(text: str, ship_context: Optional[str] = None) -> str:
    """Apply character name corrections to free text with ship context"""
    corrected_text = text
    
    # Use the new resolution system for each character reference
    from .log_patterns import FALLBACK_CHARACTER_CORRECTIONS, SHIP_SPECIFIC_CHARACTER_CORRECTIONS
    
    # Get all possible character names to replace
    all_corrections = FALLBACK_CHARACTER_CORRECTIONS.copy()
    if ship_context and ship_context.lower() in SHIP_SPECIFIC_CHARACTER_CORRECTIONS:
        all_corrections.update(SHIP_SPECIFIC_CHARACTER_CORRECTIONS[ship_context.lower()])
    
    # Replace character references in text using context-aware resolution
    for incorrect, correct in all_corrections.items():
        # Case-insensitive replacement while preserving case
        pattern = re.compile(re.escape(incorrect), re.IGNORECASE)
        
        def replacement_func(match):
            matched_text = match.group(0)
            # Use context-aware resolution instead of simple mapping
            resolved = resolve_character_name_with_context(matched_text, ship_context, text)
            return resolved
        
        corrected_text = pattern.sub(replacement_func, corrected_text)
    
    return corrected_text

def is_doic_channel_content(content: str) -> bool:
    """
    Detect if content is from a [DOIC] channel.
    DOIC content is primarily narration or other character dialogue,
    rarely from the character@account_name speaking.
    """
    # Check for [DOIC] channel indicators
    doic_patterns = [
        r'\[DOIC\]',  # Direct [DOIC] tag
        r'@DOIC',     # @DOIC mentions
        r'DOIC:',     # DOIC: prefix
    ]
    
    for pattern in doic_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    return False

def parse_doic_content(content: str, ship_name: Optional[str] = None) -> str:
    """
    Parse DOIC channel content with special rules:
    - Primarily narration or other character dialogue
    - Rarely from character@account_name speaking
    - Treat as environmental/narrative description
    """
    if not content:
        return content
    
    print(f"   📺 DOIC channel content detected - applying special parsing rules")
    
    lines = content.split('\n')
    processed_lines = []
    
    for line in lines:
        # Remove [DOIC] tags but preserve content
        line = re.sub(r'\[DOIC\]\s*', '', line, flags=re.IGNORECASE)
        
        # Check for character@account patterns in DOIC content
        speaker_pattern = r'^([^@\s]+)@([^:\s]+):\s*(.*)$'
        speaker_match = re.match(speaker_pattern, line.strip())
        
        if speaker_match:
            character_name = speaker_match.group(1)
            account_name = speaker_match.group(2)
            content_part = speaker_match.group(3)
            
            # In DOIC, this is usually narration about the character, not the character speaking
            # Format as narrative description
            if content_part.strip():
                processed_lines.append(f"*{character_name}: {content_part}*")
            else:
                processed_lines.append(f"*{character_name} is present*")
        else:
            # Regular DOIC content - treat as narration
            if line.strip():
                # If not already in narrative format, make it narrative
                if not (line.strip().startswith('*') and line.strip().endswith('*')):
                    processed_lines.append(f"*{line.strip()}*")
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def should_skip_local_character_processing(content: str) -> bool:
    """
    Determine if we should skip local character processing because
    the content will be processed by the secondary LLM processor.
    """
    # If content will go to secondary LLM, skip local processing
    # The secondary LLM will handle character disambiguation
    return should_process_data(content)

def parse_log_characters(log_content: str, ship_name: Optional[str] = None, 
                        log_title: str = "") -> str:
    """Parse log content - simplified to remove local character processing.
    
    All character processing is now handled by the secondary LLM to prevent duplication.
    This function only handles basic DOIC detection for routing purposes.
    
    Enhanced to handle new gamemaster format with ship-context aware character resolution:
    - characterName@AccountName: [Actual Character] - Extract actual character from brackets
    - If no [Actual Character], use characterName before @
    - Things with * or in ** ** are actions, not dialogue
    - Lines ending with > > or continuation from same character@account are follow ups with dialogue having \"
    - DOIC channel content gets special handling as narration
    - ALL CHARACTER PROCESSING NOW HANDLED BY SECONDARY LLM
    """
    
    # Check if this content will be processed by secondary LLM
    # (All log content now goes to secondary LLM regardless of size)
    print(f"   🔄 Log content will be processed by secondary LLM - skipping local character processing")
    
    # Only handle DOIC detection for routing, no character processing
    if is_doic_channel_content(log_content):
        # Mark as DOIC but don't process locally - LLM will handle it
        print(f"   📺 DOIC channel content detected - will be processed by secondary LLM")
        return f"[DOIC_CONTENT]\n{log_content}"
    
    # Return content unchanged - secondary LLM will handle all character processing
    return log_content

def format_content_type(content: str, is_emote: bool = False) -> str:
    """
    Format content to distinguish between actions and dialogue.
    
    Rules:
    - Content starting with * or in ** ** brackets are actions
    - Everything else is dialogue
    - Emotes are formatted as actions
    """
    if not content.strip():
        return content
    
    content = content.strip()
    
    # Check if it's already in action format (starts with * or wrapped in **)
    if content.startswith('*') or (content.startswith('**') and content.endswith('**')):
        return f"*{content.strip('*').strip()}*"  # Normalize to single asterisks
    
    # Check if it's an emote
    if is_emote:
        return f"*{content}*"
    
    # Check for common action verbs and patterns
    action_patterns = [
        r'^(walks?|runs?|sits?|stands?|looks?|turns?|moves?|enters?|exits?|approaches?)',
        r'^(nods?|smiles?|frowns?|laughs?|sighs?|shrugs?)',
        r'^(grabs?|picks? up|puts? down|places?|holds?|drops?)',
        r'^(points?|gestures?|waves?|raises?|lowers?)',
        r'^\*.*\*$',  # Already wrapped in asterisks
        r'^.*\btaps?\b.*',
        r'^.*\bpresses?\b.*',
        r'^.*\bactivates?\b.*'
    ]
    
    # Check if content matches action patterns
    for pattern in action_patterns:
        if re.match(pattern, content.lower()):
            # Don't double-wrap if already wrapped
            if content.startswith('*') and content.endswith('*'):
                return content
            return f"*{content}*"
    
    # Check for action indicators within the content
    if any(indicator in content.lower() for indicator in ['*action*', '*emote*', '*does*', '*performs*']):
        return f"*{content}*"
    
    # Otherwise, treat as dialogue
    return content

def search_memory_alpha(query: str, limit: int = 3, is_federation_archives: bool = False) -> str:
    """
    Search multiple Star Trek wikis using MediaWiki API as fallback when local database has no results.
    Returns formatted content from wiki articles.
    
    Args:
        query: Search query
        limit: Number of results to return per wiki
        is_federation_archives: If True, adds [Federation Archives] tags for explicit federation archives requests
    """
    try:
        print(f"🌟 WIKI SEARCH: '{query}' (fallback search)")
        
        # Clean up the query for better search results
        search_query = query.strip()
        
        # Get wiki endpoints from config
        from config import WIKI_ENDPOINTS
        all_content = []
        
        for base_url in WIKI_ENDPOINTS:
            wiki_name = base_url.split('/')[-2]  # Extract wiki name from URL
            print(f"   🔍 Searching {wiki_name}...")
            
            # First, search for articles
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': search_query,
                'srlimit': limit,
                'srnamespace': 0,  # Main namespace only
                'srprop': 'snippet|titlesnippet'
            }
            
            search_response = requests.get(base_url, params=search_params, timeout=10)
            search_data = search_response.json()
            
            if 'query' not in search_data or 'search' not in search_data['query']:
                print(f"   ❌ No {wiki_name} search results found")
                continue
            
            search_results = search_data['query']['search']
            if not search_results:
                print(f"   ❌ No {wiki_name} articles found for '{query}'")
                continue
            
            print(f"   📊 Found {len(search_results)} {wiki_name} articles")
            
            # Get content for the top results
            wiki_content = []
            page_titles = [result['title'] for result in search_results[:limit]]
            
            # Get page content
            content_params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(page_titles),
                'prop': 'extracts',
                'exintro': True,  # Only get intro section
                'explaintext': True,  # Plain text, no HTML
                'exsectionformat': 'plain'
            }
            
            content_response = requests.get(base_url, params=content_params, timeout=10)
            content_data = content_response.json()
            
            if 'query' not in content_data or 'pages' not in content_data['query']:
                print(f"   ❌ Could not retrieve {wiki_name} content")
                continue
            
            pages = content_data['query']['pages']
            
            for page_id, page_data in pages.items():
                if page_id == '-1':  # Page not found
                    continue
                    
                title = page_data.get('title', 'Unknown Title')
                extract = page_data.get('extract', '')
                
                if extract:
                    # Format for Elsie's response
                    page_url = f"{base_url.rsplit('/', 1)[0]}/wiki/{quote(title.replace(' ', '_'))}"
                    if is_federation_archives:
                        formatted_content = f"**{title}** [{wiki_name} - Federation Archives]\n{extract}"
                    else:
                        formatted_content = f"**{title}** [{wiki_name}]\n{extract}"
                    wiki_content.append(formatted_content)
                    print(f"   ✓ Retrieved {wiki_name} article: '{title}' ({len(extract)} chars)")
            
            if wiki_content:
                all_content.extend(wiki_content)
        
        if not all_content:
            print(f"   ❌ No usable wiki content found")
            return ""
        
        # Join all content with appropriate separators
        if is_federation_archives:
            final_content = '\n\n---FEDERATION ARCHIVES---\n\n'.join(all_content)
        else:
            final_content = '\n\n---\n\n'.join(all_content)
            
        print(f"✅ WIKI SEARCH COMPLETE: {len(final_content)} characters from {len(all_content)} articles")
        
        # Process large content through LLM if needed
        if should_process_data(final_content):
            print(f"🔄 Content size ({len(final_content)} chars) exceeds threshold, processing with LLM...")
            processor = get_llm_processor()
            query_type = determine_query_type('search_memory_alpha')
            query_description = create_query_description('search_memory_alpha', query=query)
            is_roleplay = _get_roleplay_context_from_caller()
            result = processor.process_query_results(query_type, final_content, query_description, is_roleplay)
            return result.content
        
        return final_content
        
    except requests.RequestException as e:
        print(f"   ❌ Wiki API request failed: {e}")
        return ""
    except Exception as e:
        print(f"   ❌ Wiki search error: {e}")
        return ""

def check_elsiebrain_connection() -> bool:
    """Check if the elsiebrain database is accessible and populated"""
    try:
        controller = get_db_controller()
        stats = controller.get_stats()
        
        if stats and stats.get('total_pages', 0) > 0:
            print(f"✓ elsiebrain database ready")
        else:
            print("⚠️  elsiebrain database is connected but empty - needs to be populated externally")
        
        return True
        
    except Exception as e:
        print(f"✗ Error connecting to elsiebrain database: {e}")
        print("   Make sure the elsiebrain database exists and is populated")
        return False



def get_log_content(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    """Simplified log search using categories - NO TRUNCATION
    Uses new Phase 1 category-based database controller methods
    
    Args:
        query: Search query
        mission_logs_only: If True, only search log categories (same behavior as before)
        is_roleplay: If True, use roleplay-appropriate fallback responses when processing fails
    """
    try:
        controller = get_db_controller()
        print(f"🔍 CATEGORY-BASED LOG SEARCH: '{query}' (mission_logs_only={mission_logs_only}, roleplay={is_roleplay})")
        
        # Check for log selection queries first (keep existing special handling)
        from ..ai_logic.query_detection import detect_log_selection_query
        is_selection, selection_type, ship_name = detect_log_selection_query(query)
        
        if is_selection:
            print(f"   🎯 LOG SELECTION DETECTED: type='{selection_type}', ship='{ship_name}'")
            
            if selection_type == 'random':
                return get_random_log_content(ship_name, is_roleplay)
            elif selection_type in ['latest', 'recent']:
                limit = 1 if selection_type == 'latest' else 5
                return get_temporal_log_content(selection_type, ship_name, limit=limit, is_roleplay=is_roleplay)
            elif selection_type in ['first', 'earliest', 'oldest']:
                limit = 1 if selection_type == 'first' else 5
                return get_temporal_log_content(selection_type, ship_name, limit=limit, is_roleplay=is_roleplay)
            elif selection_type in ['today', 'yesterday', 'this_week', 'last_week']:
                return get_temporal_log_content(selection_type, ship_name, limit=10, is_roleplay=is_roleplay)
        
        # Extract ship name for ship-specific log searches
        ship_name_from_query = None
        # Simple ship name extraction from query (could be enhanced)
        ship_keywords = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta']
        for ship in ship_keywords:
            if ship in query.lower():
                ship_name_from_query = ship
                break
        
        # Use new Phase 1 search_logs method - MUCH SIMPLER!
        results = controller.search_logs(query, ship_name=ship_name_from_query, limit=20)
        print(f"   📊 Category-based log search returned {len(results)} results")
        
        if not results:
            print(f"✗ No log content found for query: '{query}'")
            return ""
        
        # Process results - keep existing processing logic
        log_contents = []
        for result in results:
            title = result['title']
            content = result['raw_content']
            print(f"   📄 Processing: '{title}' ({len(content)} chars)")
            
            # Parse character speaking patterns in the log
            parsed_content = parse_log_characters(content, result.get('ship_name'), title)
            
            # Format the log with title and parsed content
            formatted_log = f"**{title}**\n{parsed_content}"
            log_contents.append(formatted_log)
            print(f"   ✓ Added: {title}")
        
        final_content = '\n\n---LOG SEPARATOR---\n\n'.join(log_contents)
        print(f"✅ CATEGORY-BASED LOG SEARCH COMPLETE: {len(final_content)} characters from {len(log_contents)} logs")
        
        # Process log content through secondary LLM
        print(f"🔄 Log content ({len(final_content)} chars) - routing to secondary LLM for character processing")
        processor = get_llm_processor()
        result = processor.process_query_results("logs", final_content, query, is_roleplay, force_processing=True)
        return result.content
        
    except Exception as e:
        print(f"✗ Error getting log content: {e}")
        return ""

def get_relevant_wiki_context(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    """Simplified unified search strategy using categories - NO TRUNCATION
    Uses intelligent query type detection and category-based searches
    
    Args:
        query: Search query
        mission_logs_only: If True, only search log categories when detecting log queries
        is_roleplay: If True, use roleplay-appropriate fallback responses when processing fails
    """
    try:
        controller = get_db_controller()
        print(f"🔍 UNIFIED CATEGORY-BASED SEARCH: '{query}' (mission_logs_only={mission_logs_only}, roleplay={is_roleplay})")
        
        # Simple query type detection - category-based routing
        query_lower = query.lower()
        
        if mission_logs_only or any(indicator in query_lower for indicator in ['log', 'mission', 'stardate', 'what happened']):
            print(f"   🚀 LOG QUERY DETECTED - routing to category-based log search")
            return get_log_content(query, mission_logs_only, is_roleplay)
        
        elif any(indicator in query_lower for indicator in ['who is', 'tell me about', 'character', 'person', 'crew']):
            print(f"   👤 CHARACTER QUERY DETECTED - routing to category-based character search")
            # Extract potential character name from query (simple approach)
            character_name = query.replace('who is', '').replace('tell me about', '').strip()
            return get_character_context(character_name)
        
        elif any(indicator in query_lower for indicator in ['uss', 'ship', 'vessel', 'starship', 'specs', 'class']):
            print(f"   🚢 SHIP QUERY DETECTED - routing to category-based ship search")
            # Extract potential ship name from query (simple approach)
            ship_name = query.replace('uss', '').replace('ship', '').strip()
            return get_ship_information(ship_name)
        
        else:
            print(f"   🔍 GENERAL QUERY - using standard search")
            # General search - use existing logic
            results = controller.search_pages(query, limit=20)
            if not results:
                print(f"✗ No wiki content found for query: {query}")
                return ""
            
            print(f"   📊 General search returned {len(results)} results")
            
            context_parts = []
            for result in results:
                title = result['title']
                content = result['raw_content']
                page_text = f"**{title}**\n{content}"
                context_parts.append(page_text)
            
            final_context = '\n\n---\n\n'.join(context_parts)
            print(f"✅ UNIFIED SEARCH COMPLETE: {len(final_context)} characters from {len(context_parts)} pages")
            
            # Process large content through LLM if needed
            if should_process_data(final_context):
                print(f"🔄 Content size ({len(final_context)} chars) exceeds threshold, processing with LLM...")
                processor = get_llm_processor()
                result = processor.process_query_results("general", final_context, query, is_roleplay)
                return result.content
            
            return final_context
        
    except Exception as e:
        print(f"✗ Error getting wiki context: {e}")
        return ""

def get_ship_information(ship_name: str) -> str:
    """Simplified ship search using categories - uses Phase 1 category-based methods"""
    try:
        controller = get_db_controller()
        print(f"🚢 CATEGORY-BASED SHIP SEARCH: '{ship_name}'")
        
        # Use new Phase 1 search_ships method - MUCH SIMPLER!
        results = controller.search_ships(ship_name, limit=2)  # Focus on most relevant results
        print(f"   📊 Category-based ship search returned {len(results)} results")
        
        if not results:
            print(f"✗ No ship information found for: {ship_name}")
            return ""
        
        ship_info = []
        for result in results:
            title = result['title']
            content = result['raw_content']
            print(f"   📄 Processing: '{title}' ({len(content)} chars)")
            
            page_text = f"**{title}**\n{content}"
            ship_info.append(page_text)

        final_content = '\n\n---\n\n'.join(ship_info)
        print(f"✅ CATEGORY-BASED SHIP SEARCH COMPLETE: {len(final_content)} characters from {len(ship_info)} pages")
        
        # Process large content through LLM if needed (>14,000 chars)
        if should_process_data(final_content):
            print(f"🔄 Content size ({len(final_content)} chars) exceeds threshold, processing with LLM...")
            processor = get_llm_processor()
            query_type = determine_query_type('get_ship_information')
            query_description = create_query_description('get_ship_information', ship_name=ship_name)
            is_roleplay = _get_roleplay_context_from_caller()
            result = processor.process_query_results(query_type, final_content, query_description, is_roleplay)
            return result.content
        
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting ship information: {e}")
        return ""

def get_character_context(character_name: str) -> str:
    """NEW: Simplified character search using categories - uses Phase 1 category-based methods"""
    try:
        controller = get_db_controller()
        print(f"👤 CATEGORY-BASED CHARACTER SEARCH: '{character_name}'")
        
        # Use new Phase 1 search_characters method
        results = controller.search_characters(character_name, limit=10)
        print(f"   📊 Category-based character search returned {len(results)} results")
        
        if not results:
            print(f"✗ No character information found for: {character_name}")
            return ""
        
        character_info = []
        for result in results:
            title = result['title']
            content = result['raw_content']
            print(f"   📄 Processing: '{title}' ({len(content)} chars)")
            
            page_text = f"**{title}**\n{content}"
            character_info.append(page_text)
        
        final_content = '\n\n---\n\n'.join(character_info)
        print(f"✅ CATEGORY-BASED CHARACTER SEARCH COMPLETE: {len(final_content)} characters from {len(character_info)} pages")
        
        # Process through LLM if needed
        if should_process_data(final_content):
            print(f"🔄 Content size ({len(final_content)} chars) exceeds threshold, processing with LLM...")
            processor = get_llm_processor()
            result = processor.process_query_results("character", final_content, f"character information for {character_name}", _get_roleplay_context_from_caller())
            return result.content
        
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting character context: {e}")
        return ""

def get_recent_logs(ship_name: Optional[str] = None, limit: int = 10) -> str:
    """Get recent mission logs"""
    try:
        controller = get_db_controller()
        results = controller.get_recent_logs(ship_name=ship_name, limit=limit)
        
        if not results:
            return ""
        
        log_summaries = []

        for result in results:
            # Filter out episode summaries
            if is_episode_summary(result):
                categories = result.get('categories', [])
                episode_cat = next((cat for cat in categories if 'episode summary' in cat.lower()), 'Episode Summary')
                print(f"   ❌ Filtering out episode summary from recent logs: '{result['title']}' Category='{episode_cat}'")
                continue
            
            title = result['title']
            content = result['raw_content']
            log_date = result['log_date']

            log_entry = f"**{title}** ({log_date})\n{content}"
            log_summaries.append(log_entry)

        final_content = '\n\n---\n\n'.join(log_summaries)
        
        # Process large content through LLM if needed
        if should_process_data(final_content):
            print(f"🔄 Content size ({len(final_content)} chars) exceeds threshold, processing with LLM...")
            processor = get_llm_processor()
            query_type = determine_query_type('get_recent_logs')
            query_description = create_query_description('get_recent_logs', ship_name=ship_name)
            is_roleplay = _get_roleplay_context_from_caller()
            result = processor.process_query_results(query_type, final_content, query_description, is_roleplay)
            return result.content
        
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting recent logs: {e}")
        return ""



def get_tell_me_about_content(subject: str) -> str:
    """Enhanced 'tell me about' functionality using hierarchical search"""
    try:
        controller = get_db_controller()
        print(f"🔍 HIERARCHICAL 'TELL ME ABOUT' SEARCH: '{subject}'")
        
        # Use hierarchical search - will search titles first, then content
        results = controller.search_pages(subject, limit=15)  # Increased limit
        print(f"   📊 Hierarchical search returned {len(results)} results")
        
        # If it looks like a ship name, also search ship-specific content
        if any(ship in subject.lower() for ship in ['uss', 'ship', 'vessel']):
            print(f"   🚢 Ship detected, searching ship-specific content...")
            # Search using actual database categories instead of artificial mappings
            ship_results = controller.search_pages(subject, limit=10)
            print(f"   📊 Ship-specific search returned {len(ship_results)} results")
            
            # Merge ship results with general results, prioritizing ship info
            existing_ids = {r['id'] for r in results}
            ship_results = [r for r in ship_results if r['id'] not in existing_ids]
            results = ship_results + results
        
        if not results:
            print(f"✗ No content found for 'tell me about' query: '{subject}'")
            return ""
        
        # Format the results
        content_parts = []

        for result in results:  # Include ALL results
            title = result['title']
            content = result['raw_content']
            categories = result.get('categories', [])
            
            # Add category indicator for clarity
            category_indicator = ""
            if categories:
                # Determine primary category type using dynamic category detection
                if any('log' in cat.lower() for cat in categories):
                    category_indicator = " [Mission Log]"
                elif 'Ship Information' in categories:
                    category_indicator = " [Ship Information]"
                elif 'Characters' in categories:
                    category_indicator = " [Personnel File]"
                elif categories:
                    category_indicator = f" [{categories[0]}]"
            
            page_text = f"**{title}{category_indicator}**\n{content}"
            content_parts.append(page_text)
        
        final_content = '\n\n---\n\n'.join(content_parts)
        print(f"✅ HIERARCHICAL 'TELL ME ABOUT' COMPLETE: {len(final_content)} characters from {len(content_parts)} sources")
        
        # Process large content through LLM if needed
        if should_process_data(final_content):
            print(f"🔄 Content size ({len(final_content)} chars) exceeds threshold, processing with LLM...")
            processor = get_llm_processor()
            query_type = determine_query_type('get_tell_me_about_content')
            query_description = create_query_description('get_tell_me_about_content', subject=subject)
            is_roleplay = _get_roleplay_context_from_caller()
            result = processor.process_query_results(query_type, final_content, query_description, is_roleplay)
            return result.content
        
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting 'tell me about' content: {e}")
        return ""

def get_tell_me_about_content_prioritized(subject: str, is_roleplay: bool = False) -> str:
    """Enhanced 'tell me about' functionality that prioritizes ship info and personnel over logs - NO TRUNCATION"""
    try:
        controller = get_db_controller()
        print(f"🔍 PRIORITIZED 'TELL ME ABOUT' SEARCH: '{subject}' (roleplay={is_roleplay})")
        
        # Step 1: Search for ship info specifically first
        ship_info_results = []
        if any(indicator in subject.lower() for indicator in ['uss', 'ship', 'stardancer', 'adagio', 'pilgrim', 'voyager', 'enterprise']):
            print(f"   🚢 PRIORITY: Searching ship info pages first...")
            # Search using actual database categories instead of artificial mappings
            ship_info_results = controller.search_pages(subject, limit=10)
            print(f"   📊 Ship info search found {len(ship_info_results)} results")
        
        # Step 2: Search for personnel records
        personnel_results = []
        if any(indicator in subject.lower() for indicator in ['captain', 'commander', 'lieutenant', 'ensign', 'admiral', 'officer']):
            print(f"   👥 PRIORITY: Searching personnel records...")
            # Search using actual database categories instead of artificial mappings
            personnel_results = controller.search_pages(subject, limit=10)
            print(f"   📊 Personnel search found {len(personnel_results)} results")
        
        # Step 3: If we have ship info or personnel, use those first
        priority_results = ship_info_results + personnel_results
        
        # Step 4: Only search general content if no specific ship/personnel info found
        general_results = []
        if not priority_results:
            print(f"   📝 No ship/personnel info found, searching general content...")
            general_results = controller.search_pages(subject, limit=15)  # Increased limit
            print(f"   📊 General search found {len(general_results)} results")
        
        # Combine results, prioritizing ship info and personnel
        all_results = priority_results + general_results
        
        # Remove duplicates
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result['id'] not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result['id'])
        
        if not unique_results:
            print(f"✗ No content found for prioritized 'tell me about' query: '{subject}'")
            return ""
        
        # Format the results, excluding mission logs unless specifically requested
        content_parts = []

        for result in unique_results:  # Include ALL unique results
            title = result['title']
            content = result['raw_content']  # NO LENGTH LIMIT
            categories = result.get('categories', [])
            
            # Skip mission logs unless no other content was found
            is_mission_log = any('log' in cat.lower() for cat in categories) if categories else False
            if is_mission_log and priority_results:
                print(f"   ⏭️  Skipping mission log '{title}' (ship/personnel info available)")
                continue
            
            # Add category indicator for clarity
            category_indicator = ""
            if categories:
                if is_mission_log:
                    category_indicator = " [Mission Log]"
                elif 'Ship Information' in categories:
                    category_indicator = " [Ship Information]"
                elif 'Characters' in categories:
                    category_indicator = " [Personnel File]"
                elif categories:
                    category_indicator = f" [{categories[0]}]"
            
            page_text = f"**{title}{category_indicator}**\n{content}"
            content_parts.append(page_text)
            print(f"   ✓ Added {categories[0] if categories else 'unknown'}: '{title}'")
        
        final_content = '\n\n---\n\n'.join(content_parts)
        print(f"✅ PRIORITIZED 'TELL ME ABOUT' COMPLETE: {len(final_content)} characters from {len(content_parts)} sources")
        
        # NEW: Process large content through LLM if needed
        if should_process_data(final_content):
            print(f"🔄 Content size ({len(final_content)} chars) exceeds threshold, processing with LLM...")
            processor = get_llm_processor()
            result = processor.process_query_results("character", final_content, subject, is_roleplay)
            return result.content
        
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting prioritized 'tell me about' content: {e}")
        return ""





def get_log_url(search_query: str) -> str:
    """Get the URL for a page based on search query (ship name, title, date, etc.) - searches all page types"""
    try:
        controller = get_db_controller()
        print(f"🔗 SEARCHING FOR PAGE URL: '{search_query}'")
        
        # Try different search strategies in priority order
        best_result = None
        best_strategy = None
        
        # Strategy 1: Check if it's a "last [ship]" request - search recent mission logs
        if search_query.lower().startswith('last '):
            ship_name = search_query[5:].strip().lower()
            print(f"   📋 Strategy 1: Last mission log for ship '{ship_name}'")
            results = controller.get_recent_logs(ship_name=ship_name, limit=3)
            if results:
                # Find the first result that has a URL and is actually a mission log
                for result in results:
                    categories = result.get('categories', [])
                    if result.get('url') and any('log' in cat.lower() for cat in categories):
                        best_result = result
                        best_strategy = f"most recent mission log for {ship_name}"
                        print(f"   ✓ Found mission log with URL: '{result.get('title')}'")
                        break
                print(f"   📊 Found {len(results)} recent logs, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        # Strategy 2: Check for ship info pages (USS [ship] format or ship names)
        if not best_result:
            print(f"   📋 Strategy 2: Ship info page search")
            ship_results = controller.search_pages(search_query, limit=10)
            if ship_results:
                # Find first ship info page with URL
                for result in ship_results:
                    if result.get('url'):
                        best_result = result
                        best_strategy = "ship information page"
                        print(f"   ✓ Found ship info with URL: '{result.get('title')}'")
                        break
                print(f"   📊 Found {len(ship_results)} ship info pages, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        # Strategy 3: Direct ship name - search mission logs  
        if not best_result and any(ship in search_query.lower() for ship in ['stardancer', 'adagio', 'pilgrim', 'voyager', 'enterprise', 'defiant', 'protector', 'manta', 'gigantes', 'banshee', 'caelian']):
            # Extract ship name
            ship_name = None
            for ship in ['stardancer', 'adagio', 'pilgrim', 'voyager', 'enterprise', 'defiant', 'protector', 'manta', 'gigantes', 'banshee', 'caelian']:
                if ship in search_query.lower():
                    ship_name = ship
                    break
            
            if ship_name:
                print(f"   📋 Strategy 3: Recent mission logs for ship '{ship_name}'")
                results = controller.get_recent_logs(ship_name=ship_name, limit=5)
                if results:
                    # Find the first result that has a URL
                    for result in results:
                        if result.get('url'):
                            best_result = result
                            best_strategy = f"recent mission logs for {ship_name}"
                            print(f"   ✓ Found mission log with URL: '{result.get('title')}'")
                            break
                    print(f"   📊 Found {len(results)} recent logs, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        # Strategy 4: Search by exact title match (all page types)
        if not best_result:
            print(f"   📋 Strategy 4: Exact title search (all page types)")
            title_results = controller.search_pages(search_query, limit=10)
            if title_results:
                # Prioritize exact title matches that have URLs
                for result in title_results:
                    title = result.get('title', '')
                    if result.get('url') and (search_query.lower() in title.lower() or title.lower() in search_query.lower()):
                        categories = result.get('categories', [])
                        category_type = categories[0] if categories else 'unknown'
                        best_result = result
                        best_strategy = f"exact title match ({category_type})"
                        print(f"   ✓ Found exact match with URL: '{title}' ({category_type})")
                        break
                
                # If no exact match with URL, use first result with URL
                if not best_result:
                    for result in title_results:
                        if result.get('url'):
                            categories = result.get('categories', [])
                            category_type = categories[0] if categories else 'page'
                            best_result = result
                            best_strategy = f"{category_type} with URL"
                            print(f"   ✓ Found page with URL: '{result.get('title')}' ({category_type})")
                            break
                
                print(f"   📊 Found {len(title_results)} pages, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        # Strategy 5: General search (all page types)
        if not best_result:
            print(f"   📋 Strategy 5: General search (all page types)")
            general_results = controller.search_pages(search_query, limit=10)
            if general_results:
                # Find first result with URL
                for result in general_results:
                    if result.get('url'):
                        categories = result.get('categories', [])
                        category_type = categories[0] if categories else 'unknown'
                        best_result = result
                        best_strategy = f"general search ({category_type})"
                        print(f"   ✓ Found page with URL: '{result.get('title')}' ({category_type})")
                        break
                print(f"   📊 Found {len(general_results)} pages, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        if not best_result:
            print(f"✗ No pages with URLs found for query: '{search_query}'")
            return f"No pages with URLs found matching '{search_query}' in the database."
        
        # Extract information from the best result
        title = best_result.get('title', 'Unknown Title')
        url = best_result.get('url', None)
        categories = best_result.get('categories', [])
        log_date = best_result.get('log_date', None)
        ship_name = best_result.get('ship_name', None)
        
        print(f"✅ Found page via {best_strategy}: '{title}' - {url}")
        
        if url:
            # Format response based on categories
            if categories:
                category_type = categories[0]
                if any('log' in cat.lower() for cat in categories):
                    return f"**Mission Log Found:**\n\n**{title}** ({log_date})\nShip: {ship_name.upper() if ship_name else 'Unknown'}\n🔗 Direct Link: {url}"
                elif 'Ship Information' in categories:
                    return f"**Ship Information Found:**\n\n**{title}**\nType: Ship Information Page\n🔗 Direct Link: {url}"
                elif 'Characters' in categories:
                    return f"**Personnel Record Found:**\n\n**{title}**\nType: Personnel File\n🔗 Direct Link: {url}"
                else:
                    return f"**Page Found:**\n\n**{title}**\nType: {category_type}\n🔗 Direct Link: {url}"
            else:
                return f"**Page Found:**\n\n**{title}**\nType: Unknown\n🔗 Direct Link: {url}"
        else:
            category_type = categories[0] if categories else 'Unknown'
            return f"**Page Found:**\n\n**{title}**\nType: {category_type}\n⚠️  No direct URL available for this page."
        
    except Exception as e:
        print(f"✗ Error searching for page URL: {e}")
        return f"Error retrieving URL for '{search_query}': {e}"

def get_random_log_content(ship_name: Optional[str] = None, is_roleplay: bool = False) -> str:
    """Get one random mission log formatted for display"""
    try:
        controller = get_db_controller()
        print(f"🎲 RANDOM LOG SELECTION: ship='{ship_name}'")
        
        random_log = controller.get_random_log(ship_name)
        
        if not random_log:
            ship_msg = f" for {ship_name.upper()}" if ship_name else ""
            print(f"   ❌ No random log found{ship_msg}")
            return f"No mission logs found{ship_msg} in the database."
        
        # Filter out episode summaries
        if is_episode_summary(random_log):
            categories = random_log.get('categories', [])
            episode_cat = next((cat for cat in categories if 'episode summary' in cat.lower()), 'Episode Summary')
            print(f"   ❌ Random log is episode summary, skipping: '{random_log['title']}' Category='{episode_cat}'")
            # Try to get another random log that's not an episode summary
            print(f"   🔄 Attempting to get another random log (not episode summary)")
            return get_random_log_content(ship_name, is_roleplay)
        
        title = random_log['title']
        content = random_log['raw_content']
        log_date = random_log.get('log_date', 'Unknown Date')
        ship = random_log.get('ship_name', 'Unknown Ship')
        
        # Parse character speaking patterns in the log
        parsed_content = parse_log_characters(content, random_log.get('ship_name'), title)
        
        # Format the random log with special indicator
        formatted_log = f"**{title}** [Random Selection - {log_date}] ({ship.upper()})\n{parsed_content}"
        
        print(f"   ✅ Random log selected: '{title}' ({len(formatted_log)} chars)")
        
        # NEW: Always process log content through secondary LLM (regardless of size)
        print(f"🔄 Random log content ({len(formatted_log)} chars) - routing to secondary LLM for character processing")
        processor = get_llm_processor()
        query_description = f"random log" + (f" for {ship_name}" if ship_name else "")
        result = processor.process_query_results("logs", formatted_log, query_description, is_roleplay, force_processing=True)
        return result.content
        
    except Exception as e:
        print(f"✗ Error getting random log content: {e}")
        return f"Error retrieving random log: {e}"


def get_temporal_log_content(selection_type: str, ship_name: Optional[str] = None, limit: int = 5, is_roleplay: bool = False) -> str:
    """Get temporally ordered logs (newest or oldest first)"""
    try:
        controller = get_db_controller()
        print(f"📅 TEMPORAL LOG SELECTION: type='{selection_type}', ship='{ship_name}', limit={limit}")
        
        results = controller.get_selected_logs(selection_type, ship_name, limit)
        
        if not results:
            ship_msg = f" for {ship_name.upper()}" if ship_name else ""
            print(f"   ❌ No {selection_type} logs found{ship_msg}")
            return f"No {selection_type} mission logs found{ship_msg} in the database."
        
        log_contents = []
        
        for result in results:
            # Filter out episode summaries
            if is_episode_summary(result):
                categories = result.get('categories', [])
                episode_cat = next((cat for cat in categories if 'episode summary' in cat.lower()), 'Episode Summary')
                print(f"   ❌ Filtering out episode summary from temporal logs: '{result['title']}' Category='{episode_cat}'")
                continue
            
            title = result['title']
            content = result['raw_content']
            log_date = result.get('log_date', 'Unknown Date')
            ship = result.get('ship_name', 'Unknown Ship')
            
            # Parse character speaking patterns in the log
            parsed_content = parse_log_characters(content, result.get('ship_name'), title)
            
            # Format with temporal indicator
            temporal_label = {
                'latest': 'Latest',
                'recent': 'Recent', 
                'first': 'First',
                'earliest': 'Earliest',
                'oldest': 'Oldest',
                'today': 'Today',
                'yesterday': 'Yesterday',
                'this_week': 'This Week',
                'last_week': 'Last Week'
            }.get(selection_type, selection_type.title())
            
            formatted_log = f"**{title}** [{temporal_label} - {log_date}] ({ship.upper()})\n{parsed_content}"
            log_contents.append(formatted_log)
            
            print(f"   ✓ Added {selection_type} log: '{title}'")
        
        final_content = '\n\n---LOG SEPARATOR---\n\n'.join(log_contents)
        print(f"✅ TEMPORAL LOG SELECTION COMPLETE: {len(final_content)} characters from {len(log_contents)} logs")
        
        # NEW: Always process log content through secondary LLM (regardless of size)
        print(f"🔄 Log content ({len(final_content)} chars) - routing to secondary LLM for character processing")
        processor = get_llm_processor()
        query_description = f"{selection_type} logs" + (f" for {ship_name}" if ship_name else "")
        result = processor.process_query_results("logs", final_content, query_description, is_roleplay, force_processing=True)
        return result.content
        
    except Exception as e:
        print(f"✗ Error getting temporal log content: {e}")
        return f"Error retrieving {selection_type} logs: {e}"


def get_recent_log_url(search_query: str) -> str:
    """Get recent log URL - redirects to get_log_url for consistency"""
    return get_log_url(search_query)

def search_database_content(search_type: str, search_term: str = None, 
                           categories: List[str] = None, limit: int = 10, 
                           log_type: str = None, **kwargs) -> List[Dict]:
    """
    Universal database search interface that delegates to appropriate search methods.
    
    This function provides a unified interface for searching different types of content
    in the database, used by context_coordinator.py for quick and comprehensive searches.
    
    Args:
        search_type: Type of search ('character', 'ship', 'logs', 'general')
        search_term: Term to search for
        categories: List of categories to filter by
        limit: Maximum number of results to return
        log_type: Specific log type for log searches
        **kwargs: Additional parameters passed to underlying search methods
        
    Returns:
        List of search result dictionaries with keys: id, title, raw_content, 
        ship_name, log_date, url, categories
    """
    try:
        controller = get_db_controller()
        
        print(f"   🔍 UNIVERSAL SEARCH: type={search_type}, term='{search_term}', categories={categories}, limit={limit}")
        
        if search_type == 'character':
            # Character search - use search_characters or search_by_categories
            if categories:
                return controller.search_by_categories(search_term or '', categories, limit)
            else:
                return controller.search_characters(search_term or '', limit)
                
        elif search_type == 'ship':
            # Ship search - use search_ships or search_by_categories  
            if categories:
                return controller.search_by_categories(search_term or '', categories, limit)
            else:
                return controller.search_ships(search_term or '', limit)
                
        elif search_type == 'logs':
            # Log search - use search_logs
            ship_name = kwargs.get('ship_name')
            return controller.search_logs(search_term or '', ship_name, limit)
            
        else:
            # General search - use search_pages
            ship_name = kwargs.get('ship_name')
            return controller.search_pages(
                search_term or '', 
                page_type=search_type if search_type != 'general' else None,
                ship_name=ship_name,
                limit=limit,
                categories=categories
            )
            
    except Exception as e:
        print(f"   ❌ ERROR in search_database_content: {e}")
        return []


def search_titles_containing(search_term: str, limit: int = 10) -> List[Dict]:
    """
    Search for titles containing the given term.
    
    This function is used by context_coordinator.py for title-based searches.
    
    Args:
        search_term: Term to search for in titles
        limit: Maximum number of results to return
        
    Returns:
        List of search result dictionaries
    """
    try:
        controller = get_db_controller()
        
        print(f"   📖 TITLE SEARCH: '{search_term}', limit={limit}")
        
        # Use the general search_pages method which searches titles by default
        results = controller.search_pages(search_term, limit=limit)
        
        print(f"   📖 TITLE SEARCH RESULTS: {len(results)} found")
        return results
        
    except Exception as e:
        print(f"   ❌ ERROR in search_titles_containing: {e}")
        return [] 