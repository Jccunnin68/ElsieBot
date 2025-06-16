"""Database-driven content retrieval and wiki search functionality"""

from database_controller import get_db_controller
from typing import Optional, List
import requests
from urllib.parse import quote
import re
from .log_patterns import (
    CHARACTER_CORRECTIONS, 
    SHIP_NAMES,
    resolve_character_name_with_context,
    extract_ship_name_from_log_content
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
        'search_by_type': f"{kwargs.get('content_type', 'content')} matching '{kwargs.get('query', '')}'",
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
        while frame:
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

def is_ship_log_title(title: str) -> bool:
    """Enhanced ship log title detection supporting multiple formats:
    - Ship Name Date
    - Date Ship Name Log  
    - Date Ship Name
    - Ship Name Date Log
    - Something like 'The Anevian Incident' Log
    """
    title_lower = title.lower().strip()
    
    # Basic log patterns for any ship name
    for ship in SHIP_NAMES:
        ship_lower = ship.lower()
        
        # Pattern 1: Ship Name Date (e.g., "Adagio 2024/01/06")
        date_patterns = [
            f"^{ship_lower}\\s+\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}",  # ship 2024/01/06
            f"^{ship_lower}\\s+\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}",   # ship 1/6/2024
            f"^{ship_lower}\\s+\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}",   # ship 2024-01-06
            f"^{ship_lower}\\s+\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}",   # ship 1-6-2024
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, title_lower):
                return True
        
        # Pattern 2: Date Ship Name (e.g., "2024/01/06 Adagio")
        date_ship_patterns = [
            f"^\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}\\s+{ship_lower}",   # 2024/01/06 ship
            f"^\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}\\s+{ship_lower}",   # 1/6/2024 ship
            f"^\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}\\s+{ship_lower}",   # 2024-01-06 ship
            f"^\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}\\s+{ship_lower}",   # 1-6-2024 ship
        ]
        
        for pattern in date_ship_patterns:
            if re.match(pattern, title_lower):
                return True
        
        # Pattern 3: Ship Name Date Log (e.g., "Adagio 2024/01/06 Log")
        date_log_patterns = [
            f"^{ship_lower}\\s+\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}\\s+log",
            f"^{ship_lower}\\s+\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}\\s+log",
            f"^{ship_lower}\\s+\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}\\s+log",
            f"^{ship_lower}\\s+\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}\\s+log",
        ]
        
        for pattern in date_log_patterns:
            if re.match(pattern, title_lower):
                return True
        
        # Pattern 4: Date Ship Name Log (e.g., "2024/01/06 Adagio Log") 
        date_ship_log_patterns = [
            f"^\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}\\s+{ship_lower}\\s+log",
            f"^\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}\\s+{ship_lower}\\s+log",
            f"^\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}\\s+{ship_lower}\\s+log",
            f"^\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}\\s+{ship_lower}\\s+log",
        ]
        
        for pattern in date_ship_log_patterns:
            if re.match(pattern, title_lower):
                return True
    
    # Pattern 5: Named incidents/events ending with "Log" (e.g., "The Anevian Incident Log")
    if title_lower.endswith(' log') and len(title_lower) > 4:
        # Check if it contains words that suggest it's an event/incident
        event_indicators = ['incident', 'event', 'mission', 'encounter', 'crisis', 'affair', 'operation']
        if any(indicator in title_lower for indicator in event_indicators):
            return True
        
        # Check if it contains "the" at the beginning, suggesting a named event
        if title_lower.startswith('the ') and len(title_lower.split()) >= 3:
            return True
    
    # Pattern 6: Any title with ship name and "log" anywhere
    for ship in SHIP_NAMES:
        ship_lower = ship.lower()
        if ship_lower in title_lower and 'log' in title_lower:
            return True
    
    return False


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
            print(f"✓ elsiebrain database ready: {stats.get('total_pages', 0)} pages, {stats.get('mission_logs', 0)} logs")
        else:
            print("⚠️  elsiebrain database is connected but empty - needs to be populated externally")
        
        return True
        
    except Exception as e:
        print(f"✗ Error connecting to elsiebrain database: {e}")
        print("   Make sure the elsiebrain database exists and is populated")
        return False

def debug_schema_info():
    """Debug function to inspect database schema"""
    try:
        controller = get_db_controller()
        return controller.get_schema_info()
    except Exception as e:
        print(f"✗ Error getting schema info: {e}")
        return {}

def get_log_content(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    """Get full log content using hierarchical search with categories - NO TRUNCATION
    
    Args:
        query: Search query
        mission_logs_only: If True, only search ship log categories, ignore other types
        is_roleplay: If True, use roleplay-appropriate fallback responses when processing fails
    """
    try:
        controller = get_db_controller()
        print(f"🔍 HIERARCHICAL LOG SEARCH: '{query}' (mission_logs_only={mission_logs_only}, roleplay={is_roleplay})")
        
        # Check for log selection queries first
        from ..ai_logic.query_detection import detect_log_selection_query
        is_selection, selection_type, ship_name = detect_log_selection_query(query)
        
        if is_selection:
            print(f"   🎯 LOG SELECTION DETECTED: type='{selection_type}', ship='{ship_name}'")
            
            if selection_type == 'random':
                # Get one random log
                return get_random_log_content(ship_name, is_roleplay)
            elif selection_type in ['latest', 'recent']:
                # Get most recent logs - "latest" should return only 1, "recent" can return multiple
                limit = 1 if selection_type == 'latest' else 5
                return get_temporal_log_content(selection_type, ship_name, limit=limit, is_roleplay=is_roleplay)
            elif selection_type in ['first', 'earliest', 'oldest']:
                # Get oldest logs - "first" should return only 1, others can return multiple  
                limit = 1 if selection_type == 'first' else 5
                return get_temporal_log_content(selection_type, ship_name, limit=limit, is_roleplay=is_roleplay)
            elif selection_type in ['today', 'yesterday', 'this_week', 'last_week']:
                # Get date-filtered logs
                return get_temporal_log_content(selection_type, ship_name, limit=10, is_roleplay=is_roleplay)
        
        # Use dynamic log category filtering instead of hardcoded categories
        from .category_mappings import get_all_log_categories
        log_categories = get_all_log_categories()
        print(f"   📊 STANDARD LOG REQUEST: Using dynamic log categories: {len(log_categories)} categories")
        
        # Search using dynamic log categories instead of hardcoded categories
        if mission_logs_only:
            # Use only dynamic log categories
            results = controller.search_by_categories(query, log_categories, limit=20)
            print(f"   📊 Dynamic log category search returned {len(results)} results")
        else:
            # Use force_mission_logs_only for backward compatibility
            results = controller.search_pages(query, limit=20, force_mission_logs_only=True)
            print(f"   📊 Force mission logs search returned {len(results)} results")
        
        # Filter out episode summaries from the main results
        filtered_results = []
        for r in results:
            if is_episode_summary(r):
                categories = r.get('categories', [])
                episode_cat = next((cat for cat in categories if 'episode summary' in cat.lower()), 'Episode Summary')
                print(f"   ❌ Filtering out episode summary from main results: '{r['title']}' Category='{episode_cat}'")
            else:
                filtered_results.append(r)
        
        unique_results = filtered_results
        
        if not unique_results and not mission_logs_only:
            # Fallback: Try general hierarchical search with log keywords (only if not mission_logs_only)
            print(f"   🔄 No category-based logs found, trying general hierarchical search...")
            results = controller.search_pages(f"{query} log", limit=20)  # Increased limit
            print(f"   📊 General hierarchical search returned {len(results)} results")
            
            # Filter to ship logs and other log-like titles using enhanced detection
            log_results = []
            for r in results:
                title = r['title']
                content_preview = r['raw_content'][:50] + "..." if len(r['raw_content']) > 50 else r['raw_content']
                categories = r.get('categories', [])
                
                # Filter out episode summaries
                if is_episode_summary(r):
                    episode_cat = next((cat for cat in categories if 'episode summary' in cat.lower()), 'Episode Summary')
                    print(f"   ❌ Filtering out episode summary: '{title}' Category='{episode_cat}'")
                    continue
                
                # Check if it has log categories or use enhanced ship log detection
                if any(cat in log_categories for cat in categories):
                    log_results.append(r)
                    print(f"   ✓ Category-based log: '{title}' Categories={categories}")
                elif is_ship_log_title(title):
                    log_results.append(r)
                    print(f"   ✓ Title-based ship log: '{title}' Content='{content_preview}'")
                # Also check for other log indicators
                elif any(indicator in title.lower() for indicator in ['personal', 'captain', 'stardate']):
                    log_results.append(r)
                    print(f"   ✓ Detected other log: '{title}' Content='{content_preview}'")
                else:
                    print(f"   ✗ Not a log: '{title}' Content='{content_preview}'")
            
            print(f"   📊 Enhanced filtering found {len(log_results)} log-like results")
            unique_results = log_results
        elif not unique_results and mission_logs_only:
            print(f"   🎯 No ship log categories found for specific request: '{query}'")
            return ""
        
        if not unique_results:
            print(f"✗ No log content found for query: '{query}'")
            return ""
        
        log_contents = []
        
        for result in unique_results:
            title = result['title']
            content = result['raw_content']  # NO LENGTH LIMIT
            categories = result.get('categories', [])
            page_type = result.get('page_type', 'unknown')
            print(f"   📄 Processing: '{title}' ({len(content)} chars)")
            
            # Parse character speaking patterns in the log using enhanced dialogue parsing
            parsed_content = parse_log_characters(content, result.get('ship_name'), title)
            
            # Format the log with title and parsed content
            formatted_log = f"**{title}**\n{parsed_content}"
            
            log_contents.append(formatted_log)
            print(f"   ✓ Added: {title}")
        
        final_content = '\n\n---LOG SEPARATOR---\n\n'.join(log_contents)
        print(f"✅ HIERARCHICAL LOG SEARCH COMPLETE: {len(final_content)} characters from {len(log_contents)} logs")
        
        # NEW: Always process log content through secondary LLM (regardless of size)
        print(f"🔄 Log content ({len(final_content)} chars) - routing to secondary LLM for character processing")
        processor = get_llm_processor()
        result = processor.process_query_results("logs", final_content, query, is_roleplay, force_processing=True)
        return result.content
        
    except Exception as e:
        print(f"✗ Error getting log content: {e}")
        return ""

def get_relevant_wiki_context(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    """Get relevant wiki content using hierarchical search (titles first, then content) - NO TRUNCATION
    
    Args:
        query: Search query
        mission_logs_only: If True, only search mission_log type pages when detecting log queries
        is_roleplay: If True, use roleplay-appropriate fallback responses when processing fails
    """
    try:
        controller = get_db_controller()
        
        # Check if this is a log query - handle with hierarchical log retrieval
        # Inline check to avoid circular import with query_detection.py
        log_indicators = [
            'log', 'logs', 'mission log', 'ship log', 'stardancer log', 
            'captain log', 'personal log', 'stardate', 'entry',
            'what happened', 'events', 'mission report', 'incident report',
            'summarize', 'summary', 'recap', 'tell me what',
            'last mission', 'recent mission', 'latest log'
        ]
        is_log_query_result = any(indicator in query.lower() for indicator in log_indicators)
        
        if is_log_query_result:
            log_content = get_log_content(query, mission_logs_only=mission_logs_only, is_roleplay=is_roleplay)
            if log_content:
                log_type_msg = "mission logs only" if mission_logs_only else "all log types"
                print(f"✓ Log query detected, retrieved {len(log_content)} chars of log content ({log_type_msg})")
                return log_content
            else:
                log_type_msg = "mission logs only" if mission_logs_only else "all log types"
                print(f"⚠️  Log query detected but no log content found ({log_type_msg})")
        
        # Use hierarchical database search for better results
        print(f"🔍 HIERARCHICAL WIKI SEARCH: '{query}' (roleplay={is_roleplay})")
        results = controller.search_pages(query, limit=20)  # Increased limit
        
        if not results:
            print(f"✗ No wiki content found for query: {query}")
            return ""
        
        print(f"   📊 Hierarchical search returned {len(results)} results")
        
        context_parts = []
        
        for result in results:
            title = result['title']
            content = result['raw_content']  # NO LENGTH LIMIT
            
            page_text = f"**{title}**\n{content}"
            context_parts.append(page_text)
        
        final_context = '\n\n---\n\n'.join(context_parts)
        print(f"✅ HIERARCHICAL WIKI SEARCH COMPLETE: {len(final_context)} characters from {len(context_parts)} pages")
        
        # NEW: Process large content through LLM if needed
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
    """Get detailed information about a specific ship"""
    try:
        controller = get_db_controller()
        results = controller.get_ship_info(ship_name)
        
        if not results:
            return ""
        
        ship_info = []

        for result in results:
            title = result['title']
            content = result['raw_content']

            page_text = f"**{title}**\n{content}"
            ship_info.append(page_text)

        final_content = '\n\n---\n\n'.join(ship_info)
        
        # Process large content through LLM if needed
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

def search_by_type(query: str, content_type: str) -> str:
    """Search for specific type of content using categories when available"""
    try:
        controller = get_db_controller()
        
        # Convert content_type to categories for better search
        from .category_mappings import convert_page_type_to_categories
        categories = convert_page_type_to_categories(content_type)
        
        if categories:
            print(f"🏷️ CATEGORY SEARCH: '{content_type}' -> categories: {categories}")
            results = controller.search_by_categories(query, categories, limit=10)
        else:
            print(f"📋 UNKNOWN CONTENT TYPE: '{content_type}' - using general search")
            results = controller.search_pages(query, limit=10)
        
        if not results:
            return ""
        
        search_results = []

        for result in results:
            title = result['title']
            content = result['raw_content']
            categories = result.get('categories', [])
            
            # Add category info to the result
            category_info = f" [Categories: {', '.join(categories)}]" if categories else ""
            page_text = f"**{title}**{category_info}\n{content}"
            search_results.append(page_text)

        final_content = '\n\n---\n\n'.join(search_results)
        
        # Process large content through LLM if needed
        if should_process_data(final_content):
            print(f"🔄 Content size ({len(final_content)} chars) exceeds threshold, processing with LLM...")
            processor = get_llm_processor()
            query_type = determine_query_type('search_by_type', content_type)
            query_description = create_query_description('search_by_type', query=query, content_type=content_type)
            is_roleplay = _get_roleplay_context_from_caller()
            result = processor.process_query_results(query_type, final_content, query_description, is_roleplay)
            return result.content
        
        return final_content
        
    except Exception as e:
        print(f"✗ Error searching by type: {e}")
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
            from .category_mappings import convert_page_type_to_categories
            ship_categories = convert_page_type_to_categories('ship_info')
            ship_results = controller.search_by_categories(subject, ship_categories, limit=10)
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
                # Determine primary category type
                if any(cat in categories for cat in ['Stardancer Log', 'Adagio Log', 'Pilgrim Log', 'Banshee Log', 'Gigantes Log']):
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
            from .category_mappings import convert_page_type_to_categories
            ship_categories = convert_page_type_to_categories('ship_info')
            ship_info_results = controller.search_by_categories(subject, ship_categories, limit=10)
            print(f"   📊 Ship info search found {len(ship_info_results)} results")
        
        # Step 2: Search for personnel records
        personnel_results = []
        if any(indicator in subject.lower() for indicator in ['captain', 'commander', 'lieutenant', 'ensign', 'admiral', 'officer']):
            print(f"   👥 PRIORITY: Searching personnel records...")
            from .category_mappings import convert_page_type_to_categories
            personnel_categories = convert_page_type_to_categories('personnel')
            personnel_results = controller.search_by_categories(subject, personnel_categories, limit=10)
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
            is_mission_log = any(cat in categories for cat in ['Stardancer Log', 'Adagio Log', 'Pilgrim Log', 'Banshee Log', 'Gigantes Log']) if categories else False
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

def debug_manual_query(query: str, categories: List[str] = None) -> str:
    """Manual query function for debugging database searches - now uses categories"""
    try:
        controller = get_db_controller()
        print(f"\n🔧 MANUAL DEBUG QUERY")
        print(f"Query: '{query}'")
        print(f"Categories Filter: {categories}")
        print("-" * 40)
        
        if categories:
            results = controller.search_by_categories(query, categories, limit=10)
        else:
            results = controller.search_pages(query, limit=10)
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"  ID: {result['id']}")
            print(f"  Title: '{result['title']}'")
            print(f"  Categories: {result.get('categories', [])}")
            print(f"  Ship Name: '{result['ship_name']}'")
            print(f"  Content (50 chars): '{result['raw_content'][:50]}...'")
            print(f"  Log Date: {result['log_date']}")
        
        print("-" * 40)
        return f"Found {len(results)} results"
        
    except Exception as e:
        print(f"✗ Error in manual query: {e}")
        return ""

def run_database_cleanup():
    """Run all database cleanup operations"""
    try:
        controller = get_db_controller()
        
        print("🔧 STARTING DATABASE CLEANUP OPERATIONS")
        print("=" * 60)
        
        # Step 1: Clean up ship names for mission logs
        ship_results = controller.cleanup_mission_log_ship_names()
        
        # Step 2: Clean up seed/example data
        seed_results = controller.cleanup_seed_data()
        
        # Step 3: Show final stats
        final_stats = controller.get_stats()
        
        print("🎉 DATABASE CLEANUP COMPLETE!")
        print("=" * 60)
        print("📊 FINAL STATISTICS:")
        print(f"  - Total pages: {final_stats.get('total_pages', 0)}")
        print(f"  - Mission logs: {final_stats.get('mission_logs', 0)}")
        print(f"  - Ship info: {final_stats.get('ship_info', 0)}")
        print(f"  - Personnel: {final_stats.get('personnel', 0)}")
        print(f"  - Unique ships: {final_stats.get('unique_ships', 0)}")
        print("=" * 60)
        
        return {
            'ship_cleanup': ship_results,
            'seed_cleanup': seed_results,
            'final_stats': final_stats
        }
        
    except Exception as e:
        print(f"✗ Error running database cleanup: {e}")
        return {}

def cleanup_ship_names_only():
    """Just run the ship name cleanup"""
    try:
        controller = get_db_controller()
        return controller.cleanup_mission_log_ship_names()
    except Exception as e:
        print(f"✗ Error cleaning up ship names: {e}")
        return {}

def cleanup_seed_data_only():
    """Just run the seed data cleanup"""
    try:
        controller = get_db_controller()
        return controller.cleanup_seed_data()
    except Exception as e:
        print(f"✗ Error cleaning up seed data: {e}")
        return {}

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
                from .category_mappings import SHIP_LOG_CATEGORIES
                for result in results:
                    categories = result.get('categories', [])
                    if result.get('url') and any(cat in SHIP_LOG_CATEGORIES for cat in categories):
                        best_result = result
                        best_strategy = f"most recent mission log for {ship_name}"
                        print(f"   ✓ Found mission log with URL: '{result.get('title')}'")
                        break
                print(f"   📊 Found {len(results)} recent logs, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        # Strategy 2: Check for ship info pages (USS [ship] format or ship names)
        if not best_result:
            print(f"   📋 Strategy 2: Ship info page search")
            from .category_mappings import convert_page_type_to_categories
            ship_categories = convert_page_type_to_categories('ship_info')
            ship_results = controller.search_by_categories(search_query, ship_categories, limit=10)
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
                if any(cat in categories for cat in ['Stardancer Log', 'Adagio Log', 'Pilgrim Log', 'Banshee Log', 'Gigantes Log']):
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