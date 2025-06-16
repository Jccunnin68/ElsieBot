#!/usr/bin/env python3
"""
Content Extractor for 22nd Mobile Daedalus Fleet Wiki Crawler
High-level content extraction strategies and orchestration.
"""

from datetime import datetime
from typing import Optional, Dict
from api_client import MediaWikiAPIClient
from content_processor import ContentProcessor


class ContentExtractor:
    """High-level content extraction with multiple strategies"""
    
    def __init__(self):
        self.api_client = MediaWikiAPIClient()
        self.content_processor = ContentProcessor()
    
    def get_enhanced_page_content_optimized(self, page_title: str) -> Optional[Dict]:
        """Optimized enhanced MediaWiki API content extraction with fewer API calls"""
        try:
            print(f"  🚀 Fetching optimized content from MediaWiki API...")
            
            # Step 1: Get combined data in single API call
            combined_data = self.api_client.get_combined_page_data(page_title)
            
            if not combined_data or not combined_data.get('page_exists'):
                print(f"  ⚠️  Page '{page_title}' does not exist")
                return None
            
            # Step 2: Try to use extract content first (often sufficient for mission logs)
            extract_content = combined_data.get('extract', '')
            if extract_content and len(extract_content) > 1000:  # Good extract available
                print(f"  ✓ Using high-quality extract: {len(extract_content)} chars")
                formatted_content = self.content_processor.build_simple_formatted_content(
                    page_title, extract_content
                )
                
                if formatted_content and len(formatted_content) > 50:
                    return {
                        'title': page_title,
                        'url': combined_data.get('canonical_url') or f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'canonical_url': combined_data.get('canonical_url', ''),
                        'touched': combined_data.get('touched', ''),
                        'lastrevid': combined_data.get('lastrevid', 0),
                        'raw_content': formatted_content,
                        'categories': combined_data.get('categories', []),  # ADD categories
                        'crawled_at': datetime.now()
                    }
            
            # Step 3: If extract insufficient, get parsed HTML (only if needed)
            parsed_content = self.api_client.get_parsed_html_optimized(page_title)
            
            # Step 4: Build comprehensive formatted content
            if parsed_content or extract_content:
                formatted_content = self.content_processor.build_formatted_content(
                    page_title, parsed_content, extract_content
                )
                
                if formatted_content and len(formatted_content) > 50:
                    print(f"  ✓ Successfully extracted {len(formatted_content)} characters (optimized)")
                    return {
                        'title': page_title,
                        'url': combined_data.get('canonical_url') or f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'canonical_url': combined_data.get('canonical_url', ''),
                        'touched': combined_data.get('touched', ''),
                        'lastrevid': combined_data.get('lastrevid', 0),
                        'raw_content': formatted_content,
                        'categories': combined_data.get('categories', []),  # ADD categories
                        'crawled_at': datetime.now()
                    }
            
            # Step 5: Final fallback to raw wikitext processing
            raw_wikitext = combined_data.get('raw_wikitext', '')
            if raw_wikitext:
                print(f"  📝 Processing raw wikitext: {len(raw_wikitext)} chars")
                processed_content = self.content_processor.process_wikitext(page_title, raw_wikitext)
                
                if processed_content and len(processed_content) > 30:
                    return {
                        'title': page_title,
                        'url': combined_data.get('canonical_url') or f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'canonical_url': combined_data.get('canonical_url', ''),
                        'touched': combined_data.get('touched', ''),
                        'lastrevid': combined_data.get('lastrevid', 0),
                        'raw_content': processed_content,
                        'categories': combined_data.get('categories', []),  # ADD categories
                        'crawled_at': datetime.now()
                    }
            
            print(f"  ✗ Unable to extract sufficient content")
            return None
            
        except Exception as e:
            print(f"  ⚠️  Error in optimized extraction: {e}")
            return None
    
    def get_enhanced_page_content_from_api(self, page_title: str) -> Optional[Dict]:
        """Enhanced MediaWiki API content extraction - Legacy method"""
        try:
            print(f"  📡 Fetching enhanced content from MediaWiki API...")
            
            # Step 1: Get parsed HTML content with sections
            parsed_content = self.api_client.get_parsed_content(page_title)
            
            # Step 2: Get plain text extract for summary  
            text_extract = self.api_client.get_text_extract(page_title)
            
            # Step 3: If initial extract is insufficient, try comprehensive extract
            if not text_extract or len(text_extract) < 50:
                text_extract = self.api_client.get_comprehensive_text_extract(page_title)
                print(f"  📝 Using comprehensive extract: {len(text_extract) if text_extract else 0} chars")
            
            # Step 4: Build formatted content
            if parsed_content or text_extract:
                formatted_content = self.content_processor.build_formatted_content(
                    page_title, parsed_content, text_extract
                )
                
                # Lower threshold for acceptance (50 instead of 100)
                min_content_length = 50
                if formatted_content and len(formatted_content) > min_content_length:
                    page_data = {
                        'title': page_title,
                        'url': f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                        'canonical_url': '',  # Not available in legacy method
                        'touched': '',  # Not available in legacy method
                        'lastrevid': 0,  # Not available in legacy method
                        'raw_content': formatted_content,
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
    
    def get_page_content_from_api(self, page_title: str) -> Optional[Dict]:
        """Get page content directly from MediaWiki API - Legacy method with improved processing"""
        try:
            legacy_data = self.api_client.get_page_content_legacy(page_title)
            
            if legacy_data and legacy_data.get('raw_wikitext'):
                # Process the raw wikitext to make it more readable
                processed_content = self.content_processor.process_wikitext(
                    page_title, legacy_data['raw_wikitext']
                )
                
                if processed_content and len(processed_content) > 30:  # Very low threshold
                    url = f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}"
                    
                    page_data = {
                        'title': page_title,
                        'url': url,
                        'canonical_url': '',  # Not available in legacy method
                        'touched': '',  # Not available in legacy method  
                        'lastrevid': 0,  # Not available in legacy method
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
    
    def extract_page_content(self, page_title: str) -> Optional[Dict]:
        """Extract content from a single page - Optimized MediaWiki API with multiple fallbacks"""
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
            print(f"Error extracting content for {page_title}: {e}")
            return None
    
    def get_all_page_titles_from_special_pages(self):
        """Get all page titles from the MediaWiki API"""
        print("  📋 Fetching all page titles from MediaWiki API...")
        
        page_titles = self.api_client.get_all_page_titles()
        
        if page_titles:
            print(f"  ✓ Found {len(page_titles)} pages from API")
            return page_titles
        else:
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
            print(f"  ⚠️  Using fallback list: {len(page_titles)} pages")
            return page_titles 