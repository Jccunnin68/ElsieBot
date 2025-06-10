"""Content retrieval and wiki search functionality"""

import os
import fandom
from config import SHIP_NAMES, ACTIVITY_KEYWORDS, MAX_CHARS_LOG, MAX_CHARS_CONTEXT
from log_processor import is_log_query, is_ship_log_page, parse_log_characters
from date_utils import mask_log_title_dates

# Global variable to store fleet wiki content
fleet_wiki_content = ""
fleet_wiki_pages = []

def load_fleet_wiki_content():
    """Load the fleet wiki content into memory at startup"""
    global fleet_wiki_content, fleet_wiki_pages
    
    wiki_file_path = "fleet_wiki_content.txt"
    
    try:
        if os.path.exists(wiki_file_path):
            with open(wiki_file_path, 'r', encoding='utf-8') as f:
                fleet_wiki_content = f.read()
            
            # Parse into structured pages for easier access
            pages = fleet_wiki_content.split('=' * 80)
            fleet_wiki_pages = []
            
            for page in pages:
                if not page.strip():
                    continue
                    
                lines = page.split('\n')
                page_data = {
                    'title': '',
                    'content': '',
                    'raw': page
                }
                
                # Extract title and content
                content_lines = []
                in_content = False
                
                # Check if this page has a PAGE header
                has_page_header = any(line.startswith('PAGE:') for line in lines)
                
                if has_page_header:
                    for line in lines:
                        if line.startswith('PAGE:'):
                            page_data['title'] = line.replace('PAGE:', '').strip()
                            in_content = True
                        elif line.startswith('END OF PAGE:'):
                            break
                        elif in_content and not line.startswith(('URL:', 'CRAWLED:', '=' * 80)):
                            content_lines.append(line)
                else:
                    # Page without header - find title from content
                    for line in lines:
                        if line.strip() and line.startswith('**') and line.endswith('**'):
                            page_data['title'] = line.strip('*').strip()
                            break
                    
                    # Include all content
                    for line in lines:
                        if line.startswith('END OF PAGE:'):
                            break
                        elif not line.startswith(('URL:', 'CRAWLED:', '=' * 80)) or line.strip():
                            content_lines.append(line)
                
                page_data['content'] = '\n'.join(content_lines).strip()
                
                if page_data['title'] or len(page_data['content']) > 50:
                    fleet_wiki_pages.append(page_data)
            
            print(f"✓ Loaded fleet wiki: {len(fleet_wiki_content)} characters, {len(fleet_wiki_pages)} pages")
            return True
            
    except Exception as e:
        print(f"✗ Error loading fleet wiki: {e}")
        return False
    
    print("✗ Fleet wiki file not found")
    return False

def get_log_content(query: str) -> str:
    """Get full log content for summarization with character parsing"""
    global fleet_wiki_pages
    
    if not fleet_wiki_pages:
        return ""
    
    query_lower = query.lower()
    query_terms = query_lower.split()
    
    # Find log pages - prioritize pages with "log" in title and ship date patterns
    log_pages = []
    
    for page in fleet_wiki_pages:
        page_title_lower = page['title'].lower()
        page_content_lower = page['content'].lower()
        
        # Check if it's a log page (traditional log patterns or ship date patterns)
        is_traditional_log = any(log_word in page_title_lower for log_word in ['log', 'entry', 'stardate'])
        is_ship_date_log = is_ship_log_page(page['title'])
        
        if is_traditional_log or is_ship_date_log:
            score = 0
            
            # Give higher score to ship date logs if query mentions a ship name
            if is_ship_date_log:
                for ship in SHIP_NAMES:
                    if ship in query_lower and ship in page_title_lower:
                        score += 15  # High score for ship name match
                        break
                else:
                    # Even if no ship name in query, ship date logs are still relevant
                    score += 5
            
            # Exact query match gets highest score
            if query_lower in page_content_lower:
                score += 10
            
            # Title matches get high score
            if any(term in page_title_lower for term in query_terms):
                score += 8
            
            # Count individual term matches
            term_matches = sum(1 for term in query_terms if term in page_content_lower)
            score += term_matches
            
            if score > 0:
                log_pages.append((score, page))
    
    # Sort by score and return full content of top matches
    log_pages.sort(key=lambda x: x[0], reverse=True)
    
    if log_pages:
        # Return full content of the most relevant log(s) with character parsing
        log_contents = []
        total_chars = 0
        
        for score, page in log_pages[:3]:  # Top 3 most relevant logs
            if total_chars >= MAX_CHARS_LOG:
                break
                
            # Parse the log content for character context
            parsed_content = parse_log_characters(page['content'])
            
            # Mask the date in the title to show universe date
            masked_title = mask_log_title_dates(page['title'])
            full_log = f"**{masked_title}**\n{parsed_content}"
            
            if total_chars + len(full_log) <= MAX_CHARS_LOG:
                log_contents.append(full_log)
                total_chars += len(full_log)
            else:
                # Add what we can fit
                remaining_chars = MAX_CHARS_LOG - total_chars
                if remaining_chars > 200:  # Only add if we have substantial space
                    log_contents.append(full_log[:remaining_chars] + "...[LOG TRUNCATED]")
                break
        
        return '\n\n---\n\n'.join(log_contents)
    
    return ""

