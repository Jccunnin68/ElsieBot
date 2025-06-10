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
                    ship_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Search pages using full-text search"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # Build the query
                    base_query = """
                        SELECT id, title, content, page_type, ship_name, log_date,
                               ts_rank(to_tsvector('english', title || ' ' || content), 
                                      plainto_tsquery('english', %s)) as rank
                        FROM wiki_pages 
                        WHERE to_tsvector('english', title || ' ' || content) @@ plainto_tsquery('english', %s)
                    """
                    
                    params = [query, query]
                    
                    if page_type:
                        base_query += " AND page_type = %s"
                        params.append(page_type)
                    
                    if ship_name:
                        base_query += " AND ship_name = %s"
                        params.append(ship_name)
                    
                    base_query += " ORDER BY rank DESC, log_date DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(base_query, params)
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            print(f"✗ Error searching pages: {e}")
            return []
    
    def get_log_content(self, query: str, max_chars: int = 8000) -> str:
        """Get mission log content for a query"""
        # Search specifically for mission logs
        results = self.search_pages(query, page_type="mission_log", limit=5)
        
        if not results:
            return ""
        
        log_contents = []
        total_chars = 0
        
        for result in results:
            title = result['title']
            content = result['content']
            
            # Format the log
            formatted_log = f"**{title}**\n{content}"
            
            if total_chars + len(formatted_log) <= max_chars:
                log_contents.append(formatted_log)
                total_chars += len(formatted_log)
            else:
                # Add partial content if it fits
                remaining_chars = max_chars - total_chars
                if remaining_chars > 200:
                    log_contents.append(formatted_log[:remaining_chars] + "...[LOG TRUNCATED]")
                break
        
        return '\n\n---\n\n'.join(log_contents)
    
    def get_relevant_context(self, query: str, max_chars: int = 3000) -> str:
        """Get relevant wiki context for general queries"""
        results = self.search_pages(query, limit=10)
        
        if not results:
            return ""
        
        context_parts = []
        total_chars = 0
        
        for result in results:
            title = result['title']
            content = result['content'][:1000]  # Limit individual content
            
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
        
        return '\n\n---\n\n'.join(context_parts)
    
    def get_ship_info(self, ship_name: str) -> List[Dict]:
        """Get all information about a specific ship"""
        return self.search_pages(ship_name, ship_name=ship_name.lower(), limit=20)
    
    def get_recent_logs(self, ship_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get recent mission logs"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    query = """
                        SELECT id, title, content, ship_name, log_date
                        FROM wiki_pages 
                        WHERE page_type = 'mission_log'
                    """
                    params = []
                    
                    if ship_name:
                        query += " AND ship_name = %s"
                        params.append(ship_name.lower())
                    
                    query += " ORDER BY log_date DESC LIMIT %s"
                    params.append(limit)
                    
                    cur.execute(query, params)
                    return [dict(row) for row in cur.fetchall()]
                    
        except Exception as e:
            print(f"✗ Error getting recent logs: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_pages,
                            COUNT(CASE WHEN page_type = 'mission_log' THEN 1 END) as mission_logs,
                            COUNT(CASE WHEN page_type = 'ship_info' THEN 1 END) as ship_info,
                            COUNT(CASE WHEN page_type = 'personnel' THEN 1 END) as personnel,
                            COUNT(DISTINCT ship_name) as unique_ships
                        FROM wiki_pages
                    """)
                    return dict(cur.fetchone())
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