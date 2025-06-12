"""Database-driven content retrieval and wiki search functionality"""

from database_controller import get_db_controller
from config import truncate_to_token_limit
from handlers.ai_logic.log_processor import parse_log_characters, is_ship_log_title, parse_character_dialogue
from handlers.ai_logic.query_detection import is_log_query
from typing import Optional
import psycopg2
import psycopg2.extras
import requests
import json
from urllib.parse import quote

def search_memory_alpha(query: str, limit: int = 3, is_federation_archives: bool = False) -> str:
    """
    Search Memory Alpha (Star Trek wiki) using MediaWiki API as fallback when local database has no results.
    Returns formatted content from Memory Alpha articles.
    
    Args:
        query: Search query
        limit: Number of results to return
        is_federation_archives: If True, adds [Federation Archives] tags for explicit federation archives requests
    """
    try:
        print(f"🌟 MEMORY ALPHA SEARCH: '{query}' (fallback search)")
        
        # Clean up the query for better search results
        search_query = query.strip()
        
        # MediaWiki API search endpoint
        base_url = "https://memory-alpha.fandom.com/api.php"
        
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
            print(f"   ❌ No Memory Alpha search results found")
            return ""
        
        search_results = search_data['query']['search']
        if not search_results:
            print(f"   ❌ No Memory Alpha articles found for '{query}'")
            return ""
        
        print(f"   📊 Found {len(search_results)} Memory Alpha articles")
        
        # Get content for the top results
        memory_alpha_content = []
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
            print(f"   ❌ Could not retrieve Memory Alpha content")
            return ""
        
        pages = content_data['query']['pages']
        
        for page_id, page_data in pages.items():
            if page_id == '-1':  # Page not found
                continue
                
            title = page_data.get('title', 'Unknown Title')
            extract = page_data.get('extract', '')
            
            if extract:
                # Format for Elsie's response - only add [Federation Archives] tag if explicitly requested
                page_url = f"https://memory-alpha.fandom.com/wiki/{quote(title.replace(' ', '_'))}"
                if is_federation_archives:
                    formatted_content = f"**{title}** [Federation Archives]\n{extract}"
                else:
                    formatted_content = f"**{title}**\n{extract}"
                memory_alpha_content.append(formatted_content)
                print(f"   ✓ Retrieved Memory Alpha article: '{title}' ({len(extract)} chars)")
        
        if not memory_alpha_content:
            print(f"   ❌ No usable Memory Alpha content found")
            return ""
        
        # Only use Federation Archives separator when explicitly requested
        if is_federation_archives:
            final_content = '\n\n---FEDERATION ARCHIVES---\n\n'.join(memory_alpha_content)
        else:
            final_content = '\n\n---\n\n'.join(memory_alpha_content)
        print(f"✅ MEMORY ALPHA SEARCH COMPLETE: {len(final_content)} characters from {len(memory_alpha_content)} articles")
        return final_content
        
    except requests.RequestException as e:
        print(f"   ❌ Memory Alpha API request failed: {e}")
        return ""
    except Exception as e:
        print(f"   ❌ Memory Alpha search error: {e}")
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

