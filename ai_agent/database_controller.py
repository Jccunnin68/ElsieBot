"""Database controller for fleet wiki content using PostgreSQL - Read-only interface"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime

class FleetDatabaseController:
    def __init__(self, 
                 db_name=None, 
                 db_user=None, 
                 db_password=None, 
                 db_host=None, 
                 db_port=None):
        self.db_config = {
            'dbname': db_name or os.getenv('DB_NAME', 'elsiebrain'),
            'user': db_user or os.getenv('DB_USER', 'elsie'),
            'password': db_password or os.getenv('DB_PASSWORD', 'elsie123'),
            'host': db_host or os.getenv('DB_HOST', 'localhost'),
            'port': db_port or os.getenv('DB_PORT', '5432')
        }
        self.ensure_connection()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def _generate_query_variations(self, query: str) -> List[str]:
        """Generate query variations for better matching"""
        query_variations = [query]
        query_lower = query.lower()
        
        # Common word variations for better matching
        word_variations = {
            # Singular/Plural variations
            'log': 'logs',
            'logs': 'log',
            'ship': 'ships',
            'ships': 'ship',
            'character': 'characters',
            'characters': 'character',
            'entry': 'entries',
            'entries': 'entry',
            'mission': 'missions',
            'missions': 'mission',
            'episode': 'episodes',
            'episodes': 'episode',
            'report': 'reports',
            'reports': 'report',
            
            # Common abbreviations and expansions
            'uss': 'united states ship',
            'united states ship': 'uss',
            'ncc': 'naval construction contract',
            'naval construction contract': 'ncc',
            'info': 'information',
            'information': 'info',
            'bio': 'biography',
            'biography': 'bio',
            'spec': 'specification',
            'specification': 'spec',
            'specs': 'specifications',
            'specifications': 'specs',
        }
        
        # Generate variations by replacing words
        for original_word, replacement_word in word_variations.items():
            if original_word in query_lower:
                # Check if we should replace (avoid replacing if both forms exist)
                if replacement_word not in query_lower:
                    variation = query_lower.replace(original_word, replacement_word)
                    query_variations.append(variation)
        
        # Add partial word matching for ship names and common terms
        query_words = query_lower.split()
        if len(query_words) > 1:
            # Try individual words for better partial matching
            for word in query_words:
                if len(word) > 3:  # Only add meaningful words
                    query_variations.append(word)
        
        # Remove duplicates while preserving order
        query_variations = list(dict.fromkeys(query_variations))
        
        return query_variations
    
    def ensure_connection(self):
        """Ensure database connection is working"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    print("✓ Connected to elsiebrain database successfully")
        except Exception as e:
            print(f"✗ Error connecting to elsiebrain database: {e}")
            print(f"  Make sure the elsiebrain database exists and is accessible")
    
    def log_search_results(self, results: List[Dict], operation: str, debug_level: int = 1) -> None:
        """
        Log detailed search results for debugging.
        
        Args:
            results: List of database results to log
            operation: Description of the operation being performed
            debug_level: Level of detail (1=summary, 2=detailed, 3=full content)
        """
        if not results:
            print(f"   📊 {operation}: No results found")
            return
            
        print(f"   📊 {operation}: {len(results)} results")
        
        if debug_level >= 2:
            print(f"   📋 DETAILED RESULTS:")
            for i, result in enumerate(results[:10], 1):  # Show first 10 results
                title = result.get('title', 'Unknown Title')
                categories = result.get('categories', [])
                            # Extract ship name from title or categories since ship_name column doesn't exist
                ship_name = self._extract_ship_from_title_or_categories(result)
                record_date = result.get('id', 'Unknown ID')  # Use ID as proxy for date ordering
                content_length = len(result.get('raw_content', ''))
                record_id = result.get('id', 'Unknown ID')
                
                # Format categories nicely
                category_str = ', '.join(categories) if categories else 'None'
                
                print(f"      {i}. ID={record_id}: '{title[:60]}{'...' if len(title) > 60 else ''}'")
                print(f"         Ship: {ship_name} | Record ID: {record_date} | Size: {content_length} chars")
                print(f"         Categories: [{category_str}]")
                
                if debug_level >= 3:
                    # Show content preview
                    content = result.get('raw_content', '')
                    content_preview = content[:200].replace('\n', ' ') + ('...' if len(content) > 200 else '')
                    print(f"         Content: {content_preview}")
                
                print()
            
            if len(results) > 10:
                print(f"      ... and {len(results) - 10} more results")

    def _extract_ship_from_title_or_categories(self, result: Dict) -> str:
        """Extract ship name from title or categories since ship_name column doesn't exist"""
        title = result.get('title', '').lower()
        categories = result.get('categories', [])
        
        # Check for ship names in title
        ships = ['stardancer', 'adagio', 'pilgrim', 'sentinel', 'banshee', 'protector', 'manta', 'gigantes']
        for ship in ships:
            if ship in title:
                return ship.title()
        
        # Check for ship names in categories
        if categories:
            for category in categories:
                category_lower = category.lower()
                for ship in ships:
                    if ship in category_lower:
                        return ship.title()
        
        return 'Unknown Ship'

    def search_pages(self, query: str, page_type: Optional[str] = None, 
                    ship_name: Optional[str] = None, limit: int = 10, 
                    force_mission_logs_only: bool = False, categories: Optional[List[str]] = None,
                    debug_level: int = 1) -> List[Dict]:
        """Enhanced search with category support, backward compatibility, and detailed debug logging"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    print(f"🔍 ENHANCED SEARCH - Query: '{query}' (force_mission_logs_only: {force_mission_logs_only}, debug_level: {debug_level})")
                    
                    # Generate query variations for better matching
                    query_variations = self._generate_query_variations(query)
                    print(f"   📝 Query variations (enhanced): {query_variations}")
                    
                    # Override for mission logs only - use database query instead of artificial mappings
                    if force_mission_logs_only:
                        categories = self._get_actual_log_categories_from_db()
                        print(f"   🎯 FORCING MISSION LOGS ONLY - using actual database log categories: {len(categories)} categories")
                    
                    all_results = []
                    
                    # STEP 1: Direct ship name matches (highest priority)
                    if not ship_name and any(ship in query.lower() for ship in ['stardancer', 'adagio', 'pilgrim', 'sentinel', 'banshee', 'protector', 'manta', 'gigantes']):
                        print(f"   🚢 Ship name detected in query, searching ship-specific logs...")
                        
                        # Extract ship name from query
                        detected_ship = None
                        for ship in ['stardancer', 'adagio', 'pilgrim', 'sentinel', 'banshee', 'protector', 'manta', 'gigantes']:
                            if ship in query.lower():
                                detected_ship = ship
                                break
                        
                        if detected_ship:
                            # Search by ship name in title instead of ship_name column
                            ship_query = """
                                SELECT id, title, raw_content, url, categories
                                FROM wiki_pages 
                                WHERE LOWER(title) LIKE %s
                                ORDER BY id DESC
                                LIMIT %s
                            """
                            cur.execute(ship_query, [f'%{detected_ship}%', limit])
                            ship_results = [dict(row) for row in cur.fetchall()]
                            self.log_search_results(ship_results, f"Ship-specific search for {detected_ship}", debug_level)
                            all_results.extend(ship_results)
                    
                    # STEP 2: Category-based search (PRIMARY)
                    if categories and len(all_results) < limit:
                        print(f"   🏷️ Category-based search for: {categories}")
                        
                        # Safety check: ensure categories is not empty
                        if not categories or len(categories) == 0:
                            print(f"   ⚠️  Empty categories array, skipping category search")
                        else:
                            category_query = """
                                SELECT id, title, raw_content, url, categories,
                                       CASE 
                                           WHEN to_tsvector('english', title) @@ plainto_tsquery('english', %s) THEN
                                               ts_rank(to_tsvector('english', title), plainto_tsquery('english', %s)) + 2.0
                                           WHEN LOWER(title) LIKE LOWER(%s) THEN 1.5
                                           ELSE 1.0
                                       END as rank
                                FROM wiki_pages 
                                WHERE categories IS NOT NULL 
                                AND array_length(categories, 1) > 0
                                AND categories && %s
                                AND (
                                    to_tsvector('english', title) @@ plainto_tsquery('english', %s) OR
                                    LOWER(title) LIKE LOWER(%s) OR
                                    LOWER(raw_content) LIKE LOWER(%s)
                                )
                            """
                            
                            # Use multiple query variations for better matching
                            like_patterns = [f'%{var}%' for var in query_variations]
                            like_condition = ' OR '.join(['LOWER(title) LIKE LOWER(%s)'] * len(like_patterns))
                            content_like_condition = ' OR '.join(['LOWER(raw_content) LIKE LOWER(%s)'] * len(like_patterns))
                            
                            category_query = f"""
                                SELECT id, title, raw_content, url, categories,
                                       CASE 
                                           WHEN to_tsvector('english', title) @@ plainto_tsquery('english', %s) THEN
                                               ts_rank(to_tsvector('english', title), plainto_tsquery('english', %s)) + 2.0
                                           WHEN ({like_condition}) THEN 1.5
                                           ELSE 1.0
                                       END as rank
                                FROM wiki_pages 
                                WHERE categories IS NOT NULL 
                                AND array_length(categories, 1) > 0
                                AND categories && %s
                                AND (
                                    to_tsvector('english', title) @@ plainto_tsquery('english', %s) OR
                                    ({like_condition}) OR
                                    ({content_like_condition})
                                )
                            """
                            
                            category_params = [query, query] + like_patterns + [categories, query] + like_patterns + like_patterns
                            
                            if ship_name:
                                category_query += " AND LOWER(title) LIKE %s"
                                category_params.append(f'%{ship_name.lower()}%')
                            
                            # Exclude already found results
                            if all_results:
                                existing_ids = [str(r['id']) for r in all_results]
                                category_query += f" AND id NOT IN ({','.join(['%s'] * len(existing_ids))})"
                                category_params.extend(existing_ids)
                            
                            remaining_limit = limit - len(all_results)
                            category_query += " ORDER BY rank DESC, id DESC LIMIT %s"
                            category_params.append(remaining_limit)
                            
                            cur.execute(category_query, category_params)
                            category_results = [dict(row) for row in cur.fetchall()]
                            self.log_search_results(category_results, "Category-based search", debug_level)
                            all_results.extend(category_results)
                    
                    # STEP 3: Enhanced Title Search (FTS + LIKE for better matching)
                    if len(all_results) < limit:
                        print(f"   🔍 Enhanced title search (FTS + LIKE)...")
                        
                        # Enhanced title search with query variations
                        like_patterns = [f'%{var}%' for var in query_variations]
                        like_condition = ' OR '.join(['LOWER(title) LIKE LOWER(%s)'] * len(like_patterns))
                        
                        title_query = f"""
                            SELECT id, title, raw_content, url, categories,
                                   CASE 
                                       WHEN to_tsvector('english', title) @@ plainto_tsquery('english', %s) THEN
                                           ts_rank(to_tsvector('english', title), plainto_tsquery('english', %s)) + 1.0
                                       ELSE 0.5
                                   END as rank
                            FROM wiki_pages 
                            WHERE (
                                to_tsvector('english', title) @@ plainto_tsquery('english', %s) OR
                                ({like_condition})
                            )
                        """
                        
                        title_params = [query, query, query] + like_patterns
                        
                        # Use categories if available
                        if categories:
                            # Safety check: ensure categories is not empty
                            if categories and len(categories) > 0:
                                title_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                                title_params.append(categories)
                        
                        if ship_name:
                            title_query += " AND LOWER(title) LIKE %s"
                            title_params.append(f'%{ship_name.lower()}%')
                        
                        # Exclude already found ship results
                        if all_results:
                            existing_ids = [str(r['id']) for r in all_results]
                            title_query += f" AND id NOT IN ({','.join(['%s'] * len(existing_ids))})"
                            title_params.extend(existing_ids)
                        
                        remaining_limit = limit - len(all_results)
                        title_query += " ORDER BY rank DESC, id DESC LIMIT %s"
                        title_params.append(remaining_limit)
                        
                        cur.execute(title_query, title_params)
                        title_results = [dict(row) for row in cur.fetchall()]
                        self.log_search_results(title_results, "Title FTS search", debug_level)
                        all_results.extend(title_results)
                    
                    # STEP 4: Content-based search if still need more results
                    if len(all_results) < limit:
                        print(f"   🔍 Content FTS search...")
                        content_query = """
                            SELECT id, title, raw_content, url, categories,
                                   ts_rank(to_tsvector('english', raw_content), 
                                          plainto_tsquery('english', %s)) as rank
                            FROM wiki_pages 
                            WHERE to_tsvector('english', raw_content) @@ plainto_tsquery('english', %s)
                        """
                        
                        content_params = [query, query]
                        
                        # Use categories if available
                        if categories:
                            # Safety check: ensure categories is not empty
                            if categories and len(categories) > 0:
                                content_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                                content_params.append(categories)
                        
                        if ship_name:
                            content_query += " AND LOWER(title) LIKE %s"
                            content_params.append(f'%{ship_name.lower()}%')
                        
                        # Exclude already found results
                        if all_results:
                            existing_ids = [str(r['id']) for r in all_results]
                            content_query += f" AND id NOT IN ({','.join(['%s'] * len(existing_ids))})"
                            content_params.extend(existing_ids)
                        
                        remaining_limit = limit - len(all_results)
                        content_query += " ORDER BY rank DESC, id DESC LIMIT %s"
                        content_params.append(remaining_limit)
                        
                        cur.execute(content_query, content_params)
                        content_results = [dict(row) for row in cur.fetchall()]
                        self.log_search_results(content_results, "Content FTS search", debug_level)
                        all_results.extend(content_results)
                    
                    # STEP 5: Enhanced Fallback LIKE search with query variations
                    if not all_results:
                        print(f"   🔄 Enhanced fallback LIKE search with variations...")
                        
                        # Build flexible LIKE conditions with all query variations
                        like_patterns = [f'%{var}%' for var in query_variations]
                        title_like_condition = ' OR '.join(['LOWER(title) LIKE LOWER(%s)'] * len(like_patterns))
                        content_like_condition = ' OR '.join(['LOWER(raw_content) LIKE LOWER(%s)'] * len(like_patterns))
                        
                        like_query = f"""
                            SELECT id, title, raw_content, url, categories
                            FROM wiki_pages 
                            WHERE (({title_like_condition}) OR ({content_like_condition}))
                        """
                        
                        like_params = like_patterns + like_patterns
                        
                        # Use categories if available
                        if categories:
                            # Safety check: ensure categories is not empty
                            if categories and len(categories) > 0:
                                like_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                                like_params.append(categories)
                        
                        if ship_name:
                            like_query += " AND LOWER(title) LIKE %s"
                            like_params.append(f'%{ship_name.lower()}%')
                        
                        like_query += " ORDER BY id DESC LIMIT %s"
                        like_params.append(limit)
                        
                        cur.execute(like_query, like_params)
                        like_results = [dict(row) for row in cur.fetchall()]
                        self.log_search_results(like_results, "LIKE fallback search", debug_level)
                        all_results.extend(like_results)
                    
                    # Remove duplicates and limit results
                    seen_ids = set()
                    unique_results = []
                    for result in all_results:
                        if result['id'] not in seen_ids:
                            unique_results.append(result)
                            seen_ids.add(result['id'])
                            if len(unique_results) >= limit:
                                break
                    
                    print(f"✅ ENHANCED SEARCH COMPLETE: {len(unique_results)} unique results")
                    
                    # Final detailed debug output
                    if debug_level >= 2:
                        self.log_search_results(unique_results, "FINAL UNIQUE RESULTS", debug_level)
                    
                    # Track content access for all returned results
                    if unique_results:
                        page_ids = [result['id'] for result in unique_results]
                        self.update_content_accessed(page_ids)
                    
                    return unique_results
                    
        except Exception as e:
            print(f"✗ Error in enhanced search: {e}")
            return []
    
    def get_log_content(self, query: str) -> str:
        """Get mission log content for a query (no truncation)"""
        # Search specifically for mission logs
        results = self.search_pages(query, page_type="mission_log", limit=20)  # Increased limit
        
        if not results:
            return ""
        
        log_contents = []
        
        for result in results:
            title = result['title']
            content = result['raw_content']
            
            # Format the log - full content, no truncation
            formatted_log = f"**{title}**\n{content}"
            log_contents.append(formatted_log)
        
        return '\n\n---\n\n'.join(log_contents)
    
    def get_relevant_context(self, query: str) -> str:
        """Get relevant wiki context for general queries (no truncation)"""
        results = self.search_pages(query, limit=20)  # Increased limit
        
        if not results:
            return ""
        
        context_parts = []
        
        for result in results:
            title = result['title']
            content = result['raw_content']  # Full content, no individual limits
            
            page_text = f"**{title}**\n{content}"
            context_parts.append(page_text)
        
        return '\n\n---\n\n'.join(context_parts)
    
    def get_ship_info(self, ship_name: str) -> List[Dict]:
        """Get all information about a specific ship"""
        return self.search_pages(ship_name, ship_name=ship_name.lower(), limit=20)
    
    def get_recent_logs(self, ship_name: Optional[str] = None, limit: int = 10, debug_level: int = 1) -> List[Dict]:
        """
        Get recent mission logs using chronological sorting when possible.
        Falls back to ID-based ordering if chronological sorting fails.
        """
        try:
            print(f"📅 GET_RECENT_LOGS: ship='{ship_name}', limit={limit}")
            
            # For ship-specific logs, try chronological sorting first
            if ship_name:
                # Get actual database log categories
                log_categories = self._get_actual_log_categories_from_db()
                
                if log_categories:
                    print(f"   📊 Attempting chronological sort with categories: {log_categories}")
                    chronological_results = self._get_logs_sorted_by_title_date(
                        ship_name=ship_name, 
                        categories=log_categories, 
                        limit=limit,
                        debug_level=debug_level
                    )
                    if chronological_results:
                        print(f"   ✅ Using chronological sort: {len(chronological_results)} results")
                        # Track content access for returned logs
                        page_ids = [result['id'] for result in chronological_results]
                        self.update_content_accessed(page_ids)
                        return chronological_results
                    else:
                        print(f"   ⚠️  Chronological sort returned no results, falling back to ID order")
            
            # Fallback to original ID-based ordering
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Use actual database log categories instead of artificial mappings
                    log_categories = self._get_actual_log_categories_from_db()
                    
                    # Safety check: ensure log_categories is not empty
                    if not log_categories or len(log_categories) == 0:
                        print(f"   ⚠️  No log categories found, falling back to page_type")
                        query = """
                            SELECT id, title, raw_content, url, categories
                            FROM wiki_pages 
                            WHERE page_type = 'mission_log'
                        """
                        params = []
                    else:
                        print(f"   📊 Using dynamic log categories: {log_categories}")
                        query = """
                            SELECT id, title, raw_content, url, categories
                            FROM wiki_pages 
                            WHERE categories IS NOT NULL 
                            AND array_length(categories, 1) > 0
                            AND categories && %s
                        """
                        params = [log_categories]
                    
                    if ship_name:
                        query += " AND LOWER(title) LIKE %s"
                        params.append(f'%{ship_name.lower()}%')
                    
                    query += " ORDER BY id DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   📋 Fallback ID-based sort returned {len(results)} results")
                    
                    # Enhanced debug logging
                    self.log_search_results(results, f"Recent logs search (ship: {ship_name})", debug_level)
                    
                    # Track content access for returned logs
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    return results
                    
        except Exception as e:
            print(f"✗ Error getting recent logs: {e}")
            return []

    def get_selected_logs(self, selection_type: str, ship_name: Optional[str] = None, 
                         limit: int = 5, date_filter: Optional[str] = None, debug_level: int = 1) -> List[Dict]:
        """
        Get logs based on selection criteria with proper ordering and filtering
        Now uses dynamic log category filtering instead of hardcoded categories
        
        Args:
            selection_type: 'latest', 'first', 'random', 'today', etc.
            ship_name: Optional ship filter
            limit: Number of results (1 for random selection)
            date_filter: Optional date range filter
        """
        try:
            print(f"🎯 SELECTED LOG SEARCH: type='{selection_type}', ship='{ship_name}', limit={limit}")
            
            # Get actual database log categories
            log_categories = self._get_actual_log_categories_from_db()
            
            # ENHANCED: Use chronological sorting for temporal selections
            if ship_name and log_categories and selection_type in ['first', 'earliest', 'oldest', 'latest', 'recent']:
                print(f"   📅 Attempting chronological selection for '{selection_type}' logs")
                
                # Get chronologically sorted logs
                chronological_results = self._get_logs_sorted_by_title_date(
                    ship_name=ship_name, 
                    categories=log_categories, 
                    limit=50,  # Get more results to ensure we have earliest logs
                    debug_level=debug_level
                )
                
                if chronological_results:
                    if selection_type in ['first', 'earliest', 'oldest']:
                        # For first/earliest, reverse the order to get oldest first
                        chronological_results.reverse()
                        result = chronological_results[:limit]
                        print(f"   ✅ Using chronological sort for EARLIEST: {len(result)} results")
                        print(f"      First log: {result[0]['title'] if result else 'None'}")
                    else:  # latest, recent
                        result = chronological_results[:limit]
                        print(f"   ✅ Using chronological sort for LATEST: {len(result)} results")
                        print(f"      Most recent log: {result[0]['title'] if result else 'None'}")
                    
                    # Track content access for returned logs
                    if result:
                        page_ids = [log['id'] for log in result]
                        self.update_content_accessed(page_ids)
                    
                    return result
                else:
                    print(f"   ⚠️  No chronological results found, falling back to ID-based ordering")
            
            # Fallback to standard ID-based ordering
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Safety check: ensure log_categories is not empty
                    if not log_categories or len(log_categories) == 0:
                        print(f"   ⚠️  No log categories found, falling back to page_type")
                        # Base query - ONLY mission logs using page_type fallback
                        query = """
                            SELECT id, title, raw_content, url, categories
                            FROM wiki_pages 
                            WHERE page_type = 'mission_log'
                        """
                        params = []
                    else:
                        print(f"   📊 Using dynamic log categories: {log_categories}")
                        # Base query - ONLY mission logs using dynamic categories
                        query = """
                            SELECT id, title, raw_content, url, categories
                            FROM wiki_pages 
                            WHERE categories IS NOT NULL 
                            AND array_length(categories, 1) > 0
                            AND categories && %s
                        """
                        params = [log_categories]
                    
                    # Add ship filter (search in title since ship_name column no longer exists)
                    if ship_name:
                        query += " AND LOWER(title) LIKE %s"
                        params.append(f'%{ship_name.lower()}%')
                    
                    # Note: Date-based filtering removed since log_date column no longer exists
                    # Log dates are now extracted from titles using chronological sorting
                    if selection_type in ['today', 'yesterday', 'this_week', 'last_week']:
                        print(f"   ⚠️ Date-based selection '{selection_type}' not supported without log_date column")
                        # Convert to 'latest' for now
                        selection_type = 'latest'
                    
                    # Add ordering based on selection type
                    if selection_type == 'random':
                        query += " ORDER BY RANDOM()"
                        limit = 1  # Random selection always returns 1
                    elif selection_type in ['latest', 'recent']:
                        query += " ORDER BY id DESC"
                    elif selection_type in ['first', 'earliest', 'oldest']:
                        query += " ORDER BY id ASC"
                    elif selection_type in ['today', 'yesterday', 'this_week', 'last_week']:
                        query += " ORDER BY id DESC"  # Most recent within date range
                    else:
                        # Default to recent
                        query += " ORDER BY id DESC"
                    
                    query += " LIMIT %s"
                    params.append(limit)
                    
                    print(f"   📊 Fallback: Executing ID-based query with {len(params)} parameters")
                    cur.execute(query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   ✅ Found {len(results)} selected logs (ID-based)")
                    
                    # Enhanced debug logging
                    self.log_search_results(results, f"Selected logs ({selection_type}, ship: {ship_name})", debug_level)
                    
                    # Track content access for returned logs
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    return results
                    
        except Exception as e:
            print(f"✗ Error getting selected logs: {e}")
            return []

    def get_random_log(self, ship_name: Optional[str] = None) -> Optional[Dict]:
        """Get one random mission log, optionally filtered by ship"""
        results = self.get_selected_logs('random', ship_name, limit=1)
        return results[0] if results else None
    
    def update_content_accessed(self, page_ids: List[int]) -> bool:
        """Update content_accessed counter for the given page IDs"""
        if not page_ids:
            return True
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Update content_accessed counter for all provided page IDs
                    cur.execute("""
                        UPDATE wiki_pages 
                        SET content_accessed = content_accessed + 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ANY(%s)
                    """, (page_ids,))
                    
                    updated_count = cur.rowcount
                    conn.commit()
                    
                    if updated_count > 0:
                        print(f"   📊 Updated content_accessed for {updated_count} pages")
                    
                    return True
                    
        except Exception as e:
            print(f"✗ Error updating content_accessed: {e}")
            return False

    def get_content_access_stats(self) -> List[Dict]:
        """Get content access statistics - most accessed pages"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT title, content_accessed, categories,
                               LEFT(raw_content, 100) as content_preview
                        FROM wiki_pages 
                        WHERE content_accessed > 0
                        ORDER BY content_accessed DESC, id ASC
                        LIMIT 20
                    """)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"✗ Error getting content access stats: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get database statistics with focus on categories"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Primary category-based stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_pages,
                            SUM(content_accessed) as total_accesses,
                            AVG(content_accessed) as avg_accesses_per_page,
                            COUNT(CASE WHEN categories IS NOT NULL AND array_length(categories, 1) > 0 THEN 1 END) as pages_with_categories,
                            COUNT(CASE WHEN categories IS NULL OR array_length(categories, 1) = 0 THEN 1 END) as pages_without_categories
                        FROM wiki_pages
                    """)
                    stats = dict(cur.fetchone())
                    
                    # Category-based stats (PRIMARY)
                    cur.execute("""
                        SELECT unnest(categories) as category, COUNT(*) as count 
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        GROUP BY unnest(categories) 
                        ORDER BY count DESC 
                        LIMIT 15
                    """)
                    category_stats = {row['category']: row['count'] for row in cur.fetchall()}
                    stats['category_breakdown'] = category_stats
                    
                    return stats
        except Exception as e:
            print(f"✗ Error getting stats: {e}")
            return {}

    def get_schema_info(self) -> Dict:
        """Get database schema information"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    print("🔍 QUERYING DATABASE SCHEMA")
                    print("=" * 50)
                    
                    # Get table structure
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable, column_default 
                        FROM information_schema.columns 
                        WHERE table_name = 'wiki_pages' 
                        ORDER BY ordinal_position
                    """)
                    columns = cur.fetchall()
                    
                    print("📋 WIKI_PAGES TABLE STRUCTURE:")
                    for col in columns:
                        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                        default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                        print(f"  - {col['column_name']}: {col['data_type']} {nullable}{default}")
                    
                    # Get sample data
                    print("\n📊 SAMPLE DATA (First 5 rows):")
                    cur.execute("""
                        SELECT id, title, categories,
                               LEFT(raw_content, 50) as content_preview,
                               log_date
                        FROM wiki_pages 
                        ORDER BY id 
                        LIMIT 5
                    """)
                    samples = cur.fetchall()
                    
                    for i, row in enumerate(samples, 1):
                        print(f"  Row {i}:")
                        print(f"    ID: {row['id']}")
                        print(f"    Title: '{row['title']}'")
                        print(f"    Categories: {row['categories']}")
                        print(f"    Content Preview: '{row['content_preview']}...'")
                        print()
                    
                    # Get page type distribution
                    print("📈 PAGE TYPE DISTRIBUTION:")
                    cur.execute("""
                        SELECT page_type, COUNT(*) as count 
                        FROM wiki_pages 
                        GROUP BY page_type 
                        ORDER BY count DESC
                    """)
                    types = cur.fetchall()
                    
                    for row in types:
                        print(f"  - {row['page_type']}: {row['count']} entries")
                    
                    # Look for Adagio entries specifically
                    print("\n🔍 ADAGIO ENTRIES:")
                    cur.execute("""
                        SELECT title, page_type, categories 
                        FROM wiki_pages 
                        WHERE LOWER(title) LIKE '%adagio%' 
                        ORDER BY title
                    """)
                    adagio_entries = cur.fetchall()
                    
                    for row in adagio_entries:
                        print(f"  - Title: '{row['title']}' | Categories: {row['categories']}")
                    
                    print("=" * 50)
                    
                    return {
                        'columns': [dict(col) for col in columns],
                        'samples': [dict(row) for row in samples], 
                        'types': [dict(row) for row in types],
                        'adagio_entries': [dict(row) for row in adagio_entries]
                    }
                    
        except Exception as e:
            print(f"✗ Error getting schema info: {e}")
            return {}

    def cleanup_mission_log_ship_names(self) -> Dict:
        """Extract ship names from mission log titles and update ship_name field"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    print("🧹 CLEANING UP MISSION LOG SHIP NAMES")
                    print("=" * 50)
                    
                    # First, let's see what we're working with - use categories instead of page_type
                    SHIP_LOG_CATEGORIES = self._get_actual_log_categories_from_db()
                    
                    # Safety check: ensure SHIP_LOG_CATEGORIES is not empty
                    if not SHIP_LOG_CATEGORIES or len(SHIP_LOG_CATEGORIES) == 0:
                        print(f"   ⚠️  No ship log categories defined, using page_type fallback")
                        cur.execute("""
                            SELECT COUNT(*) as total_mission_logs,
                                   COUNT(CASE WHEN ship_name IS NULL OR ship_name = '' THEN 1 END) as missing_ship_names
                            FROM wiki_pages 
                            WHERE page_type = 'mission_log'
                        """)
                    else:
                        cur.execute("""
                            SELECT COUNT(*) as total_mission_logs,
                                   COUNT(CASE WHEN ship_name IS NULL OR ship_name = '' THEN 1 END) as missing_ship_names
                            FROM wiki_pages 
                            WHERE categories IS NOT NULL 
                            AND array_length(categories, 1) > 0
                            AND categories && %s
                        """, (SHIP_LOG_CATEGORIES,))
                    stats_before = cur.fetchone()
                    print(f"📊 Before cleanup: {stats_before['total_mission_logs']} mission logs, {stats_before['missing_ship_names']} missing ship names")
                    
                    # Update ship names based on title patterns
                    ship_patterns = [
                        # Pattern: "Ship Name Date" (e.g., "Adagio 4/23/2022")
                        ("Adagio", r"^Adagio\s+\d"),
                        ("Stardancer", r"^Stardancer\s+\d"),
                        ("Pilgrim", r"^Pilgrim\s+\d"),
                        ("Protector", r"^Protector\s+\d"),
                        ("Manta", r"^Manta\s+\d"),
                        ("Sentinel", r"^Sentinel\s+\d"),
                        ("Caelian", r"^Caelian\s+\d"),
                        ("Enterprise", r"^Enterprise\s+\d"),
                        ("Montagnier", r"^Montagnier\s+\d"),
                        ("Faraday", r"^Faraday\s+\d"),
                        ("Cook", r"^Cook\s+\d"),
                        ("Mjolnir", r"^Mjolnir\s+\d"),
                        ("Rendino", r"^Rendino\s+\d"),
                        ("Gigantes", r"^Gigantes\s+\d"),
                        ("Banshee", r"^Banshee\s+\d"),
                        
                        # Pattern: "Date Ship Name Log" (e.g., "2024/09/29 Adagio Log")
                        ("Adagio", r"\d+[/-]\d+[/-]\d+\s+Adagio"),
                        ("Stardancer", r"\d+[/-]\d+[/-]\d+\s+Stardancer"),
                        ("Pilgrim", r"\d+[/-]\d+[/-]\d+\s+Pilgrim"),
                        ("Protector", r"\d+[/-]\d+[/-]\d+\s+Protector"),
                        ("Manta", r"\d+[/-]\d+[/-]\d+\s+Manta"),
                        ("Sentinel", r"\d+[/-]\d+[/-]\d+\s+Sentinel"),
                        ("Caelian", r"\d+[/-]\d+[/-]\d+\s+Caelian"),
                        ("Enterprise", r"\d+[/-]\d+[/-]\d+\s+Enterprise"),
                        ("Montagnier", r"\d+[/-]\d+[/-]\d+\s+Montagnier"),
                        ("Faraday", r"\d+[/-]\d+[/-]\d+\s+Faraday"),
                        ("Cook", r"\d+[/-]\d+[/-]\d+\s+Cook"),
                        ("Mjolnir", r"\d+[/-]\d+[/-]\d+\s+Mjolnir"),
                        ("Rendino", r"\d+[/-]\d+[/-]\d+\s+Rendino"),
                        ("Gigantes", r"\d+[/-]\d+[/-]\d+\s+Gigantes"),
                        ("Banshee", r"\d+[/-]\d+[/-]\d+\s+Banshee"),
                    ]
                    
                    updated_count = 0
                    for ship_name, pattern in ship_patterns:
                        if not SHIP_LOG_CATEGORIES or len(SHIP_LOG_CATEGORIES) == 0:
                            # Fallback to page_type if no categories
                            cur.execute("""
                                UPDATE wiki_pages 
                                SET ship_name = %s 
                                WHERE page_type = 'mission_log'
                                AND (ship_name IS NULL OR ship_name = '' OR ship_name = 'None')
                                AND title ~* %s
                            """, (ship_name.lower(), pattern))
                        else:
                            cur.execute("""
                                UPDATE wiki_pages 
                                SET ship_name = %s 
                                WHERE categories IS NOT NULL 
                                AND array_length(categories, 1) > 0
                                AND categories && %s
                                AND (ship_name IS NULL OR ship_name = '' OR ship_name = 'None')
                                AND title ~* %s
                            """, (ship_name.lower(), SHIP_LOG_CATEGORIES, pattern))
                        
                        count = cur.rowcount
                        if count > 0:
                            updated_count += count
                            print(f"  ✓ Updated {count} entries for {ship_name}")
                    
                    # Check results
                    if not SHIP_LOG_CATEGORIES or len(SHIP_LOG_CATEGORIES) == 0:
                        cur.execute("""
                            SELECT COUNT(*) as total_mission_logs,
                                   COUNT(CASE WHEN ship_name IS NULL OR ship_name = '' OR ship_name = 'None' THEN 1 END) as missing_ship_names
                            FROM wiki_pages 
                            WHERE page_type = 'mission_log'
                        """)
                    else:
                        cur.execute("""
                            SELECT COUNT(*) as total_mission_logs,
                                   COUNT(CASE WHEN ship_name IS NULL OR ship_name = '' OR ship_name = 'None' THEN 1 END) as missing_ship_names
                            FROM wiki_pages 
                            WHERE categories IS NOT NULL 
                            AND array_length(categories, 1) > 0
                            AND categories && %s
                        """, (SHIP_LOG_CATEGORIES,))
                    stats_after = cur.fetchone()
                    
                    print(f"📊 After cleanup: {stats_after['total_mission_logs']} mission logs, {stats_after['missing_ship_names']} missing ship names")
                    print(f"✅ Updated {updated_count} mission log entries with ship names")
                    
                    conn.commit()
                    print("=" * 50)
                    
                    return {
                        'before': dict(stats_before),
                        'after': dict(stats_after),
                        'updated_count': updated_count
                    }
                    
        except Exception as e:
            print(f"✗ Error cleaning up ship names: {e}")
            return {}

    def cleanup_seed_data(self) -> Dict:
        """Remove example/seed data from the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    print("🗑️  CLEANING UP SEED/EXAMPLE DATA")
                    print("=" * 50)
                    
                    # Count before cleanup
                    cur.execute("SELECT COUNT(*) as total_before FROM wiki_pages")
                    total_before = cur.fetchone()['total_before']
                    print(f"📊 Total entries before cleanup: {total_before}")
                    
                    # Identify and remove seed/example data patterns
                    seed_patterns = [
                        # Example entries
                        "%example%",
                        "%test%", 
                        "%sample%",
                        "%template%",
                        "%placeholder%",
                        
                        # Common seed data titles
                        "Main Page",
                        "Home",
                        "Welcome",
                        "Getting Started",
                        "How to Use",
                        "Instructions",
                        
                        # Any entries with "seed" in the title
                        "%seed%",
                        "%demo%",
                    ]
                    
                    deleted_count = 0
                    for pattern in seed_patterns:
                        cur.execute("""
                            DELETE FROM wiki_pages 
                            WHERE LOWER(title) LIKE LOWER(%s)
                        """, (pattern,))
                        
                        count = cur.rowcount
                        if count > 0:
                            deleted_count += count
                            print(f"  🗑️  Deleted {count} entries matching '{pattern}'")
                    
                    # Also remove any entries with very short content (likely examples)
                    # Use categories to avoid deleting legitimate general content
                    cur.execute("""
                        DELETE FROM wiki_pages 
                        WHERE LENGTH(raw_content) < 50 
                        AND (categories IS NULL OR 'General Information' = ANY(categories))
                    """)
                    short_content_deleted = cur.rowcount
                    if short_content_deleted > 0:
                        deleted_count += short_content_deleted
                        print(f"  🗑️  Deleted {short_content_deleted} entries with very short content")
                    
                    # Count after cleanup
                    cur.execute("SELECT COUNT(*) as total_after FROM wiki_pages")
                    total_after = cur.fetchone()['total_after']
                    
                    print(f"📊 Total entries after cleanup: {total_after}")
                    print(f"✅ Deleted {deleted_count} seed/example entries")
                    
                    conn.commit()
                    print("=" * 50)
                    
                    return {
                        'total_before': total_before,
                        'total_after': total_after,
                        'deleted_count': deleted_count
                    }
                    
        except Exception as e:
            print(f"✗ Error cleaning up seed data: {e}")
            return {}

    def _get_actual_log_categories_from_db(self) -> List[str]:
        """Get categories that actually contain 'log' from the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT unnest(categories) as category 
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        AND EXISTS (
                            SELECT 1 FROM unnest(categories) cat 
                            WHERE LOWER(cat) LIKE '%log%'
                        )
                        ORDER BY category
                    """)
                    categories = [row[0] for row in cur.fetchall()]
                    print(f"   📊 Found {len(categories)} actual log categories in database: {categories}")
                    return categories
        except Exception as e:
            print(f"✗ Error getting log categories from database: {e}")
            return []
    
    def get_character_categories(self) -> List[str]:
        """Get all character-related categories (excluding NPC Starships)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT unnest(categories) as category 
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        AND EXISTS (
                            SELECT 1 FROM unnest(categories) cat 
                            WHERE (LOWER(cat) LIKE '%character%' OR LOWER(cat) LIKE '%npc%')
                            AND LOWER(cat) NOT LIKE '%npc starship%'
                        )
                        ORDER BY category
                    """)
                    categories = [row[0] for row in cur.fetchall()]
                    print(f"   📊 Found {len(categories)} character categories in database: {categories}")
                    return categories
        except Exception as e:
            print(f"✗ Error getting character categories: {e}")
            return []

    def get_ship_categories(self) -> List[str]:
        """Get all ship-related categories - simple detection for categories containing 'ship' or 'starship'"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Simple query: find any category containing 'ship' or 'starship' (case insensitive)
                    cur.execute("""
                        SELECT DISTINCT unnest(categories) as category 
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        AND array_length(categories, 1) > 0
                        AND EXISTS (
                            SELECT 1 FROM unnest(categories) cat 
                            WHERE LOWER(cat) LIKE '%ship%'
                        )
                        ORDER BY category
                    """)
                    categories = [row[0] for row in cur.fetchall()]
                    print(f"   📊 Found {len(categories)} ship categories in database:")
                    for i, cat in enumerate(categories):
                        print(f"      {i+1}. '{cat}'")
                    return categories
        except Exception as e:
            print(f"✗ Error getting ship categories: {e}")
            return []

    def search_characters(self, query: str, limit: int = 10) -> List[Dict]:
        """Search character pages using category filtering"""
        character_categories = self.get_character_categories()
        if not character_categories:
            print("⚠️  No character categories found, falling back to general search")
            return self.search_pages(query, limit=limit)
        print(f"   🧑 Searching characters with categories: {character_categories}")
        return self.search_pages(query, categories=character_categories, limit=limit)

    def search_ships(self, query: str, limit: int = 10) -> List[Dict]:
        """Search ship pages with precise category filtering and exact title prioritization"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    print(f"   🚢 PRECISE SHIP SEARCH: '{query}' (limit={limit})")
                    
                    # Priority ship categories - focus on the most relevant ones
                    priority_categories = ['Ship Information', 'Active Starship', 'Starships', 'Ship','Inactive Starships','NPC Starships','Destroyed Starships']
                    
                    # STEP 1: Exact title match with priority categories
                    exact_query = """
                        SELECT id, title, raw_content, url, categories,
                               3.0 as rank
                        FROM wiki_pages 
                        WHERE LOWER(title) LIKE LOWER(%s)
                        AND categories IS NOT NULL 
                        AND array_length(categories, 1) > 0
                        AND categories && %s
                        ORDER BY 
                            CASE WHEN LOWER(title) = LOWER(%s) THEN 1 ELSE 2 END,
                            rank DESC
                        LIMIT %s
                    """
                    
                    # Generate query variations for better matching
                    query_variations = self._generate_query_variations(query)
                    
                    results = []
                    for variation in query_variations[:3]:  # Try top 3 variations
                        cur.execute(exact_query, [f'%{variation}%', priority_categories, variation, limit])
                        exact_results = [dict(row) for row in cur.fetchall()]
                        
                        if exact_results:
                            print(f"   ✅ Found {len(exact_results)} exact matches for '{variation}'")
                            results.extend(exact_results)
                            break  # Found exact matches, no need to try other variations
                    
                    # STEP 2: If no exact matches, try broader ship categories but still prioritize title matches
                    if not results:
                        print(f"   🔍 No exact matches, trying broader ship search...")
                        all_ship_categories = self.get_ship_categories()
                        
                        if all_ship_categories:
                            broader_query = """
                                SELECT id, title, raw_content, url, categories,
                                       CASE 
                                           WHEN LOWER(title) LIKE LOWER(%s) THEN 2.0
                                           WHEN LOWER(raw_content) LIKE LOWER(%s) THEN 1.0
                                           ELSE 0.5
                                       END as rank
                                FROM wiki_pages 
                                WHERE categories IS NOT NULL 
                                AND array_length(categories, 1) > 0
                                AND categories && %s
                                AND (
                                    LOWER(title) LIKE LOWER(%s) OR
                                    LOWER(raw_content) LIKE LOWER(%s)
                                )
                                ORDER BY rank DESC, id DESC
                                LIMIT %s
                            """
                            
                            search_term = f'%{query}%'
                            cur.execute(broader_query, [
                                search_term, search_term, all_ship_categories,
                                search_term, search_term, limit
                            ])
                            results = [dict(row) for row in cur.fetchall()]
                            print(f"   📊 Broader search found {len(results)} results")
                    
                    # STEP 3: Final fallback to general search if still no results
                    if not results:
                        print(f"   ⚠️  No ship-specific results, falling back to general search")
                        return self.search_pages(query, limit=limit)
                    
                    # Remove duplicates and limit results
                    seen_ids = set()
                    unique_results = []
                    for result in results:
                        if result['id'] not in seen_ids:
                            seen_ids.add(result['id'])
                            unique_results.append(result)
                            if len(unique_results) >= limit:
                                break
                    
                    print(f"   ✅ PRECISE SHIP SEARCH: {len(unique_results)} unique results")
                    self.log_search_results(unique_results, "Precise ship search", debug_level=1)
                    
                    return unique_results
                    
        except Exception as e:
            print(f"   ❌ Error in precise ship search: {e}")
            # Fallback to original method
            ship_categories = self.get_ship_categories()
            if not ship_categories:
                print("⚠️  No ship categories found, falling back to general search")
                return self.search_pages(query, limit=limit)
            print(f"   🚢 Fallback: Searching ships with categories: {ship_categories}")
            return self.search_pages(query, categories=ship_categories, limit=limit)

    def search_logs(self, query: str, ship_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Search log pages using category filtering with chronological sorting when possible.
        """
        log_categories = self._get_actual_log_categories_from_db()  # ✅ Already exists
        if not log_categories:
            print("⚠️  No log categories found, using force_mission_logs_only fallback")
            return self.search_pages(query, ship_name=ship_name, limit=limit, force_mission_logs_only=True)
        
        # For ship-specific searches, try chronological sorting first
        if ship_name:
            print(f"🔍 LOG SEARCH: Attempting chronological sort for '{query}' on ship '{ship_name}'")
            # Use title search in chronologically sorted results
            chronological_results = self._get_logs_sorted_by_title_date(
                ship_name=ship_name, 
                categories=log_categories, 
                limit=limit * 2,  # Get more results for filtering
                debug_level=1
            )
            
            # Filter chronological results by query text
            if chronological_results:
                query_lower = query.lower()
                filtered_results = []
                for result in chronological_results:
                    if (query_lower in result['title'].lower() or 
                        query_lower in result['raw_content'].lower()):
                        filtered_results.append(result)
                        if len(filtered_results) >= limit:
                            break
                
                if filtered_results:
                    print(f"   ✅ Found {len(filtered_results)} chronologically sorted results")
                    return filtered_results
                else:
                    print(f"   ⚠️  No chronological results matched query '{query}', falling back to standard search")
            
            # Fallback: Filter to specific ship logs using standard search
            ship_log_categories = [cat for cat in log_categories 
                                  if ship_name.lower() in cat.lower()]
            if ship_log_categories:
                print(f"   📋 Searching {ship_name} logs with categories: {ship_log_categories}")
                return self.search_pages(query, categories=ship_log_categories, ship_name=ship_name, limit=limit)
            else:
                print(f"   ⚠️  No specific log categories found for ship '{ship_name}', searching all logs")
        
        # Search all logs with category filtering
        print(f"   📋 Searching all logs with categories: {log_categories}")
        return self.search_pages(query, categories=log_categories, ship_name=ship_name, limit=limit)
    
    def search_by_categories(self, query: str, categories: List[str], limit: int = 10) -> List[Dict]:
        """Search pages by specific categories"""
        return self.search_pages(query, categories=categories, limit=limit)

    def _get_logs_sorted_by_title_date(self, ship_name: Optional[str] = None, 
                                      categories: Optional[List[str]] = None,
                                      limit: int = 10, debug_level: int = 1) -> List[Dict]:
        """
        Get logs sorted by dates extracted from titles, not by ID order.
        
        Two-phase approach:
        1. Extract dates from titles and sort chronologically 
        2. Use sorted results to retrieve full log content in proper order
        
        This handles cases where logs weren't imported chronologically.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    if debug_level >= 1:
                        print(f"📅 CHRONOLOGICAL LOG SORT: ship='{ship_name}', limit={limit}")
                    
                    # Phase 1: Extract dates from titles and sort chronologically
                    base_query = """
                        SELECT id, title,
                               -- Extract dates in various formats from titles
                               CASE 
                                   -- Format: "Ship 4/23/2022" or "Ship 04/23/2022"
                                   WHEN title ~ '\\d{1,2}/\\d{1,2}/\\d{4}' THEN
                                       TO_DATE(
                                           substring(title from '(\\d{1,2}/\\d{1,2}/\\d{4})'),
                                           'MM/DD/YYYY'
                                       )
                                   -- Format: "2024/09/29 Ship Log" or "2024-09-29 Ship Log"  
                                   WHEN title ~ '\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}' THEN
                                       TO_DATE(
                                           substring(title from '(\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})'),
                                           'YYYY-MM-DD'
                                       )
                                   -- Format: "Ship 12-25-2023" (MM-DD-YYYY)
                                   WHEN title ~ '\\d{1,2}-\\d{1,2}-\\d{4}' THEN
                                       TO_DATE(
                                           substring(title from '(\\d{1,2}-\\d{1,2}-\\d{4})'),
                                           'MM-DD-YYYY'
                                       )
                                   -- Format: "Ship 2023.12.25" (YYYY.MM.DD)
                                   WHEN title ~ '\\d{4}\\.\\d{1,2}\\.\\d{1,2}' THEN
                                       TO_DATE(
                                           substring(title from '(\\d{4}\\.\\d{1,2}\\.\\d{1,2})'),
                                           'YYYY.MM.DD'
                                       )
                                   ELSE NULL
                               END as extracted_date
                        FROM wiki_pages 
                        WHERE 1=1
                    """
                    
                    params = []
                    
                    # Add category filter (for ship's mission logs)
                    if categories and len(categories) > 0:
                        base_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                        params.append(categories)
                    
                    # Add ship name filter (search in title)
                    if ship_name:
                        base_query += " AND LOWER(title) LIKE %s"
                        params.append(f'%{ship_name.lower()}%')
                    
                    # Only include entries where we successfully extracted a date
                    base_query += """
                        AND (
                            title ~ '\\d{1,2}/\\d{1,2}/\\d{4}' OR
                            title ~ '\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}' OR  
                            title ~ '\\d{1,2}-\\d{1,2}-\\d{4}' OR
                            title ~ '\\d{4}\\.\\d{1,2}\\.\\d{1,2}'
                        )
                        ORDER BY extracted_date DESC NULLS LAST
                        LIMIT %s
                    """
                    params.append(limit)
                    
                    if debug_level >= 2:
                        print(f"   📊 Phase 1 Query: {base_query}")
                        print(f"   📊 Parameters: {params}")
                    
                    cur.execute(base_query, params)
                    date_sorted_results = cur.fetchall()
                    
                    if not date_sorted_results:
                        if debug_level >= 1:
                            print(f"   ⚠️  No logs found with extractable dates")
                        return []
                    
                    if debug_level >= 1:
                        print(f"   ✅ Phase 1: Found {len(date_sorted_results)} logs with extractable dates")
                        for i, result in enumerate(date_sorted_results[:5]):  # Show first 5
                            print(f"      {i+1}. {result['title']} -> {result['extracted_date']}")
                        if len(date_sorted_results) > 5:
                            print(f"      ... and {len(date_sorted_results) - 5} more")
                    
                    # Phase 2: Get full content for the chronologically sorted logs
                    sorted_ids = [str(result['id']) for result in date_sorted_results]
                    
                    if not sorted_ids:
                        return []
                    
                    # Create ORDER BY CASE to maintain chronological order
                    order_case = "CASE id " + " ".join([
                        f"WHEN {id_val} THEN {i}" for i, id_val in enumerate(sorted_ids)
                    ]) + " END"
                    
                    content_query = f"""
                        SELECT id, title, raw_content, url, categories
                        FROM wiki_pages 
                        WHERE id IN ({','.join(['%s'] * len(sorted_ids))})
                        ORDER BY {order_case}
                    """
                    
                    cur.execute(content_query, sorted_ids)
                    final_results = [dict(row) for row in cur.fetchall()]
                    
                    if debug_level >= 1:
                        print(f"   ✅ Phase 2: Retrieved {len(final_results)} full log entries in chronological order")
                    
                    return final_results
                    
        except Exception as e:
            print(f"✗ Error in chronological log sort: {e}")
            if debug_level >= 2:
                import traceback
                traceback.print_exc()
            return []

# Global database controller instance
db_controller = None

def get_db_controller():
    """Get the global database controller instance"""
    global db_controller
    if db_controller is None:
        db_controller = FleetDatabaseController()
    return db_controller 