def get_relevant_wiki_context(query: str, max_chars: int = MAX_CHARS_CONTEXT) -> str:
    """Get relevant wiki content based on query, limited by character count"""
    global fleet_wiki_pages
    
    if not fleet_wiki_pages:
        return ""
    
    # Check if this is a log query or mentions ship logs - handle differently
    if is_log_query(query):
        return get_log_content(query)
    
    # Check if query is asking about a specific ship's activities (which would be in ship logs)
    query_lower = query.lower()
    
    mentions_ship = any(ship in query_lower for ship in SHIP_NAMES)
    mentions_activities = any(keyword in query_lower for keyword in ACTIVITY_KEYWORDS)
    
    if mentions_ship and mentions_activities:
        return get_log_content(query)
    
    query_terms = query_lower.split()
    
    # Score pages by relevance
    scored_pages = []
    
    for page in fleet_wiki_pages:
        score = 0
        page_content_lower = (page['title'] + ' ' + page['content']).lower()
        
        # Exact query match gets highest score
        if query_lower in page_content_lower:
            score += 10
        
        # Title matches get high score
        if query_lower in page['title'].lower():
            score += 8
        
        # Count individual term matches
        term_matches = sum(1 for term in query_terms if term in page_content_lower)
        score += term_matches * 2
        
        # Bonus for USS Stardancer related content
        if any(keyword in page_content_lower for keyword in ['stardancer', 'blaine', 'crew', 'ship']):
            score += 1
        
        if score > 0:
            scored_pages.append((score, page))
    
    # Sort by score (highest first) and build context
    scored_pages.sort(key=lambda x: x[0], reverse=True)
    
    context_parts = []
    total_chars = 0
    
    for score, page in scored_pages:
        if total_chars >= max_chars:
            break
            
        # Mask dates in titles if they're ship logs
        display_title = mask_log_title_dates(page['title']) if is_ship_log_page(page['title']) else page['title']
        page_text = f"**{display_title}**\n{page['content'][:1000]}"  # Limit each page to 1000 chars
        
        if total_chars + len(page_text) <= max_chars:
            context_parts.append(page_text)
            total_chars += len(page_text)
        else:
            # Add partial content if it fits
            remaining_chars = max_chars - total_chars
            if remaining_chars > 100:  # Only add if we have substantial space
                context_parts.append(page_text[:remaining_chars] + "...")
            break
    
    return '\n\n---\n\n'.join(context_parts)

def search_fandom_wiki(query: str) -> str:
    """Search the 22nd Mobile Daedalus Fleet fandom wiki as backup option"""
    
    try:
        # Set the wiki to the 22nd Mobile Daedalus Fleet
        fandom.set_wiki("22ndmobile")
        
        # Search for pages related to the query
        search_results = fandom.search(query, results=3)
        
        if not search_results:
            return ""
        
        # Get content from the most relevant result
        try:
            page = fandom.page(search_results[0])
            
            # Get summary or first few paragraphs
            content = page.summary
            if not content and hasattr(page, 'content'):
                # If no summary, get first 500 chars of content
                content = page.content[:500] + "..." if len(page.content) > 500 else page.content
            
            if content:
                return f"**{page.title}** (from Fleet Wiki)\n\n{content}"
                
        except Exception as page_error:
            print(f"Error getting fandom page content: {page_error}")
            # Return just the search result title if we can't get content
            return f"Found reference to: {search_results[0]}"
            
    except Exception as e:
        print(f"Error searching fandom wiki: {e}")
    
    return "" 