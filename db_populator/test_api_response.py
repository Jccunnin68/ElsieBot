#!/usr/bin/env python3
"""
Test script to fetch raw JSON response from MediaWiki API for analysis
"""

import json
import requests
from api_client import MediaWikiAPIClient

def fetch_raw_api_response(page_title="Political_Timeline"):
    """Fetch and save raw JSON response from MediaWiki API"""
    
    print(f"🔍 Fetching raw API response for: {page_title}")
    
    # Initialize API client
    api_client = MediaWikiAPIClient()
    
    # Get various API responses to understand the data structure
    responses = {}
    
    try:
        # 1. Basic page info
        print("  📡 Fetching basic page info...")
        basic_params = {
            'action': 'query',
            'format': 'json',
            'titles': page_title,
            'prop': 'info|categories|templates|links|extlinks',
            'inprop': 'url',
            'cllimit': 'max',
            'tllimit': 'max',
            'pllimit': 'max',
            'ellimit': 'max'
        }
        basic_response = requests.get(api_client.api_url, params=basic_params, headers=api_client.headers, timeout=30)
        if basic_response.status_code == 200:
            responses['basic_info'] = basic_response.json()
        
        # 2. Page content and parse info
        print("  📡 Fetching parsed content...")
        parse_params = {
            'action': 'parse',
            'format': 'json',
            'page': page_title,
            'prop': 'text|sections|categories|templates|links|externallinks|displaytitle'
        }
        parse_response = requests.get(api_client.api_url, params=parse_params, headers=api_client.headers, timeout=30)
        if parse_response.status_code == 200:
            responses['parsed_content'] = parse_response.json()
        
        # 3. Raw wikitext
        print("  📡 Fetching raw wikitext...")
        raw_params = {
            'action': 'query',
            'format': 'json',
            'titles': page_title,
            'prop': 'revisions',
            'rvprop': 'content|contentmodel',
            'rvslots': 'main'
        }
        raw_response = requests.get(api_client.api_url, params=raw_params, headers=api_client.headers, timeout=30)
        if raw_response.status_code == 200:
            responses['raw_wikitext'] = raw_response.json()
        
        # 4. Combined data (like what we use in extraction)
        print("  📡 Fetching combined page data...")
        combined_data = api_client.get_combined_page_data(page_title)
        if combined_data:
            responses['combined_data'] = combined_data
        
        # Save all responses to file
        output_file = f"political_timeline_api_responses.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(responses, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Raw API responses saved to: {output_file}")
        
        # Print summary of what we found
        print("\n📊 API Response Summary:")
        for response_type, data in responses.items():
            print(f"  {response_type}: {len(json.dumps(data)) if data else 0} characters")
            
            if response_type == 'basic_info' and data:
                pages = data.get('query', {}).get('pages', {})
                for page_id, page_data in pages.items():
                    categories = page_data.get('categories', [])
                    templates = page_data.get('templates', [])
                    print(f"    Categories: {len(categories)}")
                    print(f"    Templates: {len(templates)}")
                    if categories:
                        print(f"    Sample categories: {[cat.get('title', '') for cat in categories[:5]]}")
                    if templates:
                        print(f"    Sample templates: {[tpl.get('title', '') for tpl in templates[:5]]}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error fetching API response: {e}")
        return None

if __name__ == "__main__":
    output_file = fetch_raw_api_response()
    if output_file:
        print(f"\n🎯 Examine the file '{output_file}' to understand available identifiers for classification") 