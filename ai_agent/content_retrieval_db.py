"""Database-driven content retrieval and wiki search functionality"""

from database_controller import get_db_controller
from config import MAX_CHARS_LOG, MAX_CHARS_CONTEXT
from log_processor import is_log_query
from typing import Optional

def load_fleet_wiki_content():
    """Test connection to the elsiebrain database"""
    try:
        print("🚀 Connecting to elsiebrain database...")
        controller = get_db_controller()
        
        # Get stats to confirm connection and data availability
        stats = controller.get_stats()
        
        if stats.get('total_pages', 0) > 0:
            print(f"✓ elsiebrain database ready: {stats.get('total_pages', 0)} pages, {stats.get('mission_logs', 0)} logs")
        else:
            print("⚠️  elsiebrain database is connected but empty - needs to be populated externally")
        
        return True
        
    except Exception as e:
        print(f"✗ Error connecting to elsiebrain database: {e}")
        print("   Make sure the elsiebrain database exists and is populated")
        return False

def get_log_content(query: str) -> str:
    """Get full log content for summarization with better database queries"""
    try:
        controller = get_db_controller()
        return controller.get_log_content(query, max_chars=MAX_CHARS_LOG)
        
    except Exception as e:
        print(f"✗ Error getting log content: {e}")
        return ""

def get_relevant_wiki_context(query: str, max_chars: int = MAX_CHARS_CONTEXT) -> str:
    """Get relevant wiki content based on query using database search"""
    try:
        controller = get_db_controller()
        
        # Check if this is a log query - handle differently
        if is_log_query(query):
            return get_log_content(query)
        
        # Use database search for better results
        return controller.get_relevant_context(query, max_chars=max_chars)
        
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
            content = result['content']
            
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
            content = result['content']
            
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
    """Enhanced 'tell me about' functionality with better database queries"""
    try:
        controller = get_db_controller()
        
        # Try different search strategies
        results = []
        
        # 1. Direct title search (highest priority)
        title_results = controller.search_pages(f'"{subject}"', limit=3)
        results.extend(title_results)
        
        # 2. General content search
        if len(results) < 3:
            content_results = controller.search_pages(subject, limit=5)
            # Add results that aren't already included
            existing_ids = {r['id'] for r in results}
            results.extend([r for r in content_results if r['id'] not in existing_ids])
        
        # 3. If it looks like a ship name, prioritize ship-related content
        if any(ship in subject.lower() for ship in ['uss', 'ship', 'vessel']):
            ship_results = controller.search_pages(subject, page_type='ship_info', limit=3)
            # Prioritize ship info
            existing_ids = {r['id'] for r in results}
            ship_results = [r for r in ship_results if r['id'] not in existing_ids]
            results = ship_results + results
        
        if not results:
            return ""
        
        # Format the results
        content_parts = []
        total_chars = 0
        max_chars = 5000  # Higher limit for "tell me about" queries
        
        for result in results[:5]:  # Top 5 results
            title = result['title']
            content = result['content']
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
        
        return '\n\n---\n\n'.join(content_parts)
        
    except Exception as e:
        print(f"✗ Error getting 'tell me about' content: {e}")
        return ""

# Legacy support - backup fandom search (keep the existing function)
def search_fandom_wiki(query: str) -> str:
    """Search the 22nd Mobile Daedalus Fleet fandom wiki as backup option"""
    # This can remain the same as the original implementation
    # for now as a fallback option
    return "" 