"""Database controller for fleet wiki content using PostgreSQL - Simplified single-query interface"""

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
    
    def search(self, query: str, categories: Optional[List[str]] = None, 
               limit: int = 10, order_by: str = 'relevance', 
               ship_name: Optional[str] = None) -> List[Dict]:
        """
        Single unified search method for all database queries.
        
        Args:
            query: Search terms (can be empty for category-only searches)
            categories: Optional category filter 
            limit: Max results
            order_by: 'relevance', 'chronological', 'id_desc', 'id_asc', 'random'
            ship_name: Optional ship name filter (searches in title)
        
        Returns:
            List of matching records with full content
        """
        # Handle empty query - use category-only search
        if not query or query.strip() == "":
            return self.search_by_categories_only(categories, limit, order_by, ship_name)
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    print(f"🔍 UNIFIED SEARCH: '{query}' (categories={len(categories) if categories else 0}, order={order_by})")
                    
                    # Build base query with ranking
                    base_query = """
                        SELECT id, title, raw_content, url, categories,
                               CASE 
                                   WHEN to_tsvector('english', title) @@ to_tsquery('english', %s) THEN
                                       ts_rank(to_tsvector('english', title), to_tsquery('english', %s)) + 2.0
                                   ELSE 
                                       ts_rank(to_tsvector('english', raw_content), to_tsquery('english', %s))
                               END as rank
                        FROM wiki_pages 
                        WHERE (
                            to_tsvector('english', title) @@ to_tsquery('english', %s) OR
                            to_tsvector('english', raw_content) @@ to_tsquery('english', %s)
                        )
                    """
                    
                    # Parameters for base query
                    # Format the query for to_tsquery with improved multi-word handling
                    ts_query = self._format_search_query(query)
                    params = [ts_query, ts_query, ts_query, ts_query, ts_query]
                    
                    # Add category filter if specified
                    if categories and len(categories) > 0:
                        base_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                        params.append(categories)
                    
                    # Add ship name filter if specified
                    if ship_name:
                        base_query += " AND LOWER(title) LIKE %s"
                        params.append(f'%{ship_name.lower()}%')
                    
                    # Add ordering
                    if order_by == 'chronological':
                        # Try to sort by extracted dates from titles, fallback to ID
                        base_query += """
                            ORDER BY 
                                CASE 
                                    WHEN title ~ '\\d{1,2}/\\d{1,2}/\\d{4}' THEN
                                        TO_DATE(substring(title from '(\\d{1,2}/\\d{1,2}/\\d{4})'), 'MM/DD/YYYY')
                                    WHEN title ~ '\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}' THEN
                                        TO_DATE(substring(title from '(\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})'), 'YYYY-MM-DD')
                                    ELSE NULL
                                END DESC NULLS LAST,
                                id DESC
                        """
                    elif order_by == 'closest_to_today':
                        # Find logs with dates closest to current system date
                        base_query += """
                            ORDER BY 
                                CASE 
                                    WHEN title ~ '\\d{1,2}/\\d{1,2}/\\d{4}' THEN
                                        ABS(CURRENT_DATE - TO_DATE(substring(title from '(\\d{1,2}/\\d{1,2}/\\d{4})'), 'MM/DD/YYYY'))
                                    WHEN title ~ '\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}' THEN
                                        ABS(CURRENT_DATE - TO_DATE(substring(title from '(\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})'), 'YYYY-MM-DD'))
                                    ELSE 999999999
                                END ASC,
                                id DESC
                        """
                    elif order_by == 'id_desc':
                        base_query += " ORDER BY id DESC"
                    elif order_by == 'id_asc':
                        base_query += " ORDER BY id ASC"
                    elif order_by == 'random':
                        base_query += " ORDER BY RANDOM()"
                    else:  # relevance (default)
                        base_query += " ORDER BY rank DESC, id DESC"
                    
                    base_query += " LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(base_query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   ✅ Found {len(results)} results")
                    
                    # Track content access for returned results
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    return results
                    
        except Exception as e:
            print(f"✗ Error in unified search: {e}")
            return []

    def search_by_categories_only(self, categories: Optional[List[str]] = None, 
                                 limit: int = 10, order_by: str = 'relevance',
                                 ship_name: Optional[str] = None) -> List[Dict]:
        """
        Search by categories only without requiring a text query.
        Used for general log searches and random selections.
        
        Args:
            categories: Category filter (required for this method)
            limit: Max results
            order_by: 'relevance', 'chronological', 'id_desc', 'id_asc', 'random'
            ship_name: Optional ship name filter
        
        Returns:
            List of matching records with full content
        """
        if not categories or len(categories) == 0:
            print("⚠️  Category-only search requires categories")
            return []
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    print(f"📂 CATEGORY-ONLY SEARCH: categories={categories}, order={order_by}, limit={limit}")
                    
                    # Build query that filters by categories only
                    base_query = """
                        SELECT id, title, raw_content, url, categories
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        AND array_length(categories, 1) > 0 
                        AND categories && %s
                    """
                    
                    params = [categories]
                    
                    # Add ship name filter if specified
                    if ship_name:
                        base_query += " AND LOWER(title) LIKE %s"
                        params.append(f'%{ship_name.lower()}%')
                    
                    # Add ordering
                    if order_by == 'chronological':
                        # Try to sort by extracted dates from titles, fallback to ID
                        base_query += """
                            ORDER BY 
                                CASE 
                                    WHEN title ~ '\\d{1,2}/\\d{1,2}/\\d{4}' THEN
                                        TO_DATE(substring(title from '(\\d{1,2}/\\d{1,2}/\\d{4})'), 'MM/DD/YYYY')
                                    WHEN title ~ '\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}' THEN
                                        TO_DATE(substring(title from '(\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})'), 'YYYY-MM-DD')
                                    ELSE NULL
                                END DESC NULLS LAST,
                                id DESC
                        """
                    elif order_by == 'closest_to_today':
                        # Find logs with dates closest to current system date
                        base_query += """
                            ORDER BY 
                                CASE 
                                    WHEN title ~ '\\d{1,2}/\\d{1,2}/\\d{4}' THEN
                                        ABS(CURRENT_DATE - TO_DATE(substring(title from '(\\d{1,2}/\\d{1,2}/\\d{4})'), 'MM/DD/YYYY'))
                                    WHEN title ~ '\\d{4}[/-]\\d{1,2}[/-]\\d{1,2}' THEN
                                        ABS(CURRENT_DATE - TO_DATE(substring(title from '(\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})'), 'YYYY-MM-DD'))
                                    ELSE 999999999
                                END ASC,
                                id DESC
                        """
                    elif order_by == 'id_desc':
                        base_query += " ORDER BY id DESC"
                    elif order_by == 'id_asc':
                        base_query += " ORDER BY id ASC"
                    elif order_by == 'random':
                        base_query += " ORDER BY RANDOM()"
                    else:  # relevance - for category-only, use chronological as default
                        base_query += " ORDER BY id DESC"
                    
                    base_query += " LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(base_query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   ✅ Found {len(results)} category-filtered results")
                    
                    # Track content access for returned results
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    return results
                    
        except Exception as e:
            print(f"✗ Error in category-only search: {e}")
            return []
    
    def search_titles_only(self, query: str, categories: Optional[List[str]] = None, 
                          limit: int = 10) -> List[Dict]:
        """
        Search only in page titles for exact or close matches.
        Used as first step for general searches before falling back to content search.
        
        Args:
            query: Search terms
            categories: Optional category filter 
            limit: Max results
        
        Returns:
            List of matching records with full content
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    print(f"🎯 TITLE-ONLY SEARCH: '{query}' (categories={len(categories) if categories else 0})")
                    
                    # Build query that searches only titles
                    base_query = """
                        SELECT id, title, raw_content, url, categories,
                               ts_rank(to_tsvector('english', title), to_tsquery('english', %s)) as rank
                        FROM wiki_pages 
                        WHERE to_tsvector('english', title) @@ to_tsquery('english', %s)
                    """
                    
                    # Format the query for to_tsquery with improved multi-word handling
                    ts_query = self._format_search_query(query)
                    params = [ts_query, ts_query]
                    
                    # Add category filter if specified
                    if categories and len(categories) > 0:
                        base_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                        params.append(categories)
                    
                    # Order by relevance (title rank)
                    base_query += " ORDER BY rank DESC, id DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(base_query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   ✅ Found {len(results)} title matches")
                    
                    # Track content access for returned results
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    return results
                    
        except Exception as e:
            print(f"✗ Error in title-only search: {e}")
            return []

    def search_content_deep(self, query: str, categories: Optional[List[str]] = None, 
                           limit: int = 100) -> List[Dict]:
        """
        Deep search in content for when title search fails.
        Searches top results by content relevance.
        
        Args:
            query: Search terms
            categories: Optional category filter 
            limit: Max results to consider (default 100)
        
        Returns:
            List of matching records with full content, limited to top 10 by relevance
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    print(f"🔍 DEEP CONTENT SEARCH: '{query}' (top {limit} results, categories={len(categories) if categories else 0})")
                    
                    # Build query that searches content with higher limit for processing
                    base_query = """
                        SELECT id, title, raw_content, url, categories,
                               ts_rank(to_tsvector('english', raw_content), to_tsquery('english', %s)) as rank
                        FROM wiki_pages 
                        WHERE to_tsvector('english', raw_content) @@ to_tsquery('english', %s)
                    """
                    
                    # Format the query for to_tsquery with improved multi-word handling
                    ts_query = self._format_search_query(query)
                    params = [ts_query, ts_query]
                    
                    # Add category filter if specified
                    if categories and len(categories) > 0:
                        base_query += " AND categories IS NOT NULL AND array_length(categories, 1) > 0 AND categories && %s"
                        params.append(categories)
                    
                    # Order by content relevance, get top results for processing
                    base_query += " ORDER BY rank DESC, id DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(base_query, params)
                    all_results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   📊 Found {len(all_results)} content matches for processing")
                    
                    # Return top 10 most relevant results
                    results = all_results[:10]
                    
                    # Track content access for returned results
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    print(f"   ✅ Returning top {len(results)} results")
                    return results
                    
        except Exception as e:
            print(f"✗ Error in deep content search: {e}")
            return []
    
    # ==============================================================================
    # SEARCH QUERY FORMATTING
    # ==============================================================================
    
    def _format_search_query(self, query: str) -> str:
        """
        Format a search query for PostgreSQL to_tsquery with improved multi-word handling.
        
        For character names, we want to be more flexible than requiring ALL words.
        This creates a query that tries exact phrases first, then falls back to partial matches.
        
        Args:
            query: The search query string
            
        Returns:
            Formatted query string for to_tsquery
        """
        words = [self._escape_tsquery_word(word) for word in query.strip().split()]
        
        if len(words) == 1:
            # Single word - simple case
            return words[0]
        
        elif len(words) == 2:
            # Two words - try both together and individually
            # "Marcus Blaine" -> "(Marcus & Blaine) | Marcus | Blaine"
            word1, word2 = words
            return f"({word1} & {word2}) | {word1} | {word2}"
        
        elif len(words) == 3:
            # Three words - try combinations
            # "Captain Marcus Blaine" -> "(Captain & Marcus & Blaine) | (Marcus & Blaine) | Marcus | Blaine"
            word1, word2, word3 = words
            return f"({word1} & {word2} & {word3}) | ({word2} & {word3}) | {word2} | {word3}"
        
        elif len(words) >= 4:
            # Four or more words - be very flexible for long names like "Marcus Antonius Telemachus Aquila"
            # Try: all words, any 3 consecutive, any 2 consecutive, any individual significant word
            all_words = ' & '.join(words)
            
            # Try combinations of 3 consecutive words
            three_word_combos = []
            for i in range(len(words) - 2):
                combo = ' & '.join(words[i:i+3])
                three_word_combos.append(f"({combo})")
            
            # Try combinations of 2 consecutive words  
            two_word_combos = []
            for i in range(len(words) - 1):
                combo = ' & '.join(words[i:i+2])
                two_word_combos.append(f"({combo})")
            
            # Individual words (excluding common words)
            common_words = {'the', 'and', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
            individual_words = [word for word in words if word.lower() not in common_words]
            
            # Build the final query with precedence: all words, 3-word combos, 2-word combos, individual words
            query_parts = [f"({all_words})"]
            query_parts.extend(three_word_combos)
            query_parts.extend(two_word_combos)
            query_parts.extend(individual_words)
            
            return ' | '.join(query_parts)
        
        else:
            # Fallback to original behavior
            return ' & '.join(words)

    def _escape_tsquery_word(self, word: str) -> str:
        """
        Escape a word for safe use in PostgreSQL to_tsquery.
        
        Args:
            word: The word to escape
            
        Returns:
            Escaped word safe for to_tsquery
        """
        # Remove any characters that could break the query
        # Keep only alphanumeric, apostrophes, and hyphens
        import re
        cleaned = re.sub(r"[^a-zA-Z0-9'-]", "", word)
        
        # If the word is empty after cleaning, return a safe placeholder
        if not cleaned:
            return "placeholder"
        
        return cleaned

    # ==============================================================================
    # CATEGORY HELPER METHODS
    # ==============================================================================
    
    def get_log_categories(self) -> List[str]:
        """Get categories that contain 'log' from the database"""
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
                    return categories
        except Exception as e:
            print(f"✗ Error getting log categories: {e}")
            return []
    
    def get_ship_categories(self) -> List[str]:
        """Get ship-related categories (including vessels, fleet assets, etc.)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT unnest(categories) as category 
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        AND EXISTS (
                            SELECT 1 FROM unnest(categories) cat 
                            WHERE (
                                LOWER(cat) LIKE '%ship%' 
                                OR LOWER(cat) LIKE '%vessel%'
                                OR LOWER(cat) LIKE 'uss %'
                                OR LOWER(cat) LIKE '% crew'
                                OR LOWER(cat) LIKE '%fleet%'
                            )
                            AND LOWER(cat) NOT LIKE '%log%'
                            AND LOWER(cat) NOT LIKE '%character%'
                            AND LOWER(cat) NOT LIKE '%planet%'
                            AND LOWER(cat) NOT LIKE '%species%'
                        )
                        ORDER BY category
                    """)
                    categories = [row[0] for row in cur.fetchall()]
                    return categories
        except Exception as e:
            print(f"✗ Error getting ship categories: {e}")
            return []
    
    def get_character_categories(self) -> List[str]:
        """Get character-related categories (excluding NPC Starships)"""
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
                    return categories
        except Exception as e:
            print(f"✗ Error getting character categories: {e}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """Get all distinct categories from the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT unnest(categories) as category
                        FROM wiki_pages
                        WHERE categories IS NOT NULL AND array_length(categories, 1) > 0
                        ORDER BY category
                    """)
                    categories = [row[0] for row in cur.fetchall()]
                    return categories
        except Exception as e:
            print(f"✗ Error getting all categories: {e}")
            return []
    
    # ==============================================================================
    # RESULT PROCESSING HELPERS
    # ==============================================================================
    
    def extract_ship_from_result(self, result: Dict) -> str:
        """Extract ship name from result title or categories"""
        title = result.get('title', '').lower()
        categories = result.get('categories', [])
        
        # Known ship names
        ships = ['stardancer', 'adagio', 'pilgrim', 'sentinel', 'banshee', 'protector', 'manta', 'gigantes', 'caelian', 'enterprise']
        
        # Check title first
        for ship in ships:
            if ship in title:
                return ship.title()
        
        # Check categories
        if categories:
            for category in categories:
                category_lower = category.lower()
                for ship in ships:
                    if ship in category_lower:
                        return ship.title()
        
        return 'Unknown Ship'
    
    def extract_date_from_title(self, title: str) -> Optional[str]:
        """Extract date from title using various patterns"""
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',      # MM/DD/YYYY or M/D/YYYY
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', # YYYY-MM-DD or YYYY/MM/DD
            r'(\d{1,2}-\d{1,2}-\d{4})',      # MM-DD-YYYY
            r'(\d{4}\.\d{1,2}\.\d{1,2})'     # YYYY.MM.DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        
        return None
    
    def format_log_title(self, result: Dict) -> str:
        """Format a proper log title from result data"""
        original_title = result['title']
        ship_name = self.extract_ship_from_result(result)
        extracted_date = self.extract_date_from_title(original_title)
        
        # Create proper log title: "Shipname Mission Log"
        if ship_name and ship_name != 'Unknown Ship':
            log_title = f"{ship_name} Mission Log"
        else:
            log_title = "Mission Log"
        
        # Add date if extracted from title
        if extracted_date:
            log_title += f" - {extracted_date}"
        
        return log_title
    
    # ==============================================================================
    # UTILITY METHODS
    # ==============================================================================
    
    def update_content_accessed(self, page_ids: List[int]) -> bool:
        """Update content_accessed counter for the given page IDs"""
        if not page_ids:
            return True
            
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
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

    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                    
                    # Category breakdown
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

    def find_matching_categories(self, target_category: str, all_categories: List[str]) -> List[str]:
        """
        Find categories that match the target category with fuzzy matching.
        
        Args:
            target_category: The category to search for (e.g., "Characters")
            all_categories: List of all available categories
            
        Returns:
            List of matching categories, with exact matches first
        """
        if not target_category or not all_categories:
            return []
        
        target_lower = target_category.lower()
        exact_matches = []
        partial_matches = []
        
        for category in all_categories:
            category_lower = category.lower()
            
            # Exact match
            if category_lower == target_lower:
                exact_matches.append(category)
            # Partial matches - either contains or is contained
            elif target_lower in category_lower or category_lower in target_lower:
                partial_matches.append(category)
        
        # Return exact matches first, then partial matches
        matching_categories = exact_matches + partial_matches
        
        if matching_categories:
            print(f"   🎯 Found {len(matching_categories)} matching categories for '{target_category}': {matching_categories}")
        
        return matching_categories

    def search_with_category_matching(self, query: str, target_category: str, 
                                    limit: int = 10, order_by: str = 'relevance') -> List[Dict]:
        """
        Search with intelligent category matching.
        
        Args:
            query: Search terms
            target_category: Target category (may not match exactly)
            limit: Max results
            order_by: Sort order
            
        Returns:
            List of matching records
        """
        # Get all available categories
        all_categories = self.get_all_categories()
        
        # Find matching categories
        matching_categories = self.find_matching_categories(target_category, all_categories)
        
        if matching_categories:
            # Search with the matching categories
            return self.search(
                query=query,
                categories=matching_categories,
                limit=limit,
                order_by=order_by
            )
        else:
            # No matching categories found, search without category filter
            print(f"   ⚠️  No matching categories found for '{target_category}', searching all categories")
            return self.search(
                query=query,
                categories=None,
                limit=limit,
                order_by=order_by
            )

    # ==============================================================================
    # SPECIALIZED SEARCH METHODS
    # ==============================================================================
    
    def search_ships(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Search for ships with priority given to Active Starships over Inactive ones.
        
        Args:
            query: Ship name to search for
            limit: Max results
            
        Returns:
            List of ship results with active ships prioritized
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    print(f"🚢 SHIP SEARCH: '{query}' with active ship priority")
                    
                    # Get all ship categories
                    ship_categories = self.get_ship_categories()
                    
                    if not ship_categories:
                        print("   ⚠️  No ship categories available")
                        return []
                    
                    # Build query with ship category filter and active ship priority
                    ts_query = self._format_search_query(query)
                    
                    base_query = """
                        SELECT id, title, raw_content, url, categories,
                               CASE 
                                   WHEN to_tsvector('english', title) @@ to_tsquery('english', %s) THEN
                                       ts_rank(to_tsvector('english', title), to_tsquery('english', %s)) + 2.0
                                   ELSE 
                                       ts_rank(to_tsvector('english', raw_content), to_tsquery('english', %s))
                               END as rank,
                               CASE 
                                   WHEN 'Active Starships' = ANY(categories) THEN 3
                                   WHEN 'Starships' = ANY(categories) THEN 2
                                   WHEN 'Inactive Starships' = ANY(categories) THEN 1
                                   ELSE 0
                               END as ship_priority
                        FROM wiki_pages 
                        WHERE (
                            to_tsvector('english', title) @@ to_tsquery('english', %s) OR
                            to_tsvector('english', raw_content) @@ to_tsquery('english', %s)
                        )
                        AND categories IS NOT NULL 
                        AND array_length(categories, 1) > 0 
                        AND categories && %s
                        ORDER BY ship_priority DESC, rank DESC, id DESC
                        LIMIT %s
                    """
                    
                    params = [ts_query, ts_query, ts_query, ts_query, ts_query, ship_categories, limit]
                    
                    cur.execute(base_query, params)
                    results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   ✅ Found {len(results)} ship results")
                    
                    # Log the prioritization for debugging
                    for i, result in enumerate(results):
                        title = result.get('title', 'Unknown')
                        categories = result.get('categories', [])
                        ship_priority = result.get('ship_priority', 0)
                        priority_name = {3: 'Active', 2: 'Standard', 1: 'Inactive', 0: 'Other'}[ship_priority]
                        print(f"   {i+1}. {title} (Priority: {priority_name}) - Categories: {categories}")
                    
                    # Track content access for returned results
                    if results:
                        page_ids = [result['id'] for result in results]
                        self.update_content_accessed(page_ids)
                    
                    return results
                    
        except Exception as e:
            print(f"✗ Error in ship search: {e}")
            return []

# Global database controller instance
db_controller = None

def get_db_controller():
    """Get the global database controller instance"""
    global db_controller
    if db_controller is None:
        db_controller = FleetDatabaseController()
    return db_controller 