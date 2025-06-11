#!/usr/bin/env python3
"""
Setup script for elsiebrain PostgreSQL database
This script creates the database schema and imports data from the flat file.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime
import sys
import hashlib

# Ship names for classification
SHIP_NAMES = [
    'voyager', 'defiant', 'enterprise', 'discovery', 'reliant', 'excelsior',
    'constitution', 'intrepid', 'sovereign', 'galaxy', 'miranda', 'oberth',
    'akira', 'steam runner', 'saber', 'norway', 'prometheus'
]

class ElsieBrainSetup:
    def __init__(self, db_name="elsiebrain", db_user="elsie", db_password="elsie123", db_host="localhost", db_port="5432"):
        self.db_config = {
            'dbname': db_name,
            'user': db_user,
            'password': db_password,
            'host': db_host,
            'port': db_port
        }
        self.admin_config = {
            'dbname': 'postgres',  # Connect to default postgres db for admin operations
            'user': db_user,
            'password': db_password,
            'host': db_host,
            'port': db_port
        }
    
    def get_connection(self, use_admin=False):
        """Get database connection"""
        config = self.admin_config if use_admin else self.db_config
        return psycopg2.connect(**config)
    
    def create_database(self):
        """Create the elsiebrain database if it doesn't exist"""
        try:
            with self.get_connection(use_admin=True) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    # Check if database exists
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_config['dbname'],))
                    if not cur.fetchone():
                        cur.execute(f"CREATE DATABASE {self.db_config['dbname']}")
                        print(f"✓ Created database '{self.db_config['dbname']}'")
                    else:
                        print(f"✓ Database '{self.db_config['dbname']}' already exists")
        except Exception as e:
            print(f"✗ Error creating database: {e}")
            raise
    
    def create_schema(self):
        """Create database tables and indexes"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Create pages table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS wiki_pages (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(255) NOT NULL,
                            content TEXT NOT NULL,
                            raw_content TEXT NOT NULL,
                            url VARCHAR(500),
                            crawl_date TIMESTAMP,
                            page_type VARCHAR(50),
                            ship_name VARCHAR(100),
                            log_date DATE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create page metadata tracking table for differential updates
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS page_metadata (
                            id SERIAL PRIMARY KEY,
                            page_title VARCHAR(255) NOT NULL UNIQUE,
                            url VARCHAR(500) NOT NULL,
                            last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_modified TIMESTAMP,
                            content_hash VARCHAR(64),
                            crawl_count INTEGER DEFAULT 1,
                            status VARCHAR(20) DEFAULT 'active',
                            error_message TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Create full-text search indexes
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_wiki_pages_title_gin 
                        ON wiki_pages USING gin(to_tsvector('english', title));
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_wiki_pages_content_gin 
                        ON wiki_pages USING gin(to_tsvector('english', content));
                    """)
                    
                    # Create regular indexes for common queries
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_wiki_pages_page_type 
                        ON wiki_pages(page_type);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_wiki_pages_ship_name 
                        ON wiki_pages(ship_name);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_wiki_pages_log_date 
                        ON wiki_pages(log_date);
                    """)
                    
                    # Create indexes for page metadata tracking
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_page_metadata_title 
                        ON page_metadata(page_title);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_page_metadata_last_crawled 
                        ON page_metadata(last_crawled);
                    """)
                    
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_page_metadata_status 
                        ON page_metadata(status);
                    """)
                    
                    conn.commit()
                    print("✓ Database schema created successfully")
        except Exception as e:
            print(f"✗ Error creating schema: {e}")
            raise
    
    def classify_page_type(self, title: str, content: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Classify page type and extract metadata"""
        title_lower = title.lower()
        
        # Check if it's a ship log (date pattern)
        date_pattern = r'(\d{4}/\d{1,2}/\d{1,2})|(\d{1,2}/\d{1,2}/\d{4})'
        if re.search(date_pattern, title):
            # Extract ship name
            ship_name = None
            for ship in SHIP_NAMES:
                if ship in title_lower:
                    ship_name = ship
                    break
            
            # Extract date
            log_date = self.extract_log_date(title)
            return "mission_log", ship_name, log_date
        
        # Check if it's a ship info page
        ship_pattern = r'uss\s+(\w+)|(\w+)\s+\(ncc-\d+\)'
        if re.search(ship_pattern, title_lower):
            ship_name = None
            for ship in SHIP_NAMES:
                if ship in title_lower:
                    ship_name = ship
                    break
            return "ship_info", ship_name, None
        
        # Check if it's a character/personnel page
        if any(keyword in title_lower for keyword in ['captain', 'commander', 'lieutenant', 'ensign', 'admiral']):
            return "personnel", None, None
        
        # Check if it's a location/system page
        if any(keyword in title_lower for keyword in ['system', 'planet', 'station', 'starbase']):
            return "location", None, None
        
        # Default to general article
        return "general", None, None
    
    def extract_log_date(self, title: str) -> Optional[str]:
        """Extract and normalize log date from title"""
        # Pattern: YYYY/M/D or YYYY/MM/DD
        date_match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', title)
        if date_match:
            year, month, day = date_match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Pattern: M/D/YYYY or MM/DD/YYYY
        date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', title)
        if date_match:
            month, day, year = date_match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    
    def clear_existing_data(self):
        """Clear all existing data from wiki_pages table"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM wiki_pages")
                    cur.execute("DELETE FROM page_metadata")
                    conn.commit()
                    print("✓ Cleared existing data from both wiki_pages and page_metadata tables")
        except Exception as e:
            print(f"✗ Error clearing existing data: {e}")
            raise
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def upsert_page_metadata(self, page_title: str, url: str, content_hash: str, crawl_date):
        """Insert or update page metadata"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO page_metadata 
                        (page_title, url, last_crawled, content_hash, crawl_count, status)
                        VALUES (%s, %s, %s, %s, 1, 'active')
                        ON CONFLICT (page_title) 
                        DO UPDATE SET
                            url = EXCLUDED.url,
                            last_crawled = EXCLUDED.last_crawled,
                            content_hash = EXCLUDED.content_hash,
                            crawl_count = page_metadata.crawl_count + 1,
                            status = 'active',
                            updated_at = NOW()
                    """, (page_title, url, crawl_date, content_hash))
        except Exception as e:
            print(f"✗ Error upserting page metadata: {e}")
    
    def import_flat_file(self, file_path: str):
        """Import data from the existing flat file"""
        print(f"🔄 Importing data from {file_path}...")
        
        if not os.path.exists(file_path):
            print(f"✗ File not found: {file_path}")
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by the separator
            pages = content.split('=' * 80)
            imported_count = 0
            print(f"  📋 Found {len(pages)} page sections to process")
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    processed_pages = 0
                    for page in pages:
                        if not page.strip():
                            continue
                        processed_pages += 1
                        
                        lines = page.split('\n')
                        page_data = {
                            'title': '',
                            'content': '',
                            'raw': page,
                            'url': '',
                            'crawl_date': None
                        }
                        
                        # Parse page data
                        content_lines = []
                        in_content = False
                        header_section = True
                        
                        for line in lines:
                            line_stripped = line.strip()
                            
                            # Skip empty lines
                            if not line_stripped:
                                continue
                                
                            # Parse header fields
                            if line_stripped.startswith('PAGE:'):
                                page_data['title'] = line_stripped.replace('PAGE:', '').strip()
                                continue
                            elif line_stripped.startswith('URL:'):
                                page_data['url'] = line_stripped.replace('URL:', '').strip()
                                continue
                            elif line_stripped.startswith('CRAWLED:'):
                                try:
                                    crawl_str = line_stripped.replace('CRAWLED:', '').strip()
                                    page_data['crawl_date'] = datetime.fromisoformat(crawl_str.replace('Z', '+00:00'))
                                except:
                                    pass
                                header_section = False  # After CRAWLED, content starts
                                continue
                            elif line_stripped.startswith('END OF PAGE:'):
                                break
                            elif line_stripped.startswith('=' * 10):  # Skip separator lines
                                continue
                            
                            # After header section, everything is content
                            if not header_section and line_stripped:
                                content_lines.append(line.rstrip())
                        
                        page_data['content'] = '\n'.join(content_lines).strip()
                        
                        # Debug logging for first few pages
                        if processed_pages <= 3:
                            print(f"  🔍 Processing page: Title='{page_data['title'][:30]}', Content length={len(page_data['content'])}")
                        
                        if page_data['title'] and page_data['content']:
                            # Classify the page
                            page_type, ship_name, log_date = self.classify_page_type(
                                page_data['title'], page_data['content']
                            )
                            
                            # Insert into database
                            cur.execute("""
                                INSERT INTO wiki_pages 
                                (title, content, raw_content, url, crawl_date, page_type, ship_name, log_date)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                page_data['title'],
                                page_data['content'],
                                page_data['raw'],
                                page_data['url'],
                                page_data['crawl_date'],
                                page_type,
                                ship_name,
                                log_date
                            ))
                            imported_count += 1
                            
                            # Debug logging for first few pages
                            if imported_count <= 3:
                                print(f"  📄 Imported: {page_data['title'][:50]}... (Type: {page_type})")
                
                # Now populate page metadata for all imported pages
                print("🔄 Populating page metadata...")
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT title, url, content, crawl_date FROM wiki_pages
                    """)
                    for row in cur.fetchall():
                        title, url, content, crawl_date = row
                        content_hash = self.calculate_content_hash(content)
                        self.upsert_page_metadata(title, url or "", content_hash, crawl_date)
                
                conn.commit()
                print(f"✓ Imported {imported_count} pages to database")
                
        except Exception as e:
            print(f"✗ Error importing flat file: {e}")
            raise
    
    def get_stats(self):
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
            print(f"✗ Error getting stats: {e}")
            return {}

def main():
    """Main setup function"""
    if len(sys.argv) < 2:
        print("Usage: python setup_elsiebrain_db.py <flat_file_path> [--clear]")
        print("  --clear: Clear existing data before import")
        sys.exit(1)
    
    flat_file_path = sys.argv[1]
    clear_data = '--clear' in sys.argv
    
    print("🧠 Setting up elsiebrain database...")
    
    setup = ElsieBrainSetup()
    
    try:
        # Create database
        setup.create_database()
        
        # Create schema
        setup.create_schema()
        
        # Clear existing data if requested
        if clear_data:
            setup.clear_existing_data()
        
        # Import data
        setup.import_flat_file(flat_file_path)
        
        # Print final stats
        stats = setup.get_stats()
        print(f"\n📈 Final Database Statistics:")
        print(f"   Total Pages: {stats.get('total_pages', 0)}")
        print(f"   Mission Logs: {stats.get('mission_logs', 0)}")
        print(f"   Ship Info: {stats.get('ship_info', 0)}")
        print(f"   Personnel: {stats.get('personnel', 0)}")
        print(f"   Unique Ships: {stats.get('unique_ships', 0)}")
        print(f"   Tracked Pages: {stats.get('total_tracked_pages', 0)}")
        print(f"   Active Pages: {stats.get('active_pages', 0)}")
        print(f"   Error Pages: {stats.get('error_pages', 0)}")
        print(f"   Last Crawl: {stats.get('last_crawl_time', 'Never')}")
        
        print(f"\n✅ elsiebrain database setup completed successfully!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 