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
import logging

# Local import for character mapping, no cross-container dependency
from .db_operations import DatabaseOperations
from .character_maps import SHIP_SPECIFIC_CHARACTER_CORRECTIONS, resolve_character_name_with_context, FALLBACK_CHARACTER_CORRECTIONS, FLEET_SHIP_NAMES

class ContentProcessor:
    """Handles content processing, classification, and formatting"""
    
    def __init__(self, db_ops: DatabaseOperations):
        self.db_ops = db_ops
        self.character_maps = SHIP_SPECIFIC_CHARACTER_CORRECTIONS

    def process_content(self, title: str, page_data: dict) -> str:
        """
        Routes content to the appropriate processor based on its categories.
        """
        categories = self.get_categories_from_page_data(page_data)
        wikitext = page_data.get('raw_wikitext', '')
        is_log = any('log' in cat.lower() for cat in categories)

        if is_log:
            return self.process_log_content(title, wikitext, categories)
        else:
            return self.process_wikitext(title, page_data)
    
    def get_categories_from_page_data(self, page_data: Dict) -> List[str]:
        """Extract categories from page data"""
        categories = page_data.get('categories', [])
        if not categories:
            return ['General Information']
        return categories
    
    def calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content for change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def process_wikitext(self, title: str, page_data: dict) -> str:
        """
        Process raw wikitext by leveraging HTML parsing.
        """
        try:
            parsed_content = page_data.get('parsed', {})
            text_extract = page_data.get('extract', '')
            return self.build_formatted_content(title, parsed_content, text_extract)
        except Exception as e:
            wikitext = page_data.get('raw_wikitext', '')
            basic_text = re.sub(r'<[^>]+>', '', wikitext)
            return f"**{title}**\n\n{basic_text}"

    def _cleanup_line(self, line: str) -> str:
        """Performs final formatting on the line content."""
        line = re.sub(r"'''(.*?)'''", r'\\1', line)
        line = re.sub(r"''(.*?)''", r'\\1', line)
        # Preserve asterisks for actions
        # line = line.replace('*', '') 
        return line

    def _remove_timestamp(self, line: str) -> str:
        """Removes a timestamp from the start of a line."""
        timestamp_pattern = r'^\s*\[\s*\d{1,2}:\d{2}(?::\d{2})?\s*\]\s*'
        return re.sub(timestamp_pattern, '', line)

    def _convert_scene_tags(self, line: str) -> Tuple[str, str]:
        """Converts [DOIC] tags."""
        scene_tag = ""
        scene_map = {'1': 'A', '2': 'B', '3': 'C', '4': 'D', '5': 'E', '6': 'F'}
        doic_pattern = r'\[\s*(DOIC(\d)?)\s*\]'
        match = re.search(doic_pattern, line, re.IGNORECASE)
        
        if match:
            original_tag = match.group(0)
            digit = match.group(2)
            scene_tag = f"-Scene {scene_map.get(digit, '?')}-" if digit else "-Setting-"
            line = line.replace(original_tag, "", 1).lstrip()
            
        return line, scene_tag

    def _assign_speaker(self, line: str, ship_context: str) -> Tuple[str, str]:
        """Assigns a speaker from patterns."""
        bracket_speaker_pattern = r'\[\s*([^\]]+?)\s*\]'
        bracket_match = re.search(bracket_speaker_pattern, line)
        
        if bracket_match and self._is_known_character(bracket_match.group(1), ship_context):
            speaker = bracket_match.group(1)
            line = line.replace(bracket_match.group(0), "", 1).lstrip()
            line = re.sub(r'^\s*[^:]+:\s*', '', line, count=1).lstrip()
            return line, speaker

        at_tag_pattern = r'^\s*([^:]+@\S+)\s*:'
        at_match = re.search(at_tag_pattern, line)
        if at_match:
            speaker = at_match.group(1).strip()
            line = line[at_match.end(0):].lstrip()
            return line, speaker
        
        # Fallback for simple "Name: message"
        colon_pattern = r'^\s*([^:]{2,30}?)\s*:'
        colon_match = re.search(colon_pattern, line)
        if colon_match:
            potential_speaker = colon_match.group(1).strip()
            # Basic heuristic to avoid matching non-names
            if ' ' in potential_speaker or (potential_speaker.isalpha() and potential_speaker[0].isupper()):
                 line = line[colon_match.end(0):].lstrip()
                 return line, potential_speaker

        return line, ""

    def _is_known_character(self, name: str, ship_context: str) -> bool:
        """Checks if a name is a known character."""
        resolved_name = resolve_character_name_with_context(name, ship_context)
        return resolved_name != 'Unknown' and resolved_name is not None

    def _get_ship_context(self, title: str) -> str:
        """Determines the ship context from the page title."""
        title_lower = title.lower()
        for ship_name in FLEET_SHIP_NAMES:
            if ship_name.lower() in title_lower:
                return ship_name.lower().replace('uss ', '')
        return ""

    def process_log_content(self, title: str, wikitext: str, categories: List[str]) -> str:
        """Processes raw wikitext from a log page."""
        if not wikitext:
            return ""
        
        ship_context = self._get_ship_context(title)
        cleaned_lines = []
        lines = wikitext.splitlines()
        line_number = 1
        last_setting_speaker = ""
        last_processed_speaker = ""

        for original_line in lines:
            work_line = original_line.strip()
            if not work_line:
                continue

            line_with_number = f"-Line {line_number}- "
            work_line = self._remove_timestamp(work_line)
            work_line, scene_tag = self._convert_scene_tags(work_line)
            
            is_action_line = work_line.startswith('*')
            
            work_line, speaker = self._assign_speaker(work_line, ship_context)
            
            # --- Speaker Logic for "-Setting-" channels ---
            if scene_tag == "-Setting-":
                # If a GM speaks, inherit the last speaker or become Narrator
                if '@' in speaker:
                    speaker = last_setting_speaker if last_setting_speaker else "Narrator"
                # If no speaker, but there was a previous one, continue their speech
                elif not speaker and last_setting_speaker:
                    speaker = last_setting_speaker
                # If it's an action line with no speaker, it's the Narrator
                elif is_action_line and not speaker:
                    speaker = "Narrator"

                # Update memory for the next line
                if speaker:
                    last_setting_speaker = speaker
                
                # Reset speaker if the line indicates the end of a thought/log
                words = work_line.rstrip().split()
                if words and "end" in [word.lower() for word in words[-4:]]:
                    last_setting_speaker = ""
            else:
                last_setting_speaker = ""

            # --- Final Speaker Resolution ---
            raw_speaker_name = speaker.split('@')[0].strip()
            if "DGM" in raw_speaker_name:
                if is_action_line:
                    final_speaker = "Narrator"
                else:
                    final_speaker = last_processed_speaker # Inherit previous speaker
            elif raw_speaker_name:
                # Use the existing resolver to get the canonical name
                final_speaker = resolve_character_name_with_context(raw_speaker_name, ship_context)
            else:
                final_speaker = "" # No speaker

            work_line = self._cleanup_line(work_line)

            final_line = line_with_number
            if scene_tag:
                final_line += f"{scene_tag} "
            
            if final_speaker:
                final_line += f"{final_speaker}: "
            
            final_line += work_line
            cleaned_lines.append(final_line)
            line_number += 1
            
            # Update last_processed_speaker for the next iteration
            if final_speaker:
                last_processed_speaker = final_speaker

        return f"**{title}**\n\n" + "\n".join(cleaned_lines)

    def build_formatted_content(self, title: str, parsed_content: dict, text_extract: str) -> str:
        """Builds a formatted string from structured page content."""
        content_parts = [f"**{title}**\n"]
        if text_extract and len(text_extract.strip()) > 20:
            content_parts.append(f"## Summary\n{text_extract}\n")
        
        full_content = '\n'.join(content_parts)
        full_content = re.sub(r'\n{3,}', '\n\n', full_content)
        return full_content.strip()

    def build_simple_formatted_content(self, title: str, extract_content: str) -> str:
        """Builds simple formatted content from extract."""
        content_parts = [f"**{title}**\n"]
        if extract_content:
            clean_content = re.sub(r'\s+', ' ', extract_content)
            content_parts.append(f"## Content\n{clean_content}\n")
        
        return '\n'.join(content_parts).strip()

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