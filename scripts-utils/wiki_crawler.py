#!/usr/bin/env python3
"""
22nd Mobile Daedalus Fleet Wiki Crawler
Extracts all content from the wiki using fandom-py library and saves to a flat text file for local searching.
"""

import fandom
import time
import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sys

class WikiCrawler:
    def __init__(self):
        # Set the wiki to 22ndmobile
        fandom.set_wiki("22ndmobile")
        self.wiki_content = {}
    
    def get_all_page_titles_from_special_pages(self):
        """Get all page titles from the Special:AllPages endpoint"""
        print("Fetching all page titles from Special:AllPages...")
        
        all_page_titles = []
        base_url = "https://22ndmobile.fandom.com/wiki/Special:AllPages"
        
        try:
            # Start with the first page
            current_url = base_url
            pages_processed = 0
            
            while current_url:
                print(f"Fetching page: {current_url}")
                
                # Make request to the Special:AllPages URL
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(current_url, headers=headers)
                response.raise_for_status()
                
                # Parse the HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find all page links in the content area
                # The page titles are in <a> tags within the content area
                content_area = soup.find('div', {'class': 'mw-content-ltr'}) or soup.find('div', {'id': 'mw-content-text'})
                
                if content_area:
                    # Find all links that are page titles (not edit/talk links)
                    page_links = content_area.find_all('a')
                    
                    page_count_this_batch = 0
                    for link in page_links:
                        href = link.get('href', '')
                        title = link.get_text().strip()
                        
                        # Filter out non-page links (edit, talk, etc.)
                        if (href.startswith('/wiki/') and 
                            not href.startswith('/wiki/Special:') and
                            not href.startswith('/wiki/Talk:') and
                            not href.startswith('/wiki/File:') and
                            not href.startswith('/wiki/Category:') and
                            not ':' in href.replace('/wiki/', '').split('/')[-1] and
                            title and 
                            len(title) > 2 and
                            title not in all_page_titles):
                            
                            all_page_titles.append(title)
                            page_count_this_batch += 1
                    
                    print(f"  Found {page_count_this_batch} page titles on this page")
                    pages_processed += 1
                
                # Look for "Next page" link to continue pagination
                next_link = None
                next_links = soup.find_all('a', string=lambda text: text and 'Next page' in text)
                
                if next_links:
                    for link in next_links:
                        href = link.get('href')
                        if href:
                            next_link = f"https://22ndmobile.fandom.com{href}"
                            break
                
                # Also check for pagination links
                if not next_link:
                    pagination_links = soup.find_all('a', {'class': 'mw-nextlink'})
                    if pagination_links:
                        href = pagination_links[0].get('href')
                        if href:
                            next_link = f"https://22ndmobile.fandom.com{href}"
                
                current_url = next_link
                
                # Safety break to avoid infinite loops
                if pages_processed > 50:  # Reasonable limit for pagination
                    print("Reached pagination limit, stopping.")
                    break
                    
                # Be respectful to the server
                time.sleep(1)
                
        except Exception as e:
            print(f"Error fetching page titles: {e}")
            return []
        
        # Remove duplicates and sort
        unique_titles = list(dict.fromkeys(all_page_titles))
        unique_titles.sort()
        
        print(f"✓ Found {len(unique_titles)} unique page titles")
        return unique_titles
    
    def save_page_titles_to_file(self, page_titles, filename="all_wiki_page_titles.txt"):
        """Save all page titles to a text file"""
        print(f"Saving {len(page_titles)} page titles to {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"22ND MOBILE DAEDALUS FLEET WIKI - ALL PAGE TITLES\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Pages: {len(page_titles)}\n")
            f.write(f"Source: https://22ndmobile.fandom.com/wiki/Special:AllPages\n")
            f.write("=" * 60 + "\n\n")
            
            for i, title in enumerate(page_titles, 1):
                f.write(f"{i:4d}. {title}\n")
        
        print(f"✓ Page titles saved to {filename}")
        return filename
        
    def get_all_pages(self, use_comprehensive_list=False):
        """Get a list of all wiki pages using fandom API or comprehensive Special:AllPages list"""
        
        if use_comprehensive_list:
            print("Using comprehensive page list from Special:AllPages...")
            return self.get_all_page_titles_from_special_pages()
        
        try:
            print("Fetching pages from 22ndmobile wiki using search terms...")
            
            # Try to search for common terms to get page lists
            search_terms = ["USS", "Stardancer", "Primacy", "Fleet", "Captain", "Mission", "Log", "Adagio", "Pilgrim", "Protector", "Manta", "Blaine", "Rendino", "Magellanic Cloud Expedition", "Samwise Blake","Bren Riens",
                            "Niaev","Maeve","Talia","Artesia","Dawnbreaker","Riens","Mjolnir"]
            all_pages = []
            
            for term in search_terms:
                try:
                    print(f"Searching for: {term}")
                    results = fandom.search(term, results=10)
                    print(f"Found {len(results)} results for '{term}'")
                    
                    # Extract page titles from search results (tuples of title, pageid)
                    for result in results:
                        if isinstance(result, tuple) and len(result) >= 2:
                            page_title = result[0]  # First element is the page title
                            if page_title not in all_pages:
                                all_pages.append(page_title)
                                print(f"  - {page_title}")
                        elif isinstance(result, str):
                            if result not in all_pages:
                                all_pages.append(result)
                                print(f"  - {result}")
                    
                    time.sleep(1)  # Be respectful to the API
                except Exception as e:
                    print(f"Error searching for {term}: {e}")
                    continue
            
            # Also add some specific important pages
            important_pages = [
                "USS Stardancer",
                "22nd Mobile Daedalus Wiki",
                "The Primacy",
                "Samwise Blake",
                "USS Adagio",
                "USS Pilgrim", 
                "USS Protector",
                "USS Manta",
                "Captain Marcus Blaine",
                "Large Magellanic Cloud Expedition",
                "Rendino-class Starship"
            ]
            
            # Add important pages if not already found
            for page in important_pages:
                if page not in all_pages:
                    all_pages.append(page)
            
            # Remove duplicates while preserving order
            pages = list(dict.fromkeys(all_pages))
            
            print(f"Total unique pages to process: {len(pages)}")
            return pages
            
        except Exception as e:
            print(f"Error getting page list: {e}")
            # Fallback to important pages only
            return [
                "USS Stardancer",
                "22nd Mobile Daedalus Wiki", 
                "The Primacy",
                "Samwise Blake",
                "USS Adagio",
                "USS Pilgrim",
                "USS Protector", 
                "USS Manta",
                "Captain Marcus Blaine",
                "Large Magellanic Cloud Expedition",
                "Rendino-class Starship"
            ]
    
    def extract_page_content(self, page_title):
        """Extract content from a single wiki page using fandom-py"""
        try:
            print(f"Crawling: {page_title}")
            
            # Get the page content using the proper API
            try:
                page = fandom.page(title=page_title)
            except Exception as e:
                print(f"Could not fetch page '{page_title}': {e}")
                return None
            
            # Extract content parts
            content_parts = []
            
            # Add title
            if hasattr(page, 'title'):
                content_parts.append(f"**{page.title}**\n")
            else:
                content_parts.append(f"**{page_title}**\n")
            
            # Add summary if available
            if hasattr(page, 'summary') and page.summary:
                content_parts.append(f"## Summary\n{page.summary}\n")
            
            # Get structured content
            if hasattr(page, 'content') and page.content:
                page_content = page.content
                
                if isinstance(page_content, dict):
                    # Handle structured content as documented
                    if 'content' in page_content and page_content['content']:
                        content_parts.append(f"## Overview\n{page_content['content']}\n")
                    
                    if 'infobox' in page_content and page_content['infobox']:
                        content_parts.append(f"## Information\n{page_content['infobox']}\n")
                    
                    if 'sections' in page_content and page_content['sections']:
                        for section in page_content['sections']:
                            if isinstance(section, dict) and 'title' in section:
                                content_parts.append(f"## {section['title']}")
                                if 'content' in section and section['content']:
                                    content_parts.append(f"{section['content']}\n")
                                
                                # Handle subsections
                                if 'sections' in section and section['sections']:
                                    for subsection in section['sections']:
                                        if isinstance(subsection, dict) and 'title' in subsection:
                                            content_parts.append(f"### {subsection['title']}")
                                            if 'content' in subsection and subsection['content']:
                                                content_parts.append(f"{subsection['content']}\n")
                elif isinstance(page_content, str):
                    # Handle plain text content
                    content_parts.append(f"## Content\n{page_content}\n")
            
            # Add sections if available separately
            if hasattr(page, 'sections') and page.sections:
                for section_title in page.sections[:10]:  # Limit to first 10 sections
                    try:
                        section_content = page.section(section_title)
                        if section_content and len(section_content.strip()) > 10:
                            content_parts.append(f"## {section_title}\n{section_content}\n")
                    except Exception as e:
                        print(f"  Error getting section '{section_title}': {e}")
                        continue
            
            # Join all content
            full_content = '\n'.join(content_parts)
            
            # Clean up excessive whitespace
            full_content = full_content.replace('\n\n\n', '\n\n')
            full_content = full_content.strip()
            
            if full_content and len(full_content) > 100:
                page_data = {
                    'title': page.title if hasattr(page, 'title') else page_title,
                    'url': page.url if hasattr(page, 'url') else f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                    'content': full_content,
                    'crawled_at': datetime.now().isoformat()
                }
                
                print(f"  ✓ Successfully extracted {len(full_content)} characters")
                return page_data
            else:
                print(f"  ✗ Insufficient content extracted")
                
        except Exception as e:
            print(f"Error crawling {page_title}: {e}")
            
        return None
    
    def crawl_all_pages(self, use_comprehensive_list=False):
        """Crawl all pages and save content"""
        print("Starting wiki crawl using fandom-py...")
        pages = self.get_all_pages(use_comprehensive_list)
        
        successful_crawls = 0
        
        for i, page_title in enumerate(pages, 1):
            print(f"\n[{i}/{len(pages)}] Processing: {page_title}")
            
            page_data = self.extract_page_content(page_title)
            if page_data:
                self.wiki_content[page_title] = page_data
                successful_crawls += 1
                
            # Be respectful to the API
            time.sleep(2)
            
        print(f"\nCrawling complete! Successfully crawled {successful_crawls} pages")
        return self.wiki_content
    
    def save_to_flat_file(self, filename="fleet_wiki_content.txt"):
        """Save all wiki content to a flat text file"""
        print(f"Saving content to {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("22ND MOBILE DAEDALUS FLEET WIKI - COMPLETE CONTENT DUMP\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Pages: {len(self.wiki_content)}\n")
            f.write("Source: 22ndmobile.fandom.com (via fandom-py)\n")
            f.write("=" * 80 + "\n\n")
            
            for page_name, page_data in self.wiki_content.items():
                f.write(f"\n{'='*80}\n")
                f.write(f"PAGE: {page_data['title']}\n")
                f.write(f"URL: {page_data['url']}\n")
                f.write(f"CRAWLED: {page_data['crawled_at']}\n")
                f.write(f"{'='*80}\n\n")
                f.write(page_data['content'])
                f.write(f"\n\n{'='*80}\n")
                f.write(f"END OF PAGE: {page_data['title']}\n")
                f.write(f"{'='*80}\n\n")
        
        print(f"Content saved to {filename}")
        print(f"File size: {os.path.getsize(filename) / 1024:.2f} KB")
    
    def save_to_json(self, filename="fleet_wiki_backup.json"):
        """Save all wiki content to JSON for backup"""
        print(f"Saving backup to {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.wiki_content, f, indent=2, ensure_ascii=False)
            
        print(f"Backup saved to {filename}")

def get_all_page_titles():
    """Standalone function to retrieve all page titles from Special:AllPages"""
    print("22nd Mobile Daedalus Fleet Wiki - Page Title Retriever")
    print("=" * 60)
    
    try:
        crawler = WikiCrawler()
        
        # Get all page titles from Special:AllPages
        page_titles = crawler.get_all_page_titles_from_special_pages()
        
        if page_titles:
            # Save to file
            filename = crawler.save_page_titles_to_file(page_titles)
            
            print("\n" + "=" * 60)
            print("Page title retrieval completed successfully!")
            print(f"Total page titles found: {len(page_titles)}")
            print(f"File created: {filename}")
            
            # Print first 10 and last 10 titles as a sample
            print(f"\nFirst 10 page titles:")
            for i, title in enumerate(page_titles[:10], 1):
                print(f"  {i:2d}. {title}")
            
            if len(page_titles) > 20:
                print(f"\n  ... ({len(page_titles) - 20} more pages) ...\n")
                print(f"Last 10 page titles:")
                for i, title in enumerate(page_titles[-10:], len(page_titles) - 9):
                    print(f"  {i:2d}. {title}")
                    
            return page_titles
        else:
            print("No page titles were retrieved. Please check your internet connection and try again.")
            return []
            
    except Exception as e:
        print(f"Error during page title retrieval: {e}")
        print("Make sure you have installed required packages: pip install requests beautifulsoup4")
        return []

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--page-titles":
        # Run page title retrieval only
        get_all_page_titles()
        return
    
    # Check for comprehensive crawl option
    use_comprehensive = len(sys.argv) > 1 and sys.argv[1] == "--comprehensive"
    
    print("22nd Mobile Daedalus Fleet Wiki Crawler (fandom-py)")
    print("=" * 60)
    print("Usage:")
    print("  python wiki_crawler.py                    # Standard wiki crawl (~140 pages)")
    print("  python wiki_crawler.py --comprehensive    # Comprehensive crawl (all 1400+ pages)")
    print("  python wiki_crawler.py --page-titles      # Just get all page titles")
    print("=" * 60)
    
    if use_comprehensive:
        print("⚠️  WARNING: Comprehensive crawl will attempt to crawl ALL 1400+ pages!")
        print("⚠️  This will take a very long time and create a very large file.")
        print("⚠️  Press Ctrl+C to cancel, or wait 10 seconds to continue...")
        time.sleep(10)
    
    try:
        crawler = WikiCrawler()
        
        # Crawl all pages (comprehensive or standard)
        wiki_content = crawler.crawl_all_pages(use_comprehensive)
        
        if wiki_content:
            # Save to flat text file for Elsie to search
            crawler.save_to_flat_file("ai_agent/fleet_wiki_content.txt")
            
            # Save JSON backup
            crawler.save_to_json("fleet_wiki_backup.json")
            
            print("\n" + "=" * 60)
            print("Wiki crawling completed successfully!")
            print(f"Total pages crawled: {len(wiki_content)}")
            print("Files created:")
            print("- ai_agent/fleet_wiki_content.txt (for Elsie to search)")
            print("- fleet_wiki_backup.json (backup)")
        else:
            print("No content was crawled. Please check your internet connection and try again.")
            
    except Exception as e:
        print(f"Error during crawling: {e}")
        print("Make sure you have installed fandom-py: pip install fandom-py")

if __name__ == "__main__":
    main() 