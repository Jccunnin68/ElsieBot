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
    
    def search_pages(self, query: str, page_type: Optional[str] = None, 
                    ship_name: Optional[str] = None, limit: int = 10, 
                    force_mission_logs_only: bool = False, categories: Optional[List[str]] = None) -> List[Dict]:
        """Enhanced search with category support and backward compatibility"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    print(f"🔍 ENHANCED SEARCH - Query: '{query}' (force_mission_logs_only: {force_mission_logs_only})")
                    
                    # Convert page_type to categories for backward compatibility
                    if page_type and not categories:
                        categories = self._convert_page_type_to_categories(page_type, ship_name)
                        print(f"   🔄 Converted page_type '{page_type}' to categories: {categories}")
                    
                    # Override for mission logs only
                    if force_mission_logs_only:
                        categories = self._get_all_ship_log_categories()
                        print(f"   🎯 FORCING MISSION LOGS ONLY - using ship log categories: {len(categories)} categories")
                    
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
                            ship_query = """
                                SELECT id, title, raw_content, ship_name, log_date, url, categories
                                FROM wiki_pages 
                                WHERE ship_name = %s
                                ORDER BY log_date DESC
                                LIMIT %s
                            """
                            cur.execute(ship_query, [detected_ship, limit])
                            ship_results = [dict(row) for row in cur.fetchall()]
                            print(f"   📊 Ship-specific search found {len(ship_results)} results")
                            all_results.extend(ship_results)
                    
                    # STEP 2: Category-based search (PRIMARY)
                    if categories and len(all_results) < limit:
                        print(f"   🏷️ Category-based search for: {categories}")
                        
                        # Safety check: ensure categories is not empty
                        if not categories or len(categories) == 0:
                            print(f"   ⚠️  Empty categories array, skipping category search")
                        else:
                            category_query = """
                                SELECT id, title, raw_content, ship_name, log_date, url, categories,
                                       ts_rank(to_tsvector('english', title), 
                                              plainto_tsquery('english', %s)) as rank
                                FROM wiki_pages 
                                WHERE categories IS NOT NULL 
                                AND array_length(categories, 1) > 0
                                AND categories && %s
                                AND to_tsvector('english', title) @@ plainto_tsquery('english', %s)
                            """
                            
                            category_params = [query, categories, query]
                            
                            if ship_name:
                                category_query += " AND ship_name = %s"
                                category_params.append(ship_name)
                            
                            # Exclude already found results
                            if all_results:
                                existing_ids = [str(r['id']) for r in all_results]
                                category_query += f" AND id NOT IN ({','.join(['%s'] * len(existing_ids))})"
                                category_params.extend(existing_ids)
                            
                            remaining_limit = limit - len(all_results)
                            category_query += " ORDER BY rank DESC, log_date DESC LIMIT %s"
                            category_params.append(remaining_limit)
                            
                            cur.execute(category_query, category_params)
                            category_results = [dict(row) for row in cur.fetchall()]
                            print(f"   📊 Category search found {len(category_results)} results")
                            all_results.extend(category_results)
                    
                    # STEP 3: Title-based full-text search
                    if len(all_results) < limit:
                        print(f"   🔍 Title FTS search...")
                        title_query = """
                            SELECT id, title, raw_content, ship_name, log_date, url, categories,
                                   ts_rank(to_tsvector('english', title), 
                                          plainto_tsquery('english', %s)) as rank
                            FROM wiki_pages 
                            WHERE to_tsvector('english', title) @@ plainto_tsquery('english', %s)
                        """
                        
                        title_params = [query, query]
                        
                        # Use categories if available
                        if categories:
                            # Safety check: ensure categories is not empty
                            if categories and len(categories) > 0:
                                title_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                                title_params.append(categories)
                        
                        if ship_name:
                            title_query += " AND ship_name = %s"
                            title_params.append(ship_name)
                        
                        # Exclude already found ship results
                        if all_results:
                            existing_ids = [str(r['id']) for r in all_results]
                            title_query += f" AND id NOT IN ({','.join(['%s'] * len(existing_ids))})"
                            title_params.extend(existing_ids)
                        
                        remaining_limit = limit - len(all_results)
                        title_query += " ORDER BY rank DESC, log_date DESC LIMIT %s"
                        title_params.append(remaining_limit)
                        
                        cur.execute(title_query, title_params)
                        title_results = [dict(row) for row in cur.fetchall()]
                        print(f"   📊 Title FTS found {len(title_results)} results")
                        all_results.extend(title_results)
                    
                    # STEP 4: Content-based search if still need more results
                    if len(all_results) < limit:
                        print(f"   🔍 Content FTS search...")
                        content_query = """
                            SELECT id, title, raw_content, ship_name, log_date, url, categories,
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
                            content_query += " AND ship_name = %s"
                            content_params.append(ship_name)
                        
                        # Exclude already found results
                        if all_results:
                            existing_ids = [str(r['id']) for r in all_results]
                            content_query += f" AND id NOT IN ({','.join(['%s'] * len(existing_ids))})"
                            content_params.extend(existing_ids)
                        
                        remaining_limit = limit - len(all_results)
                        content_query += " ORDER BY rank DESC, log_date DESC LIMIT %s"
                        content_params.append(remaining_limit)
                        
                        cur.execute(content_query, content_params)
                        content_results = [dict(row) for row in cur.fetchall()]
                        print(f"   📊 Content FTS found {len(content_results)} results")
                        all_results.extend(content_results)
                    
                    # STEP 5: Fallback to LIKE search if FTS fails
                    if not all_results:
                        print(f"   🔄 Fallback LIKE search...")
                        like_query = """
                            SELECT id, title, raw_content, ship_name, log_date, url, categories
                            FROM wiki_pages 
                            WHERE (LOWER(title) LIKE LOWER(%s) OR LOWER(raw_content) LIKE LOWER(%s))
                        """
                        
                        like_params = [f'%{query}%', f'%{query}%']
                        
                        # Use categories if available
                        if categories:
                            # Safety check: ensure categories is not empty
                            if categories and len(categories) > 0:
                                like_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                                like_params.append(categories)
                        
                        if ship_name:
                            like_query += " AND ship_name = %s"
                            like_params.append(ship_name)
                        
                        like_query += " ORDER BY log_date DESC LIMIT %s"
                        like_params.append(limit)
                        
                        cur.execute(like_query, like_params)
                        like_results = [dict(row) for row in cur.fetchall()]
                        print(f"   📊 LIKE search found {len(like_results)} results")
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
                    
                    # Debug: Show results
                    for i, result in enumerate(unique_results[:3]):
                        title_preview = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
                        categories_preview = result.get('categories', [])
                        print(f"      📄 Result {i+1}: '{title_preview}' (categories: {categories_preview})")
                    
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
    
    def get_recent_logs(self, ship_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent mission logs using categories"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Use ship log categories instead of page_type
                    from handlers.ai_wisdom.category_mappings import SHIP_LOG_CATEGORIES
                    
                    # Safety check: ensure SHIP_LOG_CATEGORIES is not empty
                    if not SHIP_LOG_CATEGORIES or len(SHIP_LOG_CATEGORIES) == 0:
                        print(f"   ⚠️  No ship log categories defined, falling back to page_type")
                        query = """
                            SELECT id, title, raw_content, ship_name, log_date, url, categories
                            FROM wiki_pages 
                            WHERE page_type = 'mission_log'
                        """
                        params = []
                    else:
                        query = """
                            SELECT id, title, raw_content, ship_name, log_date, url, categories
                            FROM wiki_pages 
                            WHERE categories IS NOT NULL 
                            AND array_length(categories, 1) > 0
                            AND categories && %s
                        """
                        params = [SHIP_LOG_CATEGORIES]
                    
                    if ship_name:
                        query += " AND ship_name = %s"
                        params.append(ship_name.lower())
                    
                    query += " ORDER BY log_date DESC NULLS LAST LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    # Track content access for returned logs
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    return results
                    
        except Exception as e:
            print(f"✗ Error getting recent logs: {e}")
            return []

    def get_selected_logs(self, selection_type: str, ship_name: Optional[str] = None, 
                         limit: int = 5, date_filter: Optional[str] = None) -> List[Dict]:
        """
        Get logs based on selection criteria with proper ordering and filtering
        Now uses categories instead of page_type
        
        Args:
            selection_type: 'latest', 'first', 'random', 'today', etc.
            ship_name: Optional ship filter
            limit: Number of results (1 for random selection)
            date_filter: Optional date range filter
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    print(f"🎯 SELECTED LOG SEARCH: type='{selection_type}', ship='{ship_name}', limit={limit}")
                    
                    # Use ship log categories instead of page_type
                    from handlers.ai_wisdom.category_mappings import SHIP_LOG_CATEGORIES
                    
                    # Safety check: ensure SHIP_LOG_CATEGORIES is not empty
                    if not SHIP_LOG_CATEGORIES or len(SHIP_LOG_CATEGORIES) == 0:
                        print(f"   ⚠️  No ship log categories defined, falling back to page_type")
                        # Base query - ONLY mission logs using page_type fallback
                        query = """
                            SELECT id, title, raw_content, ship_name, log_date, url, categories
                            FROM wiki_pages 
                            WHERE page_type = 'mission_log'
                        """
                        params = []
                    else:
                        # Base query - ONLY mission logs using categories
                        query = """
                            SELECT id, title, raw_content, ship_name, log_date, url, categories
                            FROM wiki_pages 
                            WHERE categories IS NOT NULL 
                            AND array_length(categories, 1) > 0
                            AND categories && %s
                        """
                        params = [SHIP_LOG_CATEGORIES]
                    
                    # Add ship filter
                    if ship_name:
                        query += " AND ship_name = %s"
                        params.append(ship_name.lower())
                    
                    # Add date filters for date-based selections
                    if selection_type == 'today':
                        query += " AND DATE(log_date) = CURRENT_DATE"
                    elif selection_type == 'yesterday':
                        query += " AND DATE(log_date) = CURRENT_DATE - INTERVAL '1 day'"
                    elif selection_type == 'this_week':
                        query += " AND log_date >= DATE_TRUNC('week', CURRENT_DATE)"
                    elif selection_type == 'last_week':
                        query += " AND log_date >= DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 week' AND log_date < DATE_TRUNC('week', CURRENT_DATE)"
                    
                    # Add ordering based on selection type
                    if selection_type == 'random':
                        query += " ORDER BY RANDOM()"
                        limit = 1  # Random selection always returns 1
                    elif selection_type in ['latest', 'recent']:
                        query += " ORDER BY log_date DESC NULLS LAST"
                    elif selection_type in ['first', 'earliest', 'oldest']:
                        query += " ORDER BY log_date ASC NULLS LAST"
                    elif selection_type in ['today', 'yesterday', 'this_week', 'last_week']:
                        query += " ORDER BY log_date DESC NULLS LAST"  # Most recent within date range
                    else:
                        # Default to recent
                        query += " ORDER BY log_date DESC NULLS LAST"
                    
                    query += " LIMIT %s"
                    params.append(limit)
                    
                    print(f"   📊 Executing query with {len(params)} parameters")
                    cur.execute(query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   ✅ Found {len(results)} selected logs")
                    
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
                        SELECT title, ship_name, content_accessed, categories,
                               LEFT(raw_content, 100) as content_preview
                        FROM wiki_pages 
                        WHERE content_accessed > 0
                        ORDER BY content_accessed DESC, title ASC
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
                            COUNT(DISTINCT ship_name) as unique_ships,
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
                        SELECT id, title, page_type, ship_name, 
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
                        print(f"    Page Type: '{row['page_type']}'")
                        print(f"    Ship Name: '{row['ship_name']}'")
                        print(f"    Content Preview: '{row['content_preview']}...'")
                        print(f"    Log Date: {row['log_date']}")
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
                        SELECT title, page_type, ship_name 
                        FROM wiki_pages 
                        WHERE LOWER(title) LIKE '%adagio%' 
                        ORDER BY title
                    """)
                    adagio_entries = cur.fetchall()
                    
                    for row in adagio_entries:
                        print(f"  - Title: '{row['title']}' | Type: '{row['page_type']}' | Ship: '{row['ship_name']}'")
                    
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
                    from handlers.ai_wisdom.category_mappings import SHIP_LOG_CATEGORIES
                    
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

    def _convert_page_type_to_categories(self, page_type: str, ship_name: Optional[str] = None) -> List[str]:
        """Convert old page_type to new categories for backward compatibility"""
        from handlers.ai_wisdom.category_mappings import convert_page_type_to_categories
        return convert_page_type_to_categories(page_type, ship_name)
    
    def _get_all_ship_log_categories(self) -> List[str]:
        """Get all ship log categories for mission log searches"""
        from handlers.ai_wisdom.category_mappings import SHIP_LOG_CATEGORIES
        return SHIP_LOG_CATEGORIES
    
    def search_by_categories(self, query: str, categories: List[str], limit: int = 10) -> List[Dict]:
        """Search pages by specific categories"""
        return self.search_pages(query, categories=categories, limit=limit)

# Global database controller instance
db_controller = None

def get_db_controller():
    """Get the global database controller instance"""
    global db_controller
    if db_controller is None:
        db_controller = FleetDatabaseController()
    return db_controller 
