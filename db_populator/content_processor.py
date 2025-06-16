#!/usr/bin/env python3
"""
Content Processor for 22nd Mobile Daedalus Fleet Wiki Crawler
Handles content formatting, classification, and text processing.
"""

import re
import hashlib
from typing import Tuple, Optional, List, Dict
from datetime import datetime
from bs4 import BeautifulSoup




class ContentProcessor:
    """Handles content processing, classification, and formatting"""
    
    def get_categories_from_page_data(self, page_data: Dict) -> List[str]:
        """Extract categories from page data (no classification)"""
        categories = page_data.get('categories', [])
        
        if not categories:
            print(f"  ⚠️  No categories found for page, using fallback")
            return ['General Information']  # Minimal fallback only
        
        print(f"  ✓ Using real wiki categories: {categories}")
        return categories
    

    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def process_wikitext(self, title: str, wikitext: str) -> str:
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
    
    def extract_infobox_from_html(self, html: str) -> Optional[str]:
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
    
    def extract_section_content(self, soup: BeautifulSoup, section_anchor: str) -> Optional[str]:
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
    
    def extract_fallback_content(self, html: str) -> Optional[str]:
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
    
    def build_formatted_content(self, title: str, parsed_content: dict, text_extract: str) -> str:
        """Build comprehensive formatted content similar to fandom-py output"""
        content_parts = []
        
        # Add title
        content_parts.append(f"**{title}**\n")
        
        # Add summary if available
        if text_extract and len(text_extract.strip()) > 20:
            content_parts.append(f"## Summary\n{text_extract}\n")
        
        # Extract and add infobox if present
        if parsed_content and parsed_content.get('html'):
            infobox_content = self.extract_infobox_from_html(parsed_content['html'])
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
                                section_content = self.extract_section_content(soup, section_anchor)
                                if section_content:
                                    content_parts.append(f"{section_content}\n")
                                    content_added = True
                
            except Exception as e:
                print(f"  ⚠️  Error processing sections: {e}")
        
        # Enhanced fallback content extraction
        current_content = '\n'.join(content_parts)
        if len(current_content) < 200 and parsed_content and parsed_content.get('html'):
            fallback_content = self.extract_fallback_content(parsed_content['html'])
            if fallback_content:
                content_parts.append(fallback_content)
                content_added = True
        
        # Join all content and clean up
        full_content = '\n'.join(content_parts)
        full_content = re.sub(r'\n{3,}', '\n\n', full_content)
        return full_content.strip()
    
    def build_simple_formatted_content(self, title: str, extract_content: str) -> str:
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