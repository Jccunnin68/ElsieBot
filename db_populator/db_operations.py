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
        # Database configuration for Docker container environment
        self.db_config = {
            'dbname': os.getenv('DB_NAME', 'elsiebrain'),
            'user': os.getenv('DB_USER', 'elsie'),
            'password': os.getenv('DB_PASSWORD', 'elsie123'),
            'host': os.getenv('DB_HOST', 'localhost'),  # Use localhost in development
            'port': os.getenv('DB_PORT', '5433')  # Use 5433 in development
        }
    
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
    
    def should_update_page(self, page_title: str, new_content_hash: str) -> bool:
        """Check if page should be updated based on content hash"""
        metadata = self.get_page_metadata(page_title)
        if not metadata:
            return True  # New page, should crawl
        
        # Check if content has changed
        return metadata.get('content_hash') != new_content_hash
    
    def save_page_to_database(self, page_data: Dict, content_processor) -> bool:
        """Save page data to the database (no content splitting)"""
        try:
            content = page_data['raw_content']
            title = page_data['title']
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Classify the page using full content
                    page_type, ship_name, log_date = content_processor.classify_page_type(
                        title, content
                    )
                    
                    # Check if page already exists
                    cur.execute("""
                        SELECT id FROM wiki_pages WHERE title = %s
                    """, (title,))
                    
                    existing_page = cur.fetchone()
                    
                    if existing_page:
                        # Update existing page
                        cur.execute("""
                            UPDATE wiki_pages 
                            SET raw_content = %s, url = %s, crawl_date = %s,
                                page_type = %s, ship_name = %s, log_date = %s, updated_at = NOW()
                            WHERE title = %s
                        """, (
                            content,
                            page_data['url'],
                            page_data['crawled_at'],
                            page_type,
                            ship_name,
                            log_date,
                            title
                        ))
                        print(f"  ✓ Updated existing page: {title} ({len(content):,} chars, type: {page_type})")
                    else:
                        # Insert new page
                        cur.execute("""
                            INSERT INTO wiki_pages 
                            (title, raw_content, url, crawl_date, page_type, ship_name, log_date)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            title,
                            content,
                            page_data['url'],
                            page_data['crawled_at'],
                            page_type,
                            ship_name,
                            log_date
                        ))
                        print(f"  ✓ Inserted new page: {title} ({len(content):,} chars, type: {page_type})")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"✗ Error saving page to database: {e}")
            return False
    
    def get_database_stats(self):
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Wiki pages stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_pages,
                            COUNT(CASE WHEN page_type = 'mission_log' THEN 1 END) as mission_logs,
                            COUNT(CASE WHEN page_type = 'ship_info' THEN 1 END) as ship_info,
                            COUNT(CASE WHEN page_type = 'personnel' THEN 1 END) as personnel,
                            COUNT(DISTINCT ship_name) as unique_ships
                        FROM wiki_pages
                    """)
                    wiki_stats = dict(cur.fetchone())
                    
                    # Metadata stats
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total_tracked_pages,
                            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_pages,
                            COUNT(CASE WHEN status = 'error' THEN 1 END) as error_pages,
                            MAX(last_crawled) as last_crawl_time
                        FROM page_metadata
                    """)
                    metadata_stats = dict(cur.fetchone())
                    
                    return {**wiki_stats, **metadata_stats}
        except Exception as e:
            logger.error(f"✗ Error getting database stats: {e}")
            return {} 