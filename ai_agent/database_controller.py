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
        """Search pages using hierarchical search: titles first, then content"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    
                    # STEP 1: Search for title matches first (highest priority)
                    print(f"🔍 HIERARCHICAL SEARCH - Step 1: Title search for '{query}'")
                    
                    title_query = """
                        SELECT id, title, content, page_type, ship_name, log_date,
                               ts_rank(to_tsvector('english', title), 
                                      plainto_tsquery('english', %s)) as rank
                        FROM wiki_pages 
                        WHERE to_tsvector('english', title) @@ plainto_tsquery('english', %s)
                    """
                    
                    title_params = [query, query]
                    
                    if page_type:
                        title_query += " AND page_type = %s"
                        title_params.append(page_type)
                    
                    if ship_name:
                        title_query += " AND ship_name = %s"
                        title_params.append(ship_name)
                    
                    title_query += " ORDER BY rank DESC, log_date DESC LIMIT %s"
                    title_params.append(limit)
                    
                    cur.execute(title_query, title_params)
                    title_results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   📊 Title search found {len(title_results)} results")
                    
                    # Debug: Show first 50 chars of each title result
                    for i, result in enumerate(title_results[:3]):  # Show max 3 for brevity
                        title_preview = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
                        content_preview = result['raw_content'][:50] + "..." if len(result['raw_content']) > 50 else result['raw_content']
                        print(f"      📄 Result {i+1}: Title='{title_preview}' Content='{content_preview}'")
                    
                    # If we have good title matches, return them
                    if len(title_results) >= 3:
                        print(f"✅ HIERARCHICAL SEARCH - Using title results ({len(title_results)} found)")
                        return title_results
                    
                    # STEP 2: Fall back to content search if title search insufficient
                    print(f"🔍 HIERARCHICAL SEARCH - Step 2: Content search (insufficient title results)")
                    
                    content_query = """
                        SELECT id, title, raw_content, page_type, ship_name, log_date,
                               ts_rank(to_tsvector('english', raw_content), 
                                      plainto_tsquery('english', %s)) as rank
                        FROM wiki_pages 
                        WHERE to_tsvector('english', raw_content) @@ plainto_tsquery('english', %s)
                    """
                    
                    content_params = [query, query]
                    
                    if page_type:
                        content_query += " AND page_type = %s"
                        content_params.append(page_type)
                    
                    if ship_name:
                        content_query += " AND ship_name = %s"
                        content_params.append(ship_name)
                    
                    # Exclude already found title results
                    if title_results:
                        title_ids = [str(r['id']) for r in title_results]
                        content_query += f" AND id NOT IN ({','.join(['%s'] * len(title_ids))})"
                        content_params.extend(title_ids)
                    
                    remaining_limit = limit - len(title_results)
                    content_query += " ORDER BY rank DESC, log_date DESC LIMIT %s"
                    content_params.append(remaining_limit)
                    
                    cur.execute(content_query, content_params)
                    content_results = [dict(row) for row in cur.fetchall()]
                    
                    print(f"   📊 Content search found {len(content_results)} results")
                    
                    # Debug: Show first 50 chars of each content result
                    for i, result in enumerate(content_results[:3]):  # Show max 3 for brevity
                        title_preview = result['title'][:50] + "..." if len(result['title']) > 50 else result['title']
                        content_preview = result['raw_content'][:50] + "..." if len(result['raw_content']) > 50 else result['raw_content']
                        print(f"      📄 Result {i+1}: Title='{title_preview}' Content='{content_preview}'")
                    
                    # Combine results: title matches first, then content matches
                    combined_results = title_results + content_results
                    
                    print(f"✅ HIERARCHICAL SEARCH - Combined results: {len(title_results)} title + {len(content_results)} content = {len(combined_results)} total")
                    
                    return combined_results
                    
        except Exception as e:
            print(f"✗ Error in hierarchical search: {e}")
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
            content = result['raw_content']
            
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
            content = result['raw_content'][:10000]  # Limit individual content
            
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
                        SELECT id, title, raw_content, ship_name, log_date
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
                    
                    # First, let's see what we're working with
                    cur.execute("""
                        SELECT COUNT(*) as total_mission_logs,
                               COUNT(CASE WHEN ship_name IS NULL OR ship_name = '' THEN 1 END) as missing_ship_names
                        FROM wiki_pages 
                        WHERE page_type = 'mission_log'
                    """)
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
                        cur.execute("""
                            UPDATE wiki_pages 
                            SET ship_name = %s 
                            WHERE page_type = 'mission_log' 
                            AND (ship_name IS NULL OR ship_name = '' OR ship_name = 'None')
                            AND title ~* %s
                        """, (ship_name.lower(), pattern))
                        
                        count = cur.rowcount
                        if count > 0:
                            updated_count += count
                            print(f"  ✓ Updated {count} entries for {ship_name}")
                    
                    # Check results
                    cur.execute("""
                        SELECT COUNT(*) as total_mission_logs,
                               COUNT(CASE WHEN ship_name IS NULL OR ship_name = '' OR ship_name = 'None' THEN 1 END) as missing_ship_names
                        FROM wiki_pages 
                        WHERE page_type = 'mission_log'
                    """)
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
                    cur.execute("""
                        DELETE FROM wiki_pages 
                        WHERE LENGTH(content) < 50 
                        AND page_type = 'general'
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

# Global database controller instance
db_controller = None

def get_db_controller():
    """Get the global database controller instance"""
    global db_controller
    if db_controller is None:
        db_controller = FleetDatabaseController()
    return db_controller 