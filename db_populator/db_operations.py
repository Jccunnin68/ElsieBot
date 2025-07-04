#!/usr/bin/env python3
"""
Database Operations for 22nd Mobile Daedalus Fleet Wiki Crawler
Handles database connections, metadata management, and page saving.
"""

import os
import time
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Handles all database operations for the wiki crawler"""
    
    def __init__(self):
        # Database configuration - auto-detect Docker vs local environment
        # When running in Docker, DB_HOST will be set to 'elsiebrain_db'
        # When running locally, we use localhost:5433
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5433' if db_host == 'localhost' else '5432')
        
        self.db_config = {
            'dbname': os.getenv('DB_NAME', 'elsiebrain'),
            'user': os.getenv('DB_USER', 'elsie'),
            'password': os.getenv('DB_PASSWORD', 'elsie123'),
            'host': db_host,
            'port': db_port
        }
        
        print(f"🔧 Database config: {self.db_config['user']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['dbname']}")
        
        # Detect environment
        if db_host == 'elsiebrain_db':
            print("🐳 Running in Docker container mode")
        else:
            print("💻 Running in local development mode")
    
    def get_connection(self):
        """Get database connection"""
        conn = psycopg2.connect(**self.db_config)
        return conn
    
    def ensure_database_connection(self):
        """Ensure database connection is working"""
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        logger.info("✓ Connected to elsiebrain database successfully")
                        return True
            except Exception as e:
                retry_count += 1
                logger.warning(f"   ⏳ Attempt {retry_count}/{max_retries} - Database not ready: {e}")
                time.sleep(2)
        
        logger.error("❌ Failed to connect to elsiebrain database")
        raise Exception("Database connection failed")
    
    def get_page_metadata(self, page_title: str) -> Optional[Dict]:
        """Get existing metadata for a page"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM page_metadata 
                        WHERE title = %s
                    """, (page_title,))
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"✗ Error getting page metadata for '{page_title}': {e}")
            return None
    
    def upsert_page_metadata(self, page_title: str, url: str, content_hash: str, status: str = 'active', error_message: str = None):
        """Insert or update page metadata"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO page_metadata 
                        (url, title, content_hash, last_crawled, crawl_count, status, error_message)
                        VALUES (%s, %s, %s, NOW(), 1, %s, %s)
                        ON CONFLICT (title) 
                        DO UPDATE SET
                            url = EXCLUDED.url,
                            content_hash = EXCLUDED.content_hash,
                            last_crawled = NOW(),
                            crawl_count = page_metadata.crawl_count + 1,
                            status = EXCLUDED.status,
                            error_message = EXCLUDED.error_message,
                            updated_at = NOW()
                    """, (url, page_title, content_hash, status, error_message))
                    conn.commit()
        except Exception as e:
            print(f"✗ Error upserting page metadata: {e}")
    
    def should_update_page_by_touched(self, page_title: str, remote_touched: str) -> bool:
        """Check if page should be updated based on MediaWiki touched timestamp"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT touched FROM wiki_pages WHERE title = %s
                    """, (page_title,))
                    result = cur.fetchone()
                    
                    if not result:
                        return True  # New page, should update
                    
                    local_touched = result['touched']
                    if not local_touched:
                        return True  # No local touched data, should update
                    
                    if not remote_touched:
                        return False  # No remote touched data, don't update
                    
                    # Convert remote touched timestamp
                    try:
                        # Parse remote timestamp (MediaWiki format with 'Z' suffix = UTC)
                        remote_dt = datetime.fromisoformat(remote_touched.replace('Z', '+00:00'))
                        # Convert to naive UTC datetime for comparison
                        remote_dt_naive = remote_dt.replace(tzinfo=None)
                        
                        # Parse local timestamp (database TIMESTAMP without timezone - stored as naive UTC)
                        if isinstance(local_touched, datetime):
                            # Database datetime object - already naive UTC
                            local_dt_naive = local_touched
                        else:
                            # String format - parse as naive UTC
                            local_dt_naive = datetime.fromisoformat(str(local_touched))
                        
                        # Update if remote is newer than local (both naive UTC)
                        should_update = remote_dt_naive > local_dt_naive
                        if should_update:
                            print(f"  🔄 Page '{page_title}' needs update: remote {remote_dt_naive} > local {local_dt_naive}")
                        else:
                            print(f"  ✓ Page '{page_title}' is current: remote {remote_dt_naive} <= local {local_dt_naive}")
                        
                        return should_update
                        
                    except Exception as e:
                        print(f"  ⚠️  Error comparing timestamps for '{page_title}': {e}")
                        return True  # On error, update to be safe
                        
        except Exception as e:
            print(f"  ⚠️  Error checking update status for '{page_title}': {e}")
            return True  # On error, update to be safe
    
    def should_update_page(self, page_title: str, new_content_hash: str) -> bool:
        """Check if page should be updated based on content hash"""
        metadata = self.get_page_metadata(page_title)
        if not metadata:
            return True  # New page, should crawl
        
        # Check if content has changed
        return metadata.get('content_hash') != new_content_hash
    
    def save_page_to_database(self, page_data: Dict, content_processor) -> bool:
        """Save page content to database using clean schema with categories and MediaWiki metadata"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    title = page_data['title']
                    
                    # Process the content using the appropriate processor (log vs. standard)
                    content = content_processor.process_content(title, page_data)
                    
                    # Get real categories from page data (no classification)
                    categories = content_processor.get_categories_from_page_data(page_data)
                    
                    # Extract MediaWiki metadata
                    canonical_url = page_data.get('canonical_url') or page_data.get('url', '')
                    touched = page_data.get('touched')
                    
                    # Convert MediaWiki touched timestamp if present
                    touched_timestamp = None
                    if touched:
                        try:
                            # MediaWiki format: "2025-05-13T15:09:05Z"
                            # Convert to UTC and then to naive datetime for database storage
                            touched_dt = datetime.fromisoformat(touched.replace('Z', '+00:00'))
                            touched_timestamp = touched_dt.replace(tzinfo=None)  # Store as naive UTC datetime
                        except Exception as e:
                            print(f"      ⚠️  Could not parse touched timestamp '{touched}': {e}")
                    
                    # Check for existing page
                    cur.execute("SELECT id FROM wiki_pages WHERE title = %s", (title,))
                    existing_page = cur.fetchone()
                    
                    if existing_page:
                        # Update existing page with clean schema + metadata
                        cur.execute("""
                            UPDATE wiki_pages 
                            SET raw_content = %s, url = %s, crawl_date = %s,
                                touched = %s, categories = %s, updated_at = NOW()
                            WHERE title = %s
                        """, (
                            content,
                            canonical_url,
                            page_data['crawled_at'],
                            touched_timestamp,
                            categories,
                            title
                        ))
                        print(f"  ✓ Updated existing page: {title} ({len(content):,} chars, categories: {categories}, touched: {touched})")
                    else:
                        # Insert new page with clean schema + metadata
                        cur.execute("""
                            INSERT INTO wiki_pages 
                            (title, raw_content, url, crawl_date, touched, categories)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            title,
                            content,
                            canonical_url,
                            page_data['crawled_at'],
                            touched_timestamp,
                            categories
                        ))
                        print(f"  ✓ Inserted new page: {title} ({len(content):,} chars, categories: {categories}, touched: {touched})")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"✗ Error saving page to database: {e}")
            return False
    
    def get_database_stats(self):
        """Get database statistics using categories"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Wiki pages stats with categories
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_pages,
                            COUNT(CASE WHEN categories IS NOT NULL AND array_length(categories, 1) > 0 THEN 1 END) as pages_with_categories,
                            COUNT(CASE WHEN categories IS NULL OR array_length(categories, 1) IS NULL THEN 1 END) as pages_without_categories,
                            AVG(LENGTH(raw_content)) as avg_content_length,
                            MAX(LENGTH(raw_content)) as max_content_length
                        FROM wiki_pages
                    """)
                    wiki_stats = dict(cur.fetchone())
                    
                    # Category distribution
                    cur.execute("""
                        SELECT unnest(categories) as category, COUNT(*) as count 
                        FROM wiki_pages 
                        WHERE categories IS NOT NULL 
                        GROUP BY unnest(categories) 
                        ORDER BY count DESC
                    """)
                    category_stats = [dict(row) for row in cur.fetchall()]
                    
                    # Metadata stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_tracked_pages,
                            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_pages,
                            COUNT(CASE WHEN status != 'active' THEN 1 END) as error_pages
                        FROM page_metadata
                    """)
                    metadata_stats = dict(cur.fetchone())
                    
                    return {
                        'wiki_stats': wiki_stats,
                        'category_stats': category_stats,
                        'metadata_stats': metadata_stats
                    }
                    
        except Exception as e:
            print(f"✗ Error getting database stats: {e}")
            return {} 