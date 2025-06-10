#!/usr/bin/env python3
"""
22nd Mobile Daedalus Fleet Wiki Crawler - Container Version
Extracts content from the wiki and stores directly in the elsiebrain PostgreSQL database.
Designed to run within the db_populator Docker container.
"""

import fandom
import time
import os
import json
import requests
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional, Tuple
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ship names for classification
SHIP_NAMES = [
    'voyager', 'defiant', 'enterprise', 'discovery', 'reliant', 'excelsior',
    'constitution', 'intrepid', 'sovereign', 'galaxy', 'miranda', 'oberth',
    'akira', 'steam runner', 'saber', 'norway', 'prometheus'
]

class WikiCrawlerContainer:
    def __init__(self):
        # Database configuration for Docker container environment
        self.db_config = {
            'dbname': os.getenv('DB_NAME', 'elsiebrain'),
            'user': os.getenv('DB_USER', 'elsie'),
            'password': os.getenv('DB_PASSWORD', 'elsie123'),
            'host': os.getenv('DB_HOST', 'localhost'),  # Use localhost in development
            'port': os.getenv('DB_PORT', '5433')  # Use 5433 in development
        }
        
        # MediaWiki API URL
        self.api_url = "https://22ndmobile.fandom.com/api.php"
        
        # Set the wiki to 22ndmobile
        fandom.set_wiki("22ndmobile")
    
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
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
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
                        (url, title, content_hash, last_crawled, crawl_count, status, last_error)
                        VALUES (%s, %s, %s, NOW(), 1, %s, %s)
                        ON CONFLICT (url) 
                        DO UPDATE SET
                            title = EXCLUDED.title,
                            content_hash = EXCLUDED.content_hash,
                            last_crawled = NOW(),
                            crawl_count = page_metadata.crawl_count + 1,
                            status = EXCLUDED.status,
                            last_error = EXCLUDED.last_error,
                            last_modified = NOW()
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
    
    def save_page_to_database(self, page_data: Dict) -> bool:
        """Save page data to the database"""
        try:
            # Check content length
            content = page_data['content']
            content_parts = []
            
            # If content is too long (>25000 chars), split it into parts
            MAX_CONTENT_LENGTH = 25000  # Reduced from 50000
            if len(content) > MAX_CONTENT_LENGTH:
                # First try to split on major section headers
                sections = re.split(r'(##\s+[^\n]+\n)', content)
                current_part = ""
                
                for section in sections:
                    # If adding this section would exceed the limit
                    if len(current_part) + len(section) > MAX_CONTENT_LENGTH:
                        # If the current section itself is too big
                        if len(section) > MAX_CONTENT_LENGTH:
                            # Split on subsections
                            subsections = re.split(r'(###\s+[^\n]+\n)', section)
                            for subsection in subsections:
                                # If subsection would exceed limit
                                if len(current_part) + len(subsection) > MAX_CONTENT_LENGTH:
                                    # If subsection itself is too big
                                    if len(subsection) > MAX_CONTENT_LENGTH:
                                        # Split on paragraphs
                                        paragraphs = subsection.split('\n\n')
                                        for paragraph in paragraphs:
                                            # If paragraph would exceed limit
                                            if len(current_part) + len(paragraph) + 2 > MAX_CONTENT_LENGTH:
                                                # If paragraph itself is too big
                                                if len(paragraph) > MAX_CONTENT_LENGTH:
                                                    # Split on sentences
                                                    sentences = re.split(r'([.!?]+\s+)', paragraph)
                                                    for sentence in sentences:
                                                        if len(current_part) + len(sentence) > MAX_CONTENT_LENGTH:
                                                            if current_part:
                                                                content_parts.append(current_part.strip())
                                                            current_part = sentence
                                                        else:
                                                            current_part += sentence
                                                else:
                                                    if current_part:
                                                        content_parts.append(current_part.strip())
                                                    current_part = paragraph + '\n\n'
                                            else:
                                                current_part += paragraph + '\n\n'
                                    else:
                                        if current_part:
                                            content_parts.append(current_part.strip())
                                        current_part = subsection
                                else:
                                    current_part += subsection
                        else:
                            if current_part:
                                content_parts.append(current_part.strip())
                            current_part = section
                    else:
                        current_part += section
                
                # Add the last part if it exists
                if current_part:
                    content_parts.append(current_part.strip())
            else:
                content_parts = [content]
            
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Classify the page
                    page_type, ship_name, log_date = self.classify_page_type(
                        page_data['title'], content_parts[0]  # Use first part for classification
                    )
                    
                    # Process each content part
                    for i, part_content in enumerate(content_parts, 1):
                        # Modify title for parts after the first
                        title = page_data['title']
                        if len(content_parts) > 1:
                            title = f"{title} (Part {i}/{len(content_parts)})"
                        
                        # Check if this part already exists
                        cur.execute("""
                            SELECT id FROM wiki_pages WHERE title = %s
                        """, (title,))
                        
                        existing_page = cur.fetchone()
                        
                        if existing_page:
                            # Update existing page
                            cur.execute("""
                                UPDATE wiki_pages 
                                SET content = %s, raw_content = %s, url = %s, crawl_date = %s,
                                    page_type = %s, ship_name = %s, log_date = %s, updated_at = NOW()
                                WHERE title = %s
                            """, (
                                part_content,
                                page_data.get('raw_content', part_content),
                                page_data['url'],
                                page_data['crawled_at'],
                                page_type,
                                ship_name,
                                log_date,
                                title
                            ))
                            print(f"  ✓ Updated existing page: {title}")
                        else:
                            # Insert new page
                            cur.execute("""
                                INSERT INTO wiki_pages 
                                (title, content, raw_content, url, crawl_date, page_type, ship_name, log_date)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                title,
                                part_content,
                                page_data.get('raw_content', part_content),
                                page_data['url'],
                                page_data['crawled_at'],
                                page_type,
                                ship_name,
                                log_date
                            ))
                            print(f"  ✓ Inserted new page: {title}")
                    
                    conn.commit()
                    return True
                    
        except Exception as e:
            print(f"✗ Error saving page to database: {e}")
            return False
    
    def get_all_page_titles_from_special_pages(self):
        """Get all page titles from the MediaWiki API"""
        logger.info("  📋 Fetching all page titles from MediaWiki API...")
        
        try:
            # Use the MediaWiki API to get all pages
            base_url = "https://22ndmobile.fandom.com/api.php"
            params = {
                'action': 'query',
                'list': 'allpages',
                'aplimit': '500',  # Get up to 500 pages
                'format': 'json'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            page_titles = []
            continue_token = None
            
            while True:
                if continue_token:
                    params['apcontinue'] = continue_token
                
                response = requests.get(base_url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Extract page titles
                if 'query' in data and 'allpages' in data['query']:
                    for page in data['query']['allpages']:
                        if 'title' in page:
                            page_titles.append(page['title'])
                
                # Check if there are more pages
                if 'continue' in data and 'apcontinue' in data['continue']:
                    continue_token = data['continue']['apcontinue']
                    time.sleep(1)  # Be nice to the API
                else:
                    break
            
            if page_titles:
                logger.info(f"  ✓ Found {len(page_titles)} pages from API")
                return sorted(page_titles)
            else:
                raise Exception("No pages found")
                
        except Exception as e:
            logger.error(f"  ✗ Error getting page titles: {e}")
            # Fallback to curated list
            page_titles = [
                "USS Stardancer", "USS Adagio", "USS Pilgrim", "USS Protector",
                "USS Manta", "Captain Marcus Blaine", "Large Magellanic Cloud Expedition",
                "Rendino-class Starship", "USS Voyager", "USS Enterprise",
                "USS Defiant", "USS Discovery", "USS Excelsior", "USS Intrepid",
                "USS Sovereign", "USS Galaxy", "USS Miranda", "USS Oberth",
                "USS Akira", "USS Steam Runner", "USS Saber", "USS Norway",
                "USS Prometheus", "22nd Mobile Daedalus Fleet", "The Primacy",
                "Samwise Blake", "Lilith", "Cetas", "Tatpha", "Beryxian",
                "Orzaul Gate", "Commander Tiberius Asada", "Commander Sif",
                "Lieutenant Commander Luka", "Lieutenant Commander Saiv Daly",
                "Lieutenant Commander Surithrae Alemyn", "Commander Priti Mehta",
                "Doctor Jiratha", "Lieutenant Commander Aija Bessley",
                "Ensign Maeve Tolena Blaine"
            ]
            logger.warning(f"  ⚠️  Using fallback list: {len(page_titles)} pages")
        
        return page_titles
    
    def get_page_content_from_api(self, page_title: str):
        """Get page content directly from MediaWiki API"""
        try:
            # First get the page ID
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'info|revisions',
                'rvprop': 'content',
                'rvslots': '*'
            }
            
            response = requests.get(self.api_url, params=params)
            data = response.json()
            
            if 'query' in data and 'pages' in data['query']:
                # Get the first (and only) page
                page = next(iter(data['query']['pages'].values()))
                
                if 'revisions' in page:
                    content = page['revisions'][0]['slots']['main']['*']
                    url = f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}"
                    
                    page_data = {
                        'title': page_title,
                        'url': url,
                        'content': content,
                        'raw_content': content,
                        'crawled_at': datetime.now()
                    }
                    
                    print(f"  ✓ Successfully extracted {len(content)} characters from API")
                    return page_data
                    
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error getting content from API: {e}")
            return None
            
    def extract_page_content(self, page_title: str):
        """Extract content from a single page"""
        try:
            print(f"Crawling: {page_title}")
            
            # First try fandom-py
            try:
                page = fandom.page(title=page_title)
                
                # Extract content parts
                content_parts = []
                
                # Add title
                if hasattr(page, 'title'):
                    content_parts.append(f"**{page.title}**\n")
                else:
                    content_parts.append(f"**{page_title}**\n")
                
                # Try to get plain text first as fallback
                if hasattr(page, 'plain_text') and page.plain_text:
                    content_parts.append(page.plain_text)
                
                # Add summary if available
                if hasattr(page, 'summary') and page.summary:
                    if not any(page.summary in part for part in content_parts):
                        content_parts.append(f"## Summary\n{page.summary}\n")
                
                # Get structured content
                if hasattr(page, 'content') and page.content:
                    try:
                        page_content = page.content
                        
                        # Handle main content before sections
                        if isinstance(page_content, dict):
                            if 'content' in page_content and page_content['content']:
                                content_parts.append(f"## Overview\n{page_content['content']}\n")
                            
                            # Handle infobox if present
                            if 'infobox' in page_content and page_content['infobox']:
                                content_parts.append(f"## Information\n{page_content['infobox']}\n")
                            
                            # Handle sections recursively
                            def process_sections(sections, level=2):
                                if not isinstance(sections, (list, tuple)):
                                    return
                                    
                                for section in sections:
                                    if not isinstance(section, dict):
                                        continue
                                        
                                    try:
                                        # Add section title with appropriate heading level
                                        if 'title' in section:
                                            content_parts.append(f"{'#' * level} {section['title']}\n")
                                        
                                        # Add section content
                                        if 'content' in section:
                                            if isinstance(section['content'], str):
                                                content_parts.append(f"{section['content']}\n")
                                            elif isinstance(section['content'], dict):
                                                if 'text' in section['content']:
                                                    content_parts.append(f"{section['content']['text']}\n")
                                        
                                        # Process subsections recursively
                                        if 'sections' in section and section['sections']:
                                            process_sections(section['sections'], level + 1)
                                    except Exception as e:
                                        print(f"  ⚠️  Error processing section: {e}")
                                        continue
                            
                            # Process all sections
                            try:
                                if 'sections' in page_content and page_content['sections']:
                                    process_sections(page_content['sections'])
                            except Exception as e:
                                print(f"  ⚠️  Error processing sections: {e}")
                        else:
                            # Handle plain text content
                            content_parts.append(f"## Content\n{page_content}\n")
                    except Exception as e:
                        print(f"  ⚠️  Error processing content: {e}")
                
                # Add sections if available separately
                if hasattr(page, 'sections') and page.sections:
                    try:
                        for section_title in page.sections[:10]:  # Limit to first 10 sections
                            try:
                                section_content = page.section(section_title)
                                if section_content:
                                    if isinstance(section_content, str):
                                        if len(section_content.strip()) > 10:
                                            content_parts.append(f"## {section_title}\n{section_content}\n")
                                    elif isinstance(section_content, dict):
                                        if 'text' in section_content and len(section_content['text'].strip()) > 10:
                                            content_parts.append(f"## {section_title}\n{section_content['text']}\n")
                            except Exception as e:
                                print(f"  ⚠️  Error getting section '{section_title}': {e}")
                                continue
                    except Exception as e:
                        print(f"  ⚠️  Error processing sections list: {e}")
                
                # Join all content
                full_content = '\n'.join(content_parts)
                
                # Clean up excessive whitespace
                full_content = re.sub(r'\n{3,}', '\n\n', full_content)
                full_content = full_content.strip()
                
                if full_content and len(full_content) > 100:
                    page_data = {
                        'title': page.title if hasattr(page, 'title') else page_title,
                        'url': page.url if hasattr(page, 'url') else f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'content': full_content,
                        'raw_content': full_content,
                        'crawled_at': datetime.now()
                    }
                    
                    print(f"  ✓ Successfully extracted {len(full_content)} characters")
                    return page_data
                else:
                    print(f"  ✗ Insufficient content extracted from fandom-py, trying API...")
                    return self.get_page_content_from_api(page_title)
                    
            except Exception as e:
                print(f"  ⚠️  Error with fandom-py: {e}, trying API...")
                return self.get_page_content_from_api(page_title)
                
        except Exception as e:
            print(f"Error crawling {page_title}: {e}")
            # Update metadata with error
            self.upsert_page_metadata(
                page_title, 
                f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}", 
                "", 
                status='error', 
                error_message=str(e)
            )
            
        return None
    
    def crawl_wiki_pages(self, use_comprehensive_list=False, force_update=False, limit=None):
        """Crawl wiki pages and save to database"""
        logger.info("🌐 Starting wiki crawl to elsiebrain database...")
        
        # Get page titles
        if use_comprehensive_list:
            page_titles = self.get_all_page_titles_from_special_pages()
        else:
            # Use a curated list for faster crawling
            page_titles = [
                "22nd Mobile Daedalus Fleet", "USS Stardancer", "USS Adagio", 
                "USS Pilgrim", "USS Protector", "USS Manta", "Captain Marcus Blaine",
                "Large Magellanic Cloud Expedition", "Rendino-class Starship",
                "Main Page", "USS Voyager", "USS Enterprise"
            ]
        
        # Limit results if specified
        if limit:
            page_titles = page_titles[:limit]
        
        successful_crawls = 0
        updated_pages = 0
        skipped_pages = 0
        
        for i, page_title in enumerate(page_titles, 1):
            logger.info(f"\n[{i}/{len(page_titles)}] Processing: {page_title}")
            
            # Check if we should update this page
            if not force_update:
                # First, do a quick content check
                page_data = self.extract_page_content(page_title)
                if page_data:
                    content_hash = self.calculate_content_hash(page_data['content'])
                    if not self.should_update_page(page_title, content_hash):
                        logger.info(f"  ⏭️  Skipping - no changes detected")
                        skipped_pages += 1
                        continue
            else:
                page_data = self.extract_page_content(page_title)
            
            if page_data:
                # Calculate content hash
                content_hash = self.calculate_content_hash(page_data['content'])
                
                # Save to database
                if self.save_page_to_database(page_data):
                    successful_crawls += 1
                    
                    # Update metadata
                    self.upsert_page_metadata(
                        page_data['title'],
                        page_data['url'],
                        content_hash,
                        status='active'
                    )
                    updated_pages += 1
            
            # Be respectful to the API
            time.sleep(2)
        
        logger.info(f"\n🌐 Wiki crawling complete!")
        logger.info(f"✓ Successfully crawled: {successful_crawls} pages")
        logger.info(f"✓ Updated: {updated_pages} pages")
        logger.info(f"⏭️  Skipped (unchanged): {skipped_pages} pages")
        
        return successful_crawls
    
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

def main():
    """Main crawler function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("22nd Mobile Daedalus Fleet Wiki Crawler - Database Version")
            print("=" * 60)
            print("Usage:")
            print("  python wiki_crawler_db.py                    # Standard crawl (~15 curated pages)")
            print("  python wiki_crawler_db.py --comprehensive    # Comprehensive crawl (all pages)")
            print("  python wiki_crawler_db.py --force            # Force update all pages")
            print("  python wiki_crawler_db.py --stats            # Show database statistics")
            print("  python wiki_crawler_db.py \"PAGE_TITLE\"      # Crawl specific page")
            print("=" * 60)
            return
        
        # Check for options
        use_comprehensive = "--comprehensive" in sys.argv
        force_update = "--force" in sys.argv
        show_stats = "--stats" in sys.argv
        
        # Check for specific page title
        specific_page = None
        for arg in sys.argv[1:]:
            if not arg.startswith("--"):
                specific_page = arg
                break
    else:
        use_comprehensive = False
        force_update = False
        show_stats = False
        specific_page = None
    
    try:
        crawler = WikiCrawlerContainer()
        
        if show_stats:
            stats = crawler.get_database_stats()
            print("\n📈 Database Statistics:")
            print(f"   Total Pages: {stats.get('total_pages', 0)}")
            print(f"   Mission Logs: {stats.get('mission_logs', 0)}")
            print(f"   Ship Info: {stats.get('ship_info', 0)}")
            print(f"   Personnel: {stats.get('personnel', 0)}")
            print(f"   Unique Ships: {stats.get('unique_ships', 0)}")
            print(f"   Tracked Pages: {stats.get('total_tracked_pages', 0)}")
            print(f"   Active Pages: {stats.get('active_pages', 0)}")
            print(f"   Error Pages: {stats.get('error_pages', 0)}")
            print(f"   Last Crawl: {stats.get('last_crawl_time', 'Never')}")
            return
        
        if specific_page:
            print(f"Crawling specific page: {specific_page}")
            page_data = crawler.extract_page_content(specific_page)
            if page_data:
                content_hash = crawler.calculate_content_hash(page_data['content'])
                if crawler.save_page_to_database(page_data):
                    crawler.upsert_page_metadata(
                        page_data['title'],
                        page_data['url'],
                        content_hash,
                        status='active'
                    )
                    print("✓ Successfully crawled and saved page")
                else:
                    print("✗ Failed to save page to database")
            return
        
        if use_comprehensive:
            print("⚠️  WARNING: Comprehensive crawl will attempt to crawl ALL pages!")
            print("⚠️  This will take a very long time.")
            print("⚠️  Press Ctrl+C to cancel, or wait 5 seconds to continue...")
            time.sleep(5)
        
        # Crawl pages
        successful_crawls = crawler.crawl_wiki_pages(use_comprehensive, force_update)
        
        if successful_crawls > 0:
            # Show final stats
            stats = crawler.get_database_stats()
            print(f"\n📈 Final Database Statistics:")
            print(f"   Total Pages: {stats.get('total_pages', 0)}")
            print(f"   Mission Logs: {stats.get('mission_logs', 0)}")
            print(f"   Ship Info: {stats.get('ship_info', 0)}")
            print(f"   Personnel: {stats.get('personnel', 0)}")
            print(f"   Unique Ships: {stats.get('unique_ships', 0)}")
            print(f"   Tracked Pages: {stats.get('total_tracked_pages', 0)}")
            
            print("\n✅ Wiki crawling to elsiebrain database completed successfully!")
        else:
            print("❌ No content was crawled. Please check your internet connection and database.")
            
    except Exception as e:
        print(f"❌ Error during crawling: {e}")
        print("Make sure:")
        print("- The elsiebrain database exists and is accessible")
        print("- You have installed required packages: pip install fandom-py psycopg2-binary requests beautifulsoup4")

if __name__ == "__main__":
    main() 