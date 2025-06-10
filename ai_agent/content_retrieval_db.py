"""Database-driven content retrieval and wiki search functionality"""

from database_controller import get_db_controller
from config import MAX_CHARS_LOG, MAX_CHARS_CONTEXT
from log_processor import is_log_query, parse_log_characters, is_ship_log_title
from typing import Optional

def check_elsiebrain_connection() -> bool:
    """Check if the elsiebrain database is accessible and populated"""
    try:
        controller = get_db_controller()
        stats = controller.get_stats()
        
        if stats and stats.get('total_pages', 0) > 0:
            print(f"✓ elsiebrain database ready: {stats.get('total_pages', 0)} pages, {stats.get('mission_logs', 0)} logs")
            
            # Also show schema info for debugging
            print("\n🔍 PERFORMING SCHEMA ANALYSIS FOR DEBUGGING:")
            schema_info = controller.get_schema_info()
            
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

def get_log_content(query: str) -> str:
    """Get full log content using hierarchical search (titles first, then content)"""
    try:
        controller = get_db_controller()
        print(f"🔍 HIERARCHICAL LOG SEARCH: '{query}'")
        
        # Search for different types of logs using hierarchical search
        log_types = ["mission_log"]
        all_results = []
        
        for log_type in log_types:
            results = controller.search_pages(query, page_type=log_type, limit=3)
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
        
        if not unique_results:
            # Fallback: Try general hierarchical search with log keywords
            print(f"   🔄 No typed logs found, trying general hierarchical search...")
            results = controller.search_pages(f"{query} log", limit=8)
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
        
        if not unique_results:
            print(f"✗ No log content found for query: '{query}'")
            return ""
        
        log_contents = []
        total_chars = 0
        max_chars = MAX_CHARS_LOG
        
        for result in unique_results:
            title = result['title']
            content = result['raw_content']
            page_type = result.get('page_type', 'unknown')
            print(f"   📄 Processing {page_type}: '{title}' ({len(content)} chars)")
            
            # Parse character speaking patterns in the log
            parsed_content = parse_log_characters(content)
            
            # Format the log with title and parsed content
            formatted_log = f"**{title}**\n{parsed_content}"
            
            # Debug: Show first 50 chars of the formatted log
            formatted_preview = formatted_log[:100].replace('\n', ' ') + "..." if len(formatted_log) > 100 else formatted_log.replace('\n', ' ')
            print(f"   📝 Formatted log preview: '{formatted_preview}'")
            
            if total_chars + len(formatted_log) <= max_chars:
                log_contents.append(formatted_log)
                total_chars += len(formatted_log)
                print(f"   ✓ Added {page_type}: {title}")
            else:
                # Add partial content if it fits
                remaining_chars = max_chars - total_chars
                if remaining_chars > 500:  # Only add if substantial content fits
                    truncated_log = formatted_log[:remaining_chars] + "...[LOG TRUNCATED]"
                    log_contents.append(truncated_log)
                    print(f"   ✓ Added truncated {page_type}: {title}")
                break
        
        final_content = '\n\n---LOG SEPARATOR---\n\n'.join(log_contents)
        print(f"✅ HIERARCHICAL LOG SEARCH COMPLETE: {len(final_content)} characters from {len(log_contents)} logs")
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting log content: {e}")
        return ""