def get_log_content(query: str, mission_logs_only: bool = False) -> str:
    """Get full log content using hierarchical search (titles first, then content) - NO TRUNCATION
    
    Args:
        query: Search query
        mission_logs_only: If True, only search mission_log type pages, ignore other types
    """
    try:
        controller = get_db_controller()
        print(f"🔍 HIERARCHICAL LOG SEARCH: '{query}' (mission_logs_only={mission_logs_only})")
        
        # Search for different types of logs using hierarchical search
        if mission_logs_only:
            log_types = ["mission_log"]
            print(f"   🎯 SPECIFIC LOG REQUEST: Only searching mission_log type pages")
        else:
            log_types = ["mission_log"]
            print(f"   📊 GENERAL LOG REQUEST: Comprehensive search including fallback")
        
        all_results = []
        
        for log_type in log_types:
            results = controller.search_pages(query, page_type=log_type, limit=10)  # Increased limit
            print(f"   📊 {log_type} hierarchical search returned {len(results)} results")
            all_results.extend(results)
        
        # Remove duplicates based on ID
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result['id'] not in seen_ids:
                unique_results.append(result)
                seen_ids.add(result['id'])
        
        print(f"   📊 Total unique log results: {len(unique_results)}")
        
        if not unique_results and not mission_logs_only:
            # Fallback: Try general hierarchical search with log keywords (only if not mission_logs_only)
            print(f"   🔄 No typed logs found, trying general hierarchical search...")
            results = controller.search_pages(f"{query} log", limit=20)  # Increased limit
            print(f"   📊 General hierarchical search returned {len(results)} results")
            
            # Filter to ship logs and other log-like titles using enhanced detection
            log_results = []
            for r in results:
                title = r['title']
                content_preview = r['raw_content'][:50] + "..." if len(r['raw_content']) > 50 else r['raw_content']
                
                # Use enhanced ship log detection
                if is_ship_log_title(title):
                    log_results.append(r)
                    print(f"   ✓ Detected ship log: '{title}' Content='{content_preview}'")
                # Also check for other log indicators
                elif any(indicator in title.lower() for indicator in ['personal', 'captain', 'stardate']):
                    log_results.append(r)
                    print(f"   ✓ Detected other log: '{title}' Content='{content_preview}'")
                else:
                    print(f"   ✗ Not a log: '{title}' Content='{content_preview}'")
            
            print(f"   📊 Enhanced filtering found {len(log_results)} log-like results")
            unique_results = log_results
        elif not unique_results and mission_logs_only:
            print(f"   🎯 No mission logs found for specific request: '{query}'")
            return ""
        
        if not unique_results:
            print(f"✗ No log content found for query: '{query}'")
            return ""
        
        log_contents = []
        
        for result in unique_results:
            title = result['title']
            content = result['raw_content']  # NO LENGTH LIMIT
            page_type = result.get('page_type', 'unknown')
            print(f"   📄 Processing {page_type}: '{title}' ({len(content)} chars)")
            
            # Parse character speaking patterns in the log using enhanced dialogue parsing
            parsed_content = parse_log_characters(content)
            
            # Format the log with title and parsed content
            formatted_log = f"**{title}**\n{parsed_content}"
            
            # Debug: Show first 50 chars of the formatted log
            formatted_preview = formatted_log[:100].replace('\n', ' ') + "..." if len(formatted_log) > 100 else formatted_log.replace('\n', ' ')
            print(f"   📝 Formatted log preview: '{formatted_preview}'")
            
            log_contents.append(formatted_log)
            print(f"   ✓ Added {page_type}: {title}")
        
        final_content = '\n\n---LOG SEPARATOR---\n\n'.join(log_contents)
        print(f"✅ HIERARCHICAL LOG SEARCH COMPLETE: {len(final_content)} characters from {len(log_contents)} logs")
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting log content: {e}")
        return ""

def get_relevant_wiki_context(query: str, mission_logs_only: bool = False) -> str:
    """Get relevant wiki content using hierarchical search (titles first, then content) - NO TRUNCATION
    
    Args:
        query: Search query
        mission_logs_only: If True, only search mission_log type pages when detecting log queries
    """
    try:
        controller = get_db_controller()
        
        # Check if this is a log query - handle with hierarchical log retrieval
        if is_log_query(query):
            log_content = get_log_content(query, mission_logs_only=mission_logs_only)
            if log_content:
                log_type_msg = "mission logs only" if mission_logs_only else "all log types"
                print(f"✓ Log query detected, retrieved {len(log_content)} chars of log content ({log_type_msg})")
                return log_content
            else:
                log_type_msg = "mission logs only" if mission_logs_only else "all log types"
                print(f"⚠️  Log query detected but no log content found ({log_type_msg})")
        
        # Use hierarchical database search for better results
        print(f"🔍 HIERARCHICAL WIKI SEARCH: '{query}'")
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
        return final_context
        
    except Exception as e:
        print(f"✗ Error getting wiki context: {e}")
        return ""

def get_ship_information(ship_name: str) -> str:
    """Get detailed information about a specific ship - NO TRUNCATION"""
    try:
        controller = get_db_controller()
        results = controller.get_ship_info(ship_name)
        
        if not results:
            return ""
        
        ship_info = []

        for result in results:
            title = result['title']
            content = result['raw_content']  # NO LENGTH LIMIT

            page_text = f"**{title}**\n{content}"
            ship_info.append(page_text)

        final_content = '\n\n---\n\n'.join(ship_info)
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting ship information: {e}")
        return ""

