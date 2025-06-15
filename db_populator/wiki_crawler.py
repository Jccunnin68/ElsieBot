#!/usr/bin/env python3
"""
22nd Mobile Daedalus Fleet Wiki Crawler - Container Version
Extracts content from the wiki and stores directly in the elsiebrain PostgreSQL database.
Designed to run within the db_populator Docker container.

Main orchestrator that coordinates the modular components:
- api_client: Low-level MediaWiki API operations
- content_processor: Content formatting and classification
- content_extractor: High-level extraction strategies  
- db_operations: Database connections and persistence
"""
import time
import sys
import logging
from datetime import datetime

# Import our modular components
from api_client import MediaWikiAPIClient
from content_processor import ContentProcessor
from content_extractor import ContentExtractor
from db_operations import DatabaseOperations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WikiCrawlerContainer:
    """Main orchestrator for the modular wiki crawler"""
    
    def __init__(self):
        # Initialize all modular components
        self.db_ops = DatabaseOperations()
        self.content_extractor = ContentExtractor()
        self.content_processor = ContentProcessor()
        
        # Ensure database connection
        self.db_ops.ensure_database_connection()
    
    def extract_page_content(self, page_title: str):
        """Extract content from a single page with error handling and metadata updates"""
        try:
            # Use the content extractor to get page data
            page_data = self.content_extractor.extract_page_content(page_title)
            
            if page_data and page_data.get('raw_content') and len(page_data['raw_content']) > 30:
                return page_data
            else:
                print(f"  ✗ Insufficient content extracted")
                return None
                
        except Exception as e:
            print(f"Error crawling {page_title}: {e}")
            # Update metadata with error
            self.db_ops.upsert_page_metadata(
                page_title, 
                f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}", 
                "", 
                status='error', 
                error_message=str(e)
            )
            return None
    
    def crawl_wiki_pages(self, use_comprehensive_list=False, force_update=False, limit=None):
        """Crawl wiki pages and save to database - Modular version"""
        logger.info("🌐 Starting modular wiki crawl to elsiebrain database...")
        
        # Get page titles
        if use_comprehensive_list:
            page_titles = self.content_extractor.get_all_page_titles_from_special_pages()
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
        
        for i, page_title in enumerate(page_titles, 1):
            logger.info(f"\n[{i}/{len(page_titles)}] Processing: {page_title}")
            
            # Check if we should update this page
            if not force_update:
                # First, do a quick content check
                page_data = self.extract_page_content(page_title)
                if page_data:
                    content_hash = self.content_processor.calculate_content_hash(page_data['raw_content'])
                    if not self.db_ops.should_update_page(page_title, content_hash):
                        logger.info(f"  ⏭️  Skipping - no changes detected")
                        skipped_pages += 1
                        continue
            else:
                page_data = self.extract_page_content(page_title)
            
            if page_data:
                # Calculate content hash
                content_hash = self.content_processor.calculate_content_hash(page_data['raw_content'])
                
                # Update metadata
                self.db_ops.upsert_page_metadata(
                    page_data['title'],
                    page_data['url'],
                    content_hash,
                    status='active'
                )
                
                # Save to database
                if self.db_ops.save_page_to_database(page_data, self.content_processor):
                    successful_crawls += 1
                    updated_pages += 1
            
            # Reduced sleep time for better performance
            time.sleep(1)  # Reduced from 2 seconds
        
        logger.info(f"\n🌐 Modular wiki crawling complete!")
        logger.info(f"✓ Successfully crawled: {successful_crawls} pages")
        logger.info(f"✓ Updated: {updated_pages} pages")
        logger.info(f"⏭️  Skipped (unchanged): {skipped_pages} pages")
        
        return successful_crawls


def main():
    """Main crawler function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            print("22nd Mobile Daedalus Fleet Wiki Crawler - Modular Version")
            print("=" * 60)
            print("Usage:")
            print("  python wiki_crawler.py                    # Standard crawl (~26 curated pages)")
            print("  python wiki_crawler.py --comprehensive    # Comprehensive crawl (all pages)")
            print("  python wiki_crawler.py --force            # Force update all pages")
            print("  python wiki_crawler.py --stats            # Show database statistics")
            print("  python wiki_crawler.py \"PAGE_TITLE\"      # Crawl specific page")
            print("=" * 60)
            print("\nModular Architecture:")
            print("  📡 api_client.py        - MediaWiki API operations")
            print("  🔄 content_processor.py - Content formatting & classification")
            print("  🚀 content_extractor.py - High-level extraction strategies")
            print("  💾 db_operations.py     - Database operations")
            print("  🎯 wiki_crawler.py      - Main orchestrator (this file)")
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
            stats = crawler.db_ops.get_database_stats()
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
                content_hash = crawler.content_processor.calculate_content_hash(page_data['raw_content'])
                # Update metadata
                crawler.db_ops.upsert_page_metadata(
                    page_data['title'],
                    page_data['url'],
                    content_hash,
                    status='active'
                )
                if crawler.db_ops.save_page_to_database(page_data, crawler.content_processor):
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
            stats = crawler.db_ops.get_database_stats()
            print(f"\n📈 Final Database Statistics:")
            print(f"   Total Pages: {stats.get('total_pages', 0)}")
            print(f"   Mission Logs: {stats.get('mission_logs', 0)}")
            print(f"   Ship Info: {stats.get('ship_info', 0)}")
            print(f"   Personnel: {stats.get('personnel', 0)}")
            print(f"   Unique Ships: {stats.get('unique_ships', 0)}")
            print(f"   Tracked Pages: {stats.get('total_tracked_pages', 0)}")
            
            print("\n✅ Modular wiki crawling to elsiebrain database completed successfully!")
        else:
            print("❌ No content was crawled. Please check your internet connection and database.")
            
    except Exception as e:
        print(f"❌ Error during crawling: {e}")
        print("Make sure:")
        print("- The elsiebrain database exists and is accessible")
        print("- You have installed required packages: pip install psycopg2-binary requests beautifulsoup4")


if __name__ == "__main__":
    main() 