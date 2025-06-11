#!/usr/bin/env python3
"""
22nd Mobile Daedalus Fleet Wiki Crawler - Container Version
Extracts content from the wiki and stores directly in the elsiebrain PostgreSQL database.
Designed to run within the db_populator Docker container.
"""

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

# Ship names for classification - Updated with actual 22nd Mobile Fleet ships
SHIP_NAMES = [
    # 22nd Mobile Daedalus Fleet Ships
    'stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel',
    'caelian', 'montagnier', 'faraday', 'cook', 'mjolnir', 'rendino', 
    'gigantes', 'banshee',
    
    # Classic Star Trek Ships (for reference/comparison)
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
        """Classify page type and extract metadata with improved ship name detection"""
        title_lower = title.lower()
        
        # Check if it's a ship log (date pattern)
        date_pattern = r'(\d{4}/\d{1,2}/\d{1,2})|(\d{1,2}/\d{1,2}/\d{4})'
        if re.search(date_pattern, title):
            # Enhanced ship name extraction for mission logs
            ship_name = self.extract_ship_name_from_title(title)
            
            # Extract date
            log_date = self.extract_log_date(title)
            
            print(f"   🚢 Classified as mission_log: '{title}' -> ship: '{ship_name}', date: '{log_date}'")
            return "mission_log", ship_name, log_date
        
        # Check if it's a ship info page
        ship_pattern = r'uss\s+(\w+)|(\w+)\s+\(ncc-\d+\)'
        if re.search(ship_pattern, title_lower):
            ship_name = self.extract_ship_name_from_title(title)
            print(f"   🚢 Classified as ship_info: '{title}' -> ship: '{ship_name}'")
            return "ship_info", ship_name, None
        
        # Check if it's a character/personnel page
        if any(keyword in title_lower for keyword in ['captain', 'commander', 'lieutenant', 'ensign', 'admiral']):
            print(f"   👤 Classified as personnel: '{title}'")
            return "personnel", None, None
        
        # Check if it's a location/system page
        if any(keyword in title_lower for keyword in ['system', 'planet', 'station', 'starbase']):
            print(f"   🌍 Classified as location: '{title}'")
            return "location", None, None
        
        # Default to general article
        print(f"   📄 Classified as general: '{title}'")
        return "general", None, None
    
    def extract_ship_name_from_title(self, title: str) -> Optional[str]:
        """Enhanced ship name extraction with multiple patterns"""
        title_lower = title.lower()
        
        # Pattern 1: Direct ship name match in known ships list
        for ship in SHIP_NAMES:
            if ship in title_lower:
                print(f"      ✓ Found ship '{ship}' in title")
                return ship
        
        # Pattern 2: Extract from "USS [ShipName]" format
        uss_pattern = r'uss\s+(\w+)'
        uss_match = re.search(uss_pattern, title_lower)
        if uss_match:
            ship_candidate = uss_match.group(1)
            # Check if it's a known ship
            if ship_candidate in SHIP_NAMES:
                print(f"      ✓ Found USS ship '{ship_candidate}' in title")
                return ship_candidate
        
        # Pattern 3: Extract from ship name at start of title (e.g., "Stardancer 4/23/2022")
        ship_start_pattern = r'^(\w+)\s+\d'
        ship_start_match = re.search(ship_start_pattern, title_lower)
        if ship_start_match:
            ship_candidate = ship_start_match.group(1)
            if ship_candidate in SHIP_NAMES:
                print(f"      ✓ Found ship '{ship_candidate}' at start of title")
                return ship_candidate
        
        # Pattern 4: Extract from "Date Ship Log" format (e.g., "2024/09/29 Adagio Log")
        date_ship_pattern = r'\d+[/-]\d+[/-]\d+\s+(\w+)'
        date_ship_match = re.search(date_ship_pattern, title_lower)
        if date_ship_match:
            ship_candidate = date_ship_match.group(1)
            if ship_candidate in SHIP_NAMES:
                print(f"      ✓ Found ship '{ship_candidate}' after date")
                return ship_candidate
        
        print(f"      ⚠️  No ship name found in title: '{title}'")
        return None
    
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
            content = page_data['raw_content']
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
                                part_content,
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
                                part_content,
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
                "USS Manta", "Marcus Blaine", "Large Magellanic Cloud Expedition",
                "Luna Class Starship",
                "USS Prometheus", "Talia", "The Primacy",
                "Samwise Blake", "Lilith", "Cetas", "Tatpha", "Beryxian",
                "Orzaul Gate", "Tiberius Asada", "Sif",
                "Saiv Daly",
                "Surithrae Alemyn",
                "Jiratha", "Aija Bessley",
                "Maeve Tolena Blaine"
            ]
            logger.warning(f"  ⚠️  Using fallback list: {len(page_titles)} pages")
        
        return page_titles
    
    def get_page_content_from_api(self, page_title: str):
        """Get page content directly from MediaWiki API - Legacy method with improved processing"""
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
                    raw_wikitext = page['revisions'][0]['slots']['main']['*']
                    
                    # Process the raw wikitext to make it more readable
                    processed_content = self._process_wikitext(page_title, raw_wikitext)
                    
                    if processed_content and len(processed_content) > 30:  # Very low threshold
                        url = f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}"
                        
                        page_data = {
                            'title': page_title,
                            'url': url,
                            'content': processed_content,
                            'raw_content': processed_content,
                            'crawled_at': datetime.now()
                        }
                        
                        print(f"  ✓ Successfully extracted {len(processed_content)} characters from legacy API")
                        return page_data
                    else:
                        print(f"  ⚠️  Processed content too short: {len(processed_content) if processed_content else 0} chars")
                        
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error getting content from legacy API: {e}")
            return None
    
    def _process_wikitext(self, title: str, wikitext: str) -> str:
        """Process raw wikitext into readable content"""
        try:
            content_parts = []
            
            # Add title
            content_parts.append(f"**{title}**\n")
            
            # Remove common wikitext elements
            text = wikitext
            
            # Remove template calls (simple version)
            text = re.sub(r'\{\{[^}]+\}\}', '', text)
            
            # Remove file/image references
            text = re.sub(r'\[\[File:[^\]]+\]\]', '', text)
            text = re.sub(r'\[\[Image:[^\]]+\]\]', '', text)
            
            # Remove category links
            text = re.sub(r'\[\[Category:[^\]]+\]\]', '', text)
            
            # Convert internal links to plain text
            text = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', text)  # [[Page|Display]] -> Display
            text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)  # [[Page]] -> Page
            
            # Remove external link formatting
            text = re.sub(r'\[([^ ]+) ([^\]]+)\]', r'\2', text)  # [URL Text] -> Text
            
            # Remove bold/italic markup
            text = re.sub(r"'{3,5}", '', text)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            
            # Remove ref tags and content
            text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
            text = re.sub(r'<ref[^>]*/?>', '', text)
            
            # Split into lines and process
            lines = text.split('\n')
            current_section = ""
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Handle section headers
                if line.startswith('='):
                    level = 0
                    while line.startswith('='):
                        level += 1
                        line = line[1:]
                    while line.endswith('='):
                        line = line[:-1]
                    line = line.strip()
                    
                    if line and level <= 4:  # Only include up to level 4 headers
                        heading = '#' * max(2, level)
                        content_parts.append(f"{heading} {line}\n")
                
                # Handle regular content
                elif len(line) > 10 and not line.startswith(('#', '*', ':', ';')):
                    # Clean up the line further
                    clean_line = line.strip()
                    if clean_line and not clean_line.lower().startswith(('category:', 'file:', 'image:')):
                        content_parts.append(f"{clean_line}\n")
            
            # Join and clean up
            result = '\n'.join(content_parts)
            result = re.sub(r'\n{3,}', '\n\n', result)
            return result.strip()
            
        except Exception as e:
            print(f"  ⚠️  Error processing wikitext: {e}")
            # Return basic processed version - NO TRUNCATION for mission logs
            basic_text = re.sub(r'\{\{[^}]+\}\}', '', wikitext)  # Remove templates
            basic_text = re.sub(r'\[\[[^\]]+\]\]', '', basic_text)  # Remove links
            basic_text = re.sub(r'<[^>]+>', '', basic_text)  # Remove HTML
            # Remove truncation - keep full content for mission logs
            return f"**{title}**\n\n{basic_text}"
    
    def _get_parsed_content(self, page_title: str) -> Optional[Dict]:
        """Get parsed HTML content with section structure"""
        try:
            params = {
                'action': 'parse',
                'format': 'json',
                'page': page_title,
                'prop': 'text|sections|displaytitle',
                'disableeditsection': True,
                'wrapoutputclass': ''
            }
            
            response = requests.get(self.api_url, params=params)
            data = response.json()
            
            if 'parse' in data:
                return {
                    'html': data['parse'].get('text', {}).get('*', ''),
                    'sections': data['parse'].get('sections', []),
                    'title': data['parse'].get('displaytitle', page_title)
                }
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error getting parsed content: {e}")
            return None
    
    def _get_text_extract(self, page_title: str) -> Optional[str]:
        """Get clean text summary"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
                'exsectionformat': 'plain',
                'exchars': 500
            }
            
            response = requests.get(self.api_url, params=params)
            data = response.json()
            
            if 'query' in data and 'pages' in data['query']:
                page = next(iter(data['query']['pages'].values()))
                return page.get('extract', '').strip()
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error getting text extract: {e}")
            return None
    
    def _extract_infobox_from_html(self, html: str) -> Optional[str]:
        """Extract and format infobox data from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Look for portable infobox (Fandom's standard)
            infobox = soup.find('aside', class_='portable-infobox')
            if not infobox:
                # Look for traditional infobox
                infobox = soup.find('table', class_='infobox')
            
            if infobox:
                # Extract text content and format it nicely
                infobox_text = infobox.get_text(separator='\n', strip=True)
                if infobox_text:
                    return f"## Information\n{infobox_text}\n"
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error extracting infobox: {e}")
            return None
    
    def _build_formatted_content(self, title: str, parsed_content: Dict, text_extract: str, raw_wikitext: str = None) -> str:
        """Build comprehensive formatted content similar to fandom-py output"""
        content_parts = []
        
        # Add title
        content_parts.append(f"**{title}**\n")
        
        # Add summary if available
        if text_extract and len(text_extract.strip()) > 20:
            content_parts.append(f"## Summary\n{text_extract}\n")
        
        # Extract and add infobox if present
        if parsed_content and parsed_content.get('html'):
            infobox_content = self._extract_infobox_from_html(parsed_content['html'])
            if infobox_content:
                content_parts.append(infobox_content)
        
        # Process sections from parsed content
        content_added = False
        if parsed_content and parsed_content.get('sections'):
            try:
                html = parsed_content.get('html', '')
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove infoboxes since we already extracted them
                for infobox in soup.find_all(['aside', 'table'], class_=['portable-infobox', 'infobox']):
                    infobox.decompose()
                
                # Remove navigation boxes and other clutter
                for nav in soup.find_all('table', class_='navbox'):
                    nav.decompose()
                for toc in soup.find_all('div', id='toc'):
                    toc.decompose()
                
                # Extract sections based on headings
                sections = parsed_content['sections']
                if sections:
                    # Find content before first section (overview) - NO LIMITS
                    overview_content = []
                    for elem in soup.find_all(['p', 'div']):
                        text = elem.get_text(strip=True)
                        if text and len(text) > 20:
                            overview_content.append(text)
                            # Remove limit - get ALL overview content for mission logs
                    
                    if overview_content:
                        content_parts.append(f"## Overview\n{' '.join(overview_content)}\n")
                        content_added = True
                    
                    # Add sections with proper hierarchy (NO LIMITS for mission logs)
                    for section in sections:  # Get ALL sections, not just first 10
                        section_title = section.get('line', '')
                        section_level = int(section.get('level', 2))
                        
                        if section_title and section_title.lower() not in ['references', 'external links', 'see also']:
                            heading = '#' * max(2, section_level)
                            content_parts.append(f"{heading} {section_title}\n")
                            
                            # Try to extract section content
                            section_anchor = section.get('anchor', '')
                            if section_anchor:
                                section_content = self._extract_section_content(soup, section_anchor)
                                if section_content:
                                    content_parts.append(f"{section_content}\n")
                                    content_added = True
                
            except Exception as e:
                print(f"  ⚠️  Error processing sections: {e}")
        
        # Enhanced fallback content extraction
        current_content = '\n'.join(content_parts)
        if len(current_content) < 200 and parsed_content and parsed_content.get('html'):
            fallback_content = self._extract_fallback_content(parsed_content['html'])
            if fallback_content:
                content_parts.append(fallback_content)
                content_added = True
        
        # Join all content and clean up
        full_content = '\n'.join(content_parts)
        full_content = re.sub(r'\n{3,}', '\n\n', full_content)
        return full_content.strip()
    
    def _extract_section_content(self, soup: BeautifulSoup, section_anchor: str) -> Optional[str]:
        """Extract content for a specific section"""
        try:
            # Find the heading with this anchor
            heading = soup.find(attrs={'id': section_anchor})
            if heading:
                content_parts = []
                current = heading.find_next_sibling()
                
                while current and current.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    if current.name in ['p', 'div'] and current.get_text(strip=True):
                        text = current.get_text(strip=True)
                        if len(text) > 20:
                            content_parts.append(text)
                    current = current.find_next_sibling()
                    # Remove limit - get ALL section content for mission logs
                
                return ' '.join(content_parts) if content_parts else None
            return None
            
        except Exception as e:
            return None
    
    def _extract_fallback_content(self, html: str) -> Optional[str]:
        """Enhanced fallback content extraction for pages with minimal structured content"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements more aggressively
            for elem in soup.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                elem.decompose()
            
            # Remove specific Fandom elements
            for elem in soup.find_all(class_=['navbox', 'toc', 'mw-references-wrap', 'printfooter']):
                elem.decompose()
            
            # Strategy 1: Try to find main content area
            main_content = soup.find('div', class_='mw-parser-output')
            if not main_content:
                main_content = soup.find('div', id='mw-content-text')
            if not main_content:
                main_content = soup
            
            # Strategy 2: Extract meaningful paragraphs (NO LIMITS for mission logs)
            paragraphs = []
            for p in main_content.find_all(['p', 'div']):
                text = p.get_text(strip=True)
                # More lenient criteria for content
                if text and len(text) > 15 and not text.startswith(('Category:', 'File:', 'Template:')):
                    # Skip navigation-like content
                    if not any(nav_word in text.lower() for nav_word in ['navigation', 'menu', 'edit', 'view source']):
                        paragraphs.append(text)
                        # Remove limit for mission logs - get ALL content
            
            # Strategy 3: If still no content, try lists and other elements
            if len(paragraphs) < 2:
                for elem in main_content.find_all(['li', 'dd', 'td']):
                    text = elem.get_text(strip=True)
                    if text and len(text) > 15:
                        paragraphs.append(text)
                        # Remove limit - get ALL content
            
            # Strategy 4: As last resort, get any text content
            if len(paragraphs) < 2:
                clean_text = main_content.get_text(separator=' ', strip=True)
                if clean_text:
                    # For mission logs, take ALL content, not just a few sentences
                    paragraphs = [clean_text]
            
            if paragraphs:
                content = ' '.join(paragraphs)
                # Clean up the content
                content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
                content = re.sub(r'\[edit\]', '', content)  # Remove edit links
                return f"## Content\n{content}\n"
            
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error in fallback extraction: {e}")
            return None
    
    def _get_comprehensive_text_extract(self, page_title: str) -> Optional[str]:
        """Get more comprehensive text extract without intro limitation"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extracts',
                'exintro': False,  # Get full content, not just intro
                'explaintext': True,
                'exsectionformat': 'plain'
                # No exchars limit - get full content for mission logs
            }
            
            response = requests.get(self.api_url, params=params)
            data = response.json()
            
            if 'query' in data and 'pages' in data['query']:
                page = next(iter(data['query']['pages'].values()))
                extract = page.get('extract', '').strip()
                if extract and len(extract) > 50:  # Lower threshold
                    return extract
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error getting comprehensive extract: {e}")
            return None
    
    def get_enhanced_page_content_optimized(self, page_title: str):
        """Optimized enhanced MediaWiki API content extraction with fewer API calls"""
        try:
            print(f"  🚀 Fetching optimized content from MediaWiki API...")
            
            # Step 1: Get combined data in single API call
            combined_data = self._get_combined_page_data(page_title)
            
            if not combined_data or not combined_data.get('page_exists'):
                print(f"  ⚠️  Page '{page_title}' does not exist")
                return None
            
            # Step 2: Try to use extract content first (often sufficient for mission logs)
            extract_content = combined_data.get('extract', '')
            if extract_content and len(extract_content) > 1000:  # Good extract available
                print(f"  ✓ Using high-quality extract: {len(extract_content)} chars")
                formatted_content = self._build_simple_formatted_content(
                    page_title, extract_content
                )
                
                if formatted_content and len(formatted_content) > 50:
                    return {
                        'title': page_title,
                        'url': f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'content': formatted_content,
                        'raw_content': formatted_content,
                        'crawled_at': datetime.now()
                    }
            
            # Step 3: If extract insufficient, get parsed HTML (only if needed)
            parsed_content = self._get_parsed_html_optimized(page_title)
            
            # Step 4: Build comprehensive formatted content
            if parsed_content or extract_content:
                formatted_content = self._build_formatted_content(
                    page_title, parsed_content, extract_content
                )
                
                if formatted_content and len(formatted_content) > 50:
                    print(f"  ✓ Successfully extracted {len(formatted_content)} characters (optimized)")
                    return {
                        'title': page_title,
                        'url': f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'content': formatted_content,
                        'raw_content': formatted_content,
                        'crawled_at': datetime.now()
                    }
            
            # Step 5: Final fallback to raw wikitext processing
            raw_wikitext = combined_data.get('raw_wikitext', '')
            if raw_wikitext:
                print(f"  📝 Processing raw wikitext: {len(raw_wikitext)} chars")
                processed_content = self._process_wikitext(page_title, raw_wikitext)
                
                if processed_content and len(processed_content) > 30:
                    return {
                        'title': page_title,
                        'url': f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'content': processed_content,
                        'raw_content': processed_content,
                        'crawled_at': datetime.now()
                    }
            
            print(f"  ✗ Unable to extract sufficient content")
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error in optimized extraction: {e}")
            return None
    
    def _build_simple_formatted_content(self, title: str, extract_content: str) -> str:
        """Build simple formatted content from extract (faster for mission logs)"""
        try:
            content_parts = []
            
            # Add title
            content_parts.append(f"**{title}**\n")
            
            # Add the extract content with minimal processing
            if extract_content:
                # Clean up the content slightly
                clean_content = re.sub(r'\s+', ' ', extract_content)  # Normalize whitespace
                content_parts.append(f"## Content\n{clean_content}\n")
            
            return '\n'.join(content_parts)
            
        except Exception as e:
            print(f"  ⚠️  Error building simple content: {e}")
            return f"**{title}**\n\n{extract_content}"
    
    def _get_combined_page_data(self, page_title: str) -> Dict:
        """Optimized method to get multiple types of content in fewer API calls"""
        try:
            # Single API call to get parsed content, extract, and page info
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extracts|info|revisions',
                'exintro': False,  # Get full content
                'explaintext': True,
                'exsectionformat': 'plain',
                'rvprop': 'content',
                'rvslots': '*',
                # No character limits for full content
            }
            
            response = requests.get(self.api_url, params=params)
            data = response.json()
            
            if 'query' not in data or 'pages' not in data['query']:
                return {}
            
            page = next(iter(data['query']['pages'].values()))
            
            # Extract all available data from single response
            result = {
                'title': page_title,
                'page_id': page.get('pageid', -1),
                'extract': page.get('extract', '').strip() if 'extract' in page else '',
                'raw_wikitext': '',
                'page_exists': page.get('pageid', -1) != -1
            }
            
            # Get raw wikitext if available
            if 'revisions' in page and page['revisions']:
                result['raw_wikitext'] = page['revisions'][0]['slots']['main']['*']
            
            return result
            
        except Exception as e:
            print(f"  ⚠️  Error in combined API call: {e}")
            return {}
    
    def _get_parsed_html_optimized(self, page_title: str) -> Optional[Dict]:
        """Optimized parsed HTML extraction with retry logic"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                params = {
                    'action': 'parse',
                    'format': 'json',
                    'page': page_title,
                    'prop': 'text|sections|displaytitle',
                    'disableeditsection': True,
                    'wrapoutputclass': ''
                }
                
                response = requests.get(self.api_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'parse' in data:
                    return {
                        'html': data['parse'].get('text', {}).get('*', ''),
                        'sections': data['parse'].get('sections', []),
                        'title': data['parse'].get('displaytitle', page_title)
                    }
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠️  Parse API attempt {attempt + 1} failed, retrying...")
                    time.sleep(1)
                else:
                    print(f"  ⚠️  Parse API failed after {max_retries} attempts: {e}")
        
        return None
    
    def extract_page_content(self, page_title: str):
        """Extract content from a single page - Optimized MediaWiki API"""
        try:
            print(f"Crawling: {page_title}")
            
            # Use optimized MediaWiki API method first
            page_data = self.get_enhanced_page_content_optimized(page_title)
            
            if page_data and page_data.get('raw_content') and len(page_data['raw_content']) > 30:
                print(f"  ✓ Successfully extracted {len(page_data['raw_content'])} characters")
                return page_data
            else:
                # Fallback to original enhanced method if optimized fails
                print(f"  ⚠️  Optimized extraction failed, trying legacy enhanced method...")
                page_data = self.get_enhanced_page_content_from_api(page_title)
                
                if page_data and page_data.get('raw_content') and len(page_data['raw_content']) > 30:
                    print(f"  ✓ Successfully extracted {len(page_data['raw_content'])} characters (fallback)")
                    return page_data
                else:
                    print(f"  ✗ Insufficient content extracted ({len(page_data['raw_content']) if page_data and page_data.get('raw_content') else 0} chars)")
                    return None
                
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
    
    def get_enhanced_page_content_from_api(self, page_title: str):
        """Enhanced MediaWiki API content extraction - Legacy method"""
        try:
            print(f"  📡 Fetching enhanced content from MediaWiki API...")
            
            # Step 1: Get parsed HTML content with sections
            parsed_content = self._get_parsed_content(page_title)
            
            # Step 2: Get plain text extract for summary  
            text_extract = self._get_text_extract(page_title)
            
            # Step 3: If initial extract is insufficient, try comprehensive extract
            if not text_extract or len(text_extract) < 50:
                text_extract = self._get_comprehensive_text_extract(page_title)
                print(f"  📝 Using comprehensive extract: {len(text_extract) if text_extract else 0} chars")
            
            # Step 4: Build formatted content
            if parsed_content or text_extract:
                formatted_content = self._build_formatted_content(
                    page_title, parsed_content, text_extract
                )
                
                # Lower threshold for acceptance (50 instead of 100)
                min_content_length = 50
                if formatted_content and len(formatted_content) > min_content_length:
                    page_data = {
                        'title': page_title,
                        'url': f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'content': formatted_content,      # Same content in both fields
                        'raw_content': formatted_content,  # Same content in both fields  
                        'crawled_at': datetime.now()
                    }
                    
                    print(f"  ✓ Successfully extracted {len(formatted_content)} characters from enhanced API")
                    return page_data
                else:
                    print(f"  ⚠️  Content too short ({len(formatted_content) if formatted_content else 0} chars), trying legacy API...")
            else:
                print(f"  ⚠️  No parsed content or text extract available, trying legacy API...")
            
            # Fallback to legacy method if enhanced extraction fails
            return self.get_page_content_from_api(page_title)
            
        except Exception as e:
            print(f"  ⚠️  Error with enhanced API: {e}, trying legacy API...")
            return self.get_page_content_from_api(page_title)
    
    def crawl_wiki_pages(self, use_comprehensive_list=False, force_update=False, limit=None):
        """Crawl wiki pages and save to database - Optimized version"""
        logger.info("🌐 Starting optimized wiki crawl to elsiebrain database...")
        
        # Get page titles
        if use_comprehensive_list:
            page_titles = self.get_all_page_titles_from_special_pages()
        else:
            # Use updated curated list
            page_titles = [
                "22nd Mobile Daedalus Fleet", "USS Stardancer", "USS Adagio", 
                "USS Pilgrim", "USS Protector", "USS Manta", "Marcus Blaine",
                "Large Magellanic Cloud Expedition", "Luna Class Starship",
                "Main Page", "USS Prometheus", "Talia", "The Primacy",
                "Samwise Blake", "Lilith", "Cetas", "Tatpha", "Beryxian",
                "Orzaul Gate", "Tiberius Asada", "Sif", "Saiv Daly",
                "Surithrae Alemyn", "Jiratha", "Aija Bessley", "Maeve Tolena Blaine"
            ]
        
        # Limit results if specified
        if limit:
            page_titles = page_titles[:limit]
        
        successful_crawls = 0
        updated_pages = 0
        skipped_pages = 0
        start_time = time.time()
        
        for i, page_title in enumerate(page_titles, 1):
            logger.info(f"\n[{i}/{len(page_titles)}] Processing: {page_title}")
            page_start_time = time.time()
            
            # Check if we should update this page
            if not force_update:
                # First, do a quick content check
                page_data = self.extract_page_content(page_title)
                if page_data:
                    content_hash = self.calculate_content_hash(page_data['raw_content'])
                    if not self.should_update_page(page_title, content_hash):
                        logger.info(f"  ⏭️  Skipping - no changes detected")
                        skipped_pages += 1
                        continue
            else:
                page_data = self.extract_page_content(page_title)
            
            if page_data:
                # Calculate content hash
                content_hash = self.calculate_content_hash(page_data['raw_content'])
                
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
                    
                    # Performance metrics
                    page_time = time.time() - page_start_time
                    print(f"  ⏱️  Processed in {page_time:.2f}s")
            
            # Reduced sleep time for better performance
            time.sleep(1)  # Reduced from 2 seconds
        
        total_time = time.time() - start_time
        logger.info(f"\n🌐 Optimized wiki crawling complete in {total_time:.2f} seconds!")
        logger.info(f"✓ Successfully crawled: {successful_crawls} pages")
        logger.info(f"✓ Updated: {updated_pages} pages")
        logger.info(f"⏭️  Skipped (unchanged): {skipped_pages} pages")
        logger.info(f"⚡ Average time per page: {total_time/len(page_titles):.2f}s")
        
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
                content_hash = crawler.calculate_content_hash(page_data['raw_content'])
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
        print("- You have installed required packages: pip install psycopg2-binary requests beautifulsoup4")

if __name__ == "__main__":
    main() 