def get_relevant_wiki_context(query: str, max_chars: int = MAX_CHARS_CONTEXT) -> str:
    """Get relevant wiki content using hierarchical search (titles first, then content)"""
    try:
        controller = get_db_controller()
        
        # Check if this is a log query - handle with hierarchical log retrieval
        if is_log_query(query):
            log_content = get_log_content(query)
            if log_content:
                print(f"✓ Log query detected, retrieved {len(log_content)} chars of log content")
                return log_content
            else:
                print("⚠️  Log query detected but no log content found")
        
        # Use hierarchical database search for better results
        print(f"🔍 HIERARCHICAL WIKI SEARCH: '{query}'")
        results = controller.search_pages(query, limit=10)
        
        if not results:
            print(f"✗ No wiki content found for query: {query}")
            return ""
        
        print(f"   📊 Hierarchical search returned {len(results)} results")
        
        context_parts = []
        total_chars = 0
        
        for result in results:
            title = result['title']
            content = result['raw_content'][:30000]  # Limit individual content
            
            page_text = f"**{title}**\n{content}"
            
            if total_chars + len(page_text) <= max_chars:
                context_parts.append(page_text)
                total_chars += len(page_text)
            else:
                # Add partial content if it fits
                remaining_chars = max_chars - total_chars
                if remaining_chars > 100:
                    context_parts.append(page_text[:remaining_chars] + "...")
                break
        
        final_context = '\n\n---\n\n'.join(context_parts)
        print(f"✅ HIERARCHICAL WIKI SEARCH COMPLETE: {len(final_context)} characters from {len(context_parts)} pages")
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
        total_chars = 0
        max_chars = MAX_CHARS_CONTEXT
        
        for result in results:
            title = result['title']
            content = result['raw_content']
            
            page_text = f"**{title}**\n{content[:800]}"  # Limit individual entries
            
            if total_chars + len(page_text) <= max_chars:
                ship_info.append(page_text)
                total_chars += len(page_text)
            else:
                remaining_chars = max_chars - total_chars
                if remaining_chars > 100:
                    ship_info.append(page_text[:remaining_chars] + "...")
                break
        
        return '\n\n---\n\n'.join(ship_info)
        
    except Exception as e:
        print(f"✗ Error getting ship information: {e}")
        return ""

def get_recent_logs(ship_name: Optional[str] = None, limit: int = 5) -> str:
    """Get recent mission logs"""
    try:
        controller = get_db_controller()
        results = controller.get_recent_logs(ship_name=ship_name, limit=limit)
        
        if not results:
            return ""
        
        log_summaries = []
        for result in results:
            title = result['title']
            content = result['content'][:300]  # Brief summary
            log_date = result['log_date']
            
            log_summaries.append(f"**{title}** ({log_date})\n{content}...")
        
        return '\n\n---\n\n'.join(log_summaries)
        
    except Exception as e:
        print(f"✗ Error getting recent logs: {e}")
        return ""

def search_by_type(query: str, content_type: str) -> str:
    """Search for specific type of content"""
    try:
        controller = get_db_controller()
        results = controller.search_pages(query, page_type=content_type, limit=5)
        
        if not results:
            return ""
        
        search_results = []
        total_chars = 0
        max_chars = MAX_CHARS_CONTEXT
        
        for result in results:
            title = result['title']
            content = result['raw_content']
            
            page_text = f"**{title}**\n{content[:600]}"
            
            if total_chars + len(page_text) <= max_chars:
                search_results.append(page_text)
                total_chars += len(page_text)
            else:
                remaining_chars = max_chars - total_chars
                if remaining_chars > 100:
                    search_results.append(page_text[:remaining_chars] + "...")
                break
        
        return '\n\n---\n\n'.join(search_results)
        
    except Exception as e:
        print(f"✗ Error searching by type: {e}")
        return ""

def get_tell_me_about_content(subject: str) -> str:
    """Enhanced 'tell me about' functionality using hierarchical search"""
    try:
        controller = get_db_controller()
        print(f"🔍 HIERARCHICAL 'TELL ME ABOUT' SEARCH: '{subject}'")
        
        # Use hierarchical search - will search titles first, then content
        results = controller.search_pages(subject, limit=8)
        print(f"   📊 Hierarchical search returned {len(results)} results")
        
        # If it looks like a ship name, also search ship-specific content
        if any(ship in subject.lower() for ship in ['uss', 'ship', 'vessel']):
            print(f"   🚢 Ship detected, searching ship-specific content...")
            ship_results = controller.search_pages(subject, page_type='ship_info', limit=3)
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
        total_chars = 0
        max_chars = 5000  # Higher limit for "tell me about" queries
        
        for result in results[:5]:  # Top 5 results
            title = result['title']
            content = result['raw_content']
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
            
            if total_chars + len(page_text) <= max_chars:
                content_parts.append(page_text)
                total_chars += len(page_text)
            else:
                remaining_chars = max_chars - total_chars
                if remaining_chars > 200:
                    content_parts.append(page_text[:remaining_chars] + "...[CONTENT TRUNCATED]")
                break
        
        final_content = '\n\n---\n\n'.join(content_parts)
        print(f"✅ HIERARCHICAL 'TELL ME ABOUT' COMPLETE: {len(final_content)} characters from {len(content_parts)} sources")
        return final_content
        
    except Exception as e:
        print(f"✗ Error getting 'tell me about' content: {e}")
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
            print(f"  Content (50 chars): '{result['content'][:50]}...'")
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