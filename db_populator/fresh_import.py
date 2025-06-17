#!/usr/bin/env python3
"""
Fresh Database Import Controller
Orchestrates clean import from MediaWiki to categories-only schema
"""

import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional
from content_extractor import ContentExtractor
from content_processor import ContentProcessor
from db_operations import DatabaseOperations


class FreshImportController:
    """Orchestrates fresh import process with clean schema"""
    
    def __init__(self):
        self.extractor = ContentExtractor()
        self.processor = ContentProcessor()
        self.db_ops = DatabaseOperations()
        self.stats = {
            'total_pages': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'categories': {}
        }
    
    def run_fresh_import(self, test_mode: bool = False, limit: Optional[int] = None) -> bool:
        """
        Run complete fresh import process
        
        Args:
            test_mode: If True, run on limited dataset for testing
            limit: Maximum number of pages to process (None = all)
        """
        print("🚀 FRESH DATABASE IMPORT")
        print("=" * 60)
        print(f"⏰ Started at: {datetime.now()}")
        print(f"🧪 Test mode: {test_mode}")
        print(f"📊 Limit: {limit if limit else 'All pages'}")
        
        try:
            # Step 1: Get all page titles from MediaWiki API
            print("\n📋 Step 1: Fetching page titles from MediaWiki API...")
            page_titles = self.get_page_titles(test_mode, limit)
            
            if not page_titles:
                print("❌ No page titles found")
                return False
            
            self.stats['total_pages'] = len(page_titles)
            print(f"   ✓ Found {len(page_titles)} pages to process")
            
            # Step 2: Process each page
            print(f"\n📥 Step 2: Processing {len(page_titles)} pages...")
            self.process_pages(page_titles)
            
            # Step 3: Validate and report
            print(f"\n✅ Step 3: Import validation and reporting...")
            self.validate_import()
            self.print_final_report()
            
            return True
            
        except Exception as e:
            print(f"❌ Error during fresh import: {e}")
            return False
    
    def get_page_titles(self, test_mode: bool, limit: Optional[int]) -> List[str]:
        """Get page titles from MediaWiki API"""
        try:
            # Use the content extractor's API client
            page_titles = self.extractor.get_all_page_titles_from_special_pages()
            
            if test_mode:
                # Use a curated test set for testing
                test_titles = [
                    "USS Stardancer", "USS Adagio", "USS Pilgrim", 
                    "Marcus Blaine", "Talia", "Luna Class Starship",
                    "Large Magellanic Cloud Expedition"
                ]
                page_titles = test_titles
                print(f"   🧪 Using test dataset: {len(page_titles)} pages")
            
            if limit and len(page_titles) > limit:
                page_titles = page_titles[:limit]
                print(f"   📊 Limited to {limit} pages")
            
            return page_titles
            
        except Exception as e:
            print(f"   ❌ Error getting page titles: {e}")
            return []
    
    def process_pages(self, page_titles: List[str]) -> None:
        """Process each page and save to database"""
        print(f"   📥 Processing {len(page_titles)} pages...")
        
        for i, title in enumerate(page_titles, 1):
            try:
                print(f"\n   📄 [{i}/{len(page_titles)}] Processing: {title}")
                
                # Extract content from MediaWiki
                page_data = self.extractor.extract_page_content(title)
                
                if not page_data:
                    print(f"      ⚠️  No content extracted for: {title}")
                    self.stats['skipped'] += 1
                    continue
                
                # Save to database (classification happens inside)
                success = self.db_ops.save_page_to_database(page_data, self.processor)
                
                if success:
                    self.stats['successful'] += 1
                    
                    # Track category statistics
                    categories = self.processor.get_categories_from_page_data(page_data)
                    for category in categories:
                        self.stats['categories'][category] = self.stats['categories'].get(category, 0) + 1
                else:
                    self.stats['failed'] += 1
                
                # Progress reporting
                if i % 10 == 0:
                    print(f"      📊 Progress: {i}/{len(page_titles)} ({i/len(page_titles)*100:.1f}%)")
                
                # Small delay to be nice to the API
                time.sleep(0.1)
                
            except Exception as e:
                print(f"      ❌ Error processing {title}: {e}")
                self.stats['failed'] += 1
                continue
    
    def validate_import(self) -> None:
        """Validate the import results"""
        print("   🔍 Validating import results...")
        
        try:
            # Get database statistics
            db_stats = self.db_ops.get_database_stats()
            
            if db_stats:
                wiki_stats = db_stats.get('wiki_stats', {})
                category_stats = db_stats.get('category_stats', [])
                
                total_in_db = wiki_stats.get('total_pages', 0)
                pages_with_categories = wiki_stats.get('pages_with_categories', 0)
                pages_without_categories = wiki_stats.get('pages_without_categories', 0)
                
                print(f"      📊 Database contains {total_in_db} total pages")
                print(f"      ✅ Pages with categories: {pages_with_categories}")
                print(f"      ❌ Pages without categories: {pages_without_categories}")
                
                if pages_without_categories > 0:
                    print(f"      ⚠️  WARNING: {pages_without_categories} pages missing categories!")
                
                # Show top categories
                print(f"      📋 Top categories:")
                for i, cat_stat in enumerate(category_stats[:5], 1):
                    print(f"         {i}. {cat_stat['category']}: {cat_stat['count']} pages")
                    
        except Exception as e:
            print(f"      ❌ Validation error: {e}")
    
    def print_final_report(self) -> None:
        """Print final import report"""
        print("\n🎉 FRESH IMPORT COMPLETE!")
        print("=" * 60)
        print(f"⏰ Finished at: {datetime.now()}")
        print(f"\n📊 IMPORT STATISTICS:")
        print(f"   📄 Total pages processed: {self.stats['total_pages']}")
        print(f"   ✅ Successfully imported: {self.stats['successful']}")
        print(f"   ❌ Failed to import: {self.stats['failed']}")
        print(f"   ⏭️  Skipped (no content): {self.stats['skipped']}")
        
        success_rate = (self.stats['successful'] / self.stats['total_pages']) * 100 if self.stats['total_pages'] > 0 else 0
        print(f"   🎯 Success rate: {success_rate:.1f}%")
        
        print(f"\n📋 CATEGORY DISTRIBUTION:")
        sorted_categories = sorted(self.stats['categories'].items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories:
            print(f"   📄 {category}: {count} pages")
        
        print("\n✅ Fresh import completed successfully!")
        print("🚀 Database is ready for use!")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🚀 Fresh Database Import Controller")
        print("=" * 60)
        print("Usage:")
        print("  python fresh_import.py test              # Test import (limited dataset)")
        print("  python fresh_import.py full              # Full import (all pages)")
        print("  python fresh_import.py limited [N]       # Import N pages only")
        return
    
    command = sys.argv[1].lower()
    controller = FreshImportController()
    
    if command == "test":
        success = controller.run_fresh_import(test_mode=True)
    elif command == "full":
        success = controller.run_fresh_import(test_mode=False)
    elif command == "limited":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        success = controller.run_fresh_import(test_mode=False, limit=limit)
    else:
        print(f"❌ Unknown command: {command}")
        return
    
    if success:
        print("\n🎉 Import completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Import failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 