def get_recent_logs(ship_name: Optional[str] = None, limit: int = 10) -> str:
    """Get recent mission logs - NO TRUNCATION"""
    try:
        controller = get_db_controller()
        results = controller.get_recent_logs(ship_name=ship_name, limit=limit)
        
        if not results:
            return ""
        
        log_summaries = []

        for result in results:
            title = result['title']
            content = result['raw_content']  # NO LENGTH LIMIT
            log_date = result['log_date']

            log_entry = f"**{title}** ({log_date})\n{content}"
            log_summaries.append(log_entry)

        final_content = '\n\n---\n\n'.join(log_summaries)
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting recent logs: {e}")
        return ""

def search_by_type(query: str, content_type: str) -> str:
    """Search for specific type of content - NO TRUNCATION"""
    try:
        controller = get_db_controller()
        results = controller.search_pages(query, page_type=content_type, limit=10)  # Increased limit
        
        if not results:
            return ""
        
        search_results = []

        for result in results:
            title = result['title']
            content = result['raw_content']  # NO LENGTH LIMIT

            page_text = f"**{title}**\n{content}"
            search_results.append(page_text)

        final_content = '\n\n---\n\n'.join(search_results)
        return final_content
        
    except Exception as e:
        print(f"✗ Error searching by type: {e}")
        return ""

def get_tell_me_about_content(subject: str) -> str:
    """Enhanced 'tell me about' functionality using hierarchical search - NO TRUNCATION"""
    try:
        controller = get_db_controller()
        print(f"🔍 HIERARCHICAL 'TELL ME ABOUT' SEARCH: '{subject}'")
        
        # Use hierarchical search - will search titles first, then content
        results = controller.search_pages(subject, limit=15)  # Increased limit
        print(f"   📊 Hierarchical search returned {len(results)} results")
        
        # If it looks like a ship name, also search ship-specific content
        if any(ship in subject.lower() for ship in ['uss', 'ship', 'vessel']):
            print(f"   🚢 Ship detected, searching ship-specific content...")
            ship_results = controller.search_pages(subject, page_type='ship_info', limit=10)  # Increased limit
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
            content = result['raw_content']  # NO LENGTH LIMIT
            page_type = result.get('page_type', 'general')
            
            # Add type indicator for clarity
            type_indicator = ""
            if page_type == 'mission_log':
                type_indicator = " [Mission Log]"
            elif page_type == 'ship_info':
                type_indicator = " [Ship Information]"
            elif page_type == 'personnel':
                type_indicator = " [Personnel File]"
            
            page_text = f"**{title}{type_indicator}**\n{content}"
            content_parts.append(page_text)
        
        final_content = '\n\n---\n\n'.join(content_parts)
        print(f"✅ HIERARCHICAL 'TELL ME ABOUT' COMPLETE: {len(final_content)} characters from {len(content_parts)} sources")
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting 'tell me about' content: {e}")
        return ""

def get_tell_me_about_content_prioritized(subject: str) -> str:
    """Enhanced 'tell me about' functionality that prioritizes ship info and personnel over logs - NO TRUNCATION"""
    try:
        controller = get_db_controller()
        print(f"🔍 PRIORITIZED 'TELL ME ABOUT' SEARCH: '{subject}'")
        
        # Step 1: Search for ship info specifically first
        ship_info_results = []
        if any(indicator in subject.lower() for indicator in ['uss', 'ship', 'stardancer', 'adagio', 'pilgrim', 'voyager', 'enterprise']):
            print(f"   🚢 PRIORITY: Searching ship info pages first...")
            ship_info_results = controller.search_pages(subject, page_type='ship_info', limit=10)  # Increased limit
            print(f"   📊 Ship info search found {len(ship_info_results)} results")
        
        # Step 2: Search for personnel records
        personnel_results = []
        if any(indicator in subject.lower() for indicator in ['captain', 'commander', 'lieutenant', 'ensign', 'admiral', 'officer']):
            print(f"   👥 PRIORITY: Searching personnel records...")
            personnel_results = controller.search_pages(subject, page_type='personnel', limit=10)  # Increased limit
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
            page_type = result.get('page_type', 'general')
            
            # Skip mission logs unless no other content was found
            if page_type == 'mission_log' and priority_results:
                print(f"   ⏭️  Skipping mission log '{title}' (ship/personnel info available)")
                continue
            
            # Add type indicator for clarity
            type_indicator = ""
            if page_type == 'mission_log':
                type_indicator = " [Mission Log]"
            elif page_type == 'ship_info':
                type_indicator = " [Ship Information]"
            elif page_type == 'personnel':
                type_indicator = " [Personnel File]"
            
            page_text = f"**{title}{type_indicator}**\n{content}"
            content_parts.append(page_text)
            print(f"   ✓ Added {page_type}: '{title}'")
        
        final_content = '\n\n---\n\n'.join(content_parts)
        print(f"✅ PRIORITIZED 'TELL ME ABOUT' COMPLETE: {len(final_content)} characters from {len(content_parts)} sources")
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting prioritized 'tell me about' content: {e}")
        return ""

