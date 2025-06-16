#!/usr/bin/env python3
"""
MediaWiki API Client for 22nd Mobile Daedalus Fleet Wiki
Handles all low-level API communication with the MediaWiki API.
"""

import time
import requests
from typing import Dict, Optional
from bs4 import BeautifulSoup


class MediaWikiAPIClient:
    """Low-level MediaWiki API client"""
    
    def __init__(self, api_url: str = "https://22ndmobile.fandom.com/api.php"):
        self.api_url = api_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def get_combined_page_data(self, page_title: str) -> Dict:
        """Optimized method to get multiple types of content in fewer API calls"""
        try:
            # Single API call to get parsed content, extract, and page info
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'extracts|info|revisions',
                'inprop': 'url|touched',  # Get URL and touched timestamp
                'exintro': False,  # Get full content
                'explaintext': True,
                'exsectionformat': 'plain',
                'rvprop': 'content',
                'rvslots': '*',
                # No character limits for full content
            }
            
            response = requests.get(self.api_url, params=params, headers=self.headers)
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
                'page_exists': page.get('pageid', -1) != -1,
                'canonical_url': page.get('canonicalurl', ''),  # MediaWiki canonical URL
                'touched': page.get('touched', ''),  # MediaWiki last modification timestamp
                'lastrevid': page.get('lastrevid', 0)  # Last revision ID for change detection
            }
            
            # Get raw wikitext if available
            if 'revisions' in page and page['revisions']:
                result['raw_wikitext'] = page['revisions'][0]['slots']['main']['*']
            
            return result
            
        except Exception as e:
            print(f"  ⚠️  Error in combined API call: {e}")
            return {}
    
    def get_page_metadata(self, page_title: str) -> Dict:
        """Get page metadata including touched timestamp and URLs for update detection"""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': page_title,
                'prop': 'info',
                'inprop': 'url|touched'  # Get URL info and touched timestamp
            }
            
            response = requests.get(self.api_url, params=params, headers=self.headers)
            data = response.json()
            
            if 'query' not in data or 'pages' not in data['query']:
                return {}
            
            page = next(iter(data['query']['pages'].values()))
            
            if page.get('pageid', -1) == -1:  # Page doesn't exist
                return {}
            
            return {
                'title': page.get('title', page_title),
                'pageid': page.get('pageid', -1),
                'canonical_url': page.get('canonicalurl', ''),
                'full_url': page.get('fullurl', ''),
                'edit_url': page.get('editurl', ''),
                'touched': page.get('touched', ''),
                'lastrevid': page.get('lastrevid', 0),
                'length': page.get('length', 0),
                'contentmodel': page.get('contentmodel', 'wikitext')
            }
            
        except Exception as e:
            print(f"  ⚠️  Error getting page metadata: {e}")
            return {}
    
    def get_parsed_html_optimized(self, page_title: str) -> Optional[Dict]:
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
                
                response = requests.get(self.api_url, params=params, headers=self.headers, timeout=10)
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
    
    def get_parsed_content(self, page_title: str) -> Optional[Dict]:
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
            
            response = requests.get(self.api_url, params=params, headers=self.headers)
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
    
    def get_text_extract(self, page_title: str) -> Optional[str]:
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
            
            response = requests.get(self.api_url, params=params, headers=self.headers)
            data = response.json()
            
            if 'query' in data and 'pages' in data['query']:
                page = next(iter(data['query']['pages'].values()))
                return page.get('extract', '').strip()
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error getting text extract: {e}")
            return None
    
    def get_comprehensive_text_extract(self, page_title: str) -> Optional[str]:
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
            
            response = requests.get(self.api_url, params=params, headers=self.headers)
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
    
    def get_page_content_legacy(self, page_title: str) -> Optional[Dict]:
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
            
            response = requests.get(self.api_url, params=params, headers=self.headers)
            data = response.json()
            
            if 'query' in data and 'pages' in data['query']:
                # Get the first (and only) page
                page = next(iter(data['query']['pages'].values()))
                
                if 'revisions' in page:
                    raw_wikitext = page['revisions'][0]['slots']['main']['*']
                    return {
                        'raw_wikitext': raw_wikitext,
                        'page_title': page_title
                    }
                        
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error getting content from legacy API: {e}")
            return None
    
    def get_all_page_titles(self):
        """Get all page titles from the MediaWiki API"""
        try:
            # Use the MediaWiki API to get all pages
            params = {
                'action': 'query',
                'list': 'allpages',
                'aplimit': '500',  # Get up to 500 pages
                'format': 'json'
            }
            
            page_titles = []
            continue_token = None
            
            while True:
                if continue_token:
                    params['apcontinue'] = continue_token
                
                response = requests.get(self.api_url, params=params, headers=self.headers)
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
            
            return sorted(page_titles) if page_titles else []
                
        except Exception as e:
            print(f"  ✗ Error getting page titles: {e}")
            return [] 