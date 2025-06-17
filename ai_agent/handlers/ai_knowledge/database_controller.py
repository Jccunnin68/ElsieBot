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
            query: Search terms
            categories: Optional category filter 
            limit: Max results
            order_by: 'relevance', 'chronological', 'id_desc', 'id_asc', 'random'
            ship_name: Optional ship name filter (searches in title)
        
        Returns:
            List of matching records with full content
        """
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
                    # Format the query for to_tsquery, looking for phrases
                    ts_query = ' & '.join(query.split())
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
        """Get categories that contain 'ship' or 'starship' from the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT unnest(categories) as category 
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        AND EXISTS (
                            SELECT 1 FROM unnest(categories) cat 
                            WHERE LOWER(cat) LIKE '%ship%' AND LOWER(cat) NOT LIKE '%log%'
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

# Global database controller instance
db_controller = None

def get_db_controller():
    """Get the global database controller instance"""
    global db_controller
    if db_controller is None:
        db_controller = FleetDatabaseController()
    return db_controller 