def debug_manual_query(query: str, page_type: str = None) -> str:
    """Manual query function for debugging database searches"""
    try:
        controller = get_db_controller()
        print(f"\n🔧 MANUAL DEBUG QUERY")
        print(f"Query: '{query}'")
        print(f"Page Type Filter: {page_type}")
        print("-" * 40)
        
        results = controller.search_pages(query, page_type=page_type, limit=10)
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\nResult {i}:")
            print(f"  ID: {result['id']}")
            print(f"  Title: '{result['title']}'")
            print(f"  Page Type: '{result['page_type']}'")
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
                for result in results:
                    if result.get('url') and result.get('page_type') == 'mission_log':
                        best_result = result
                        best_strategy = f"most recent mission log for {ship_name}"
                        print(f"   ✓ Found mission log with URL: '{result.get('title')}'")
                        break
                print(f"   📊 Found {len(results)} recent logs, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        # Strategy 2: Check for ship info pages (USS [ship] format or ship names)
        if not best_result:
            print(f"   📋 Strategy 2: Ship info page search")
            ship_results = controller.search_pages(search_query, page_type='ship_info', limit=10)
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
                        best_result = result
                        best_strategy = f"exact title match ({result.get('page_type', 'unknown')})"
                        print(f"   ✓ Found exact match with URL: '{title}' ({result.get('page_type')})")
                        break
                
                # If no exact match with URL, use first result with URL
                if not best_result:
                    for result in title_results:
                        if result.get('url'):
                            best_result = result
                            best_strategy = f"{result.get('page_type', 'page')} with URL"
                            print(f"   ✓ Found page with URL: '{result.get('title')}' ({result.get('page_type')})")
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
                        best_result = result
                        best_strategy = f"general search ({result.get('page_type', 'unknown')})"
                        print(f"   ✓ Found page with URL: '{result.get('title')}' ({result.get('page_type')})")
                        break
                print(f"   📊 Found {len(general_results)} pages, selected: {best_result.get('title') if best_result else 'none with URL'}")
        
        if not best_result:
            print(f"✗ No pages with URLs found for query: '{search_query}'")
            return f"No pages with URLs found matching '{search_query}' in the database."
        
        # Extract information from the best result
        title = best_result.get('title', 'Unknown Title')
        url = best_result.get('url', None)
        page_type = best_result.get('page_type', 'page')
        log_date = best_result.get('log_date', None)
        ship_name = best_result.get('ship_name', None)
        
        print(f"✅ Found page via {best_strategy}: '{title}' - {url}")
        
        if url:
            # Format response based on page type
            if page_type == 'mission_log':
                return f"**Mission Log Found:**\n\n**{title}** ({log_date})\nShip: {ship_name.upper() if ship_name else 'Unknown'}\n🔗 Direct Link: {url}"
            elif page_type == 'ship_info':
                return f"**Ship Information Found:**\n\n**{title}**\nType: Ship Information Page\n🔗 Direct Link: {url}"
            elif page_type == 'personnel':
                return f"**Personnel Record Found:**\n\n**{title}**\nType: Personnel File\n🔗 Direct Link: {url}"
            else:
                return f"**Page Found:**\n\n**{title}**\nType: {page_type.title()}\n🔗 Direct Link: {url}"
        else:
            return f"**Page Found:**\n\n**{title}**\nType: {page_type.title()}\n⚠️  No direct URL available for this page."
        
    except Exception as e:
        print(f"✗ Error searching for page URL: {e}")
        return f"Error retrieving URL for '{search_query}': {e}"

def get_recent_log_url(search_query: str) -> str:
    """Legacy function - redirects to get_log_url for backward compatibility"""
    return get_log_url(search_query) 