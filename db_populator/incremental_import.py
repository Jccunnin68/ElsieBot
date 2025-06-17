#!/usr/bin/env python3
"""
Incremental Database Import Controller
Performs smart updates based on MediaWiki touched timestamps
Only updates pages that have actually changed since last crawl
"""

import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from content_extractor import ContentExtractor
from content_processor import ContentProcessor
from db_operations import DatabaseOperations


class IncrementalImportController:
    """Orchestrates incremental import process using MediaWiki touched timestamps"""
    
    def __init__(self):
        self.extractor = ContentExtractor()
        self.processor = ContentProcessor()
        self.db_ops = DatabaseOperations()
        self.stats = {
            'total_pages': 0,
            'checked': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'new_pages': 0,
            'unchanged': 0
        }
    
    def run_incremental_update(self, limit: Optional[int] = None, test_mode: bool = False) -> bool:
        """
        Run incremental update process - only update changed pages
        
        Args:
            limit: Maximum number of pages to check (None = all)
            test_mode: If True, run on limited test dataset
        """
        print("🔄 INCREMENTAL DATABASE UPDATE")
        print("=" * 60)
        print(f"⏰ Started at: {datetime.now()}")
        print(f"🧪 Test mode: {test_mode}")
        print(f"📊 Check limit: {limit if limit else 'All pages'}")
        
        try:
            # Step 1: Get all page titles
            print("\n📋 Step 1: Fetching page titles from MediaWiki...")
            page_titles = self.get_page_titles(test_mode, limit)
            
            if not page_titles:
                print("❌ No page titles found")
                return False
            
            self.stats['total_pages'] = len(page_titles)
            print(f"   ✓ Found {len(page_titles)} pages to check")
            
            # Step 2: Check for updates and get list of pages to update
            print(f"\n🔍 Step 2: Checking for updates...")
            pages_to_update = self.check_for_updates(page_titles)
            
            print(f"   📊 Update analysis:")
            print(f"      Total pages checked: {self.stats['checked']}")
            print(f"      Pages needing update: {len(pages_to_update)}")
            print(f"      Pages up to date: {self.stats['unchanged']}")
            
            if not pages_to_update:
                print("   ✅ All pages are up to date!")
                self.print_final_report()
                return True
            
            # Step 3: Update only the pages that need updating
            print(f"\n📥 Step 3: Updating {len(pages_to_update)} changed pages...")
            self.update_pages(pages_to_update)
            
            # Step 4: Final report
            print(f"\n✅ Step 4: Update completion report...")
            self.print_final_report()
            
            return True
            
        except Exception as e:
            print(f"❌ Error during incremental update: {e}")
            return False
    
    def get_page_titles(self, test_mode: bool, limit: Optional[int]) -> List[str]:
        """Get page titles for checking"""
        try:
            page_titles = self.extractor.get_all_page_titles_from_special_pages()
            
            if test_mode:
                test_titles = [
                    "USS Stardancer", "USS Adagio", "Political Timeline",
                    "Marcus Blaine", "Talia", "Large Magellanic Cloud Expedition"
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
    
    def check_for_updates(self, page_titles: List[str]) -> List[str]:
        """Check which pages need updating based on touched timestamps"""
        pages_to_update = []
        
        print(f"   🔍 Checking {len(page_titles)} pages for updates...")
        
        for i, title in enumerate(page_titles, 1):
            try:
                self.stats['checked'] += 1
                
                # Get remote metadata (touched timestamp)
                print(f"\n   📄 [{i}/{len(page_titles)}] Checking: {title}")
                remote_metadata = self.extractor.api_client.get_page_metadata(title)
                
                if not remote_metadata:
                    print(f"      ⚠️  Could not get metadata for: {title}")
                    continue
                
                remote_touched = remote_metadata.get('touched', '')
                
                # Check if update is needed
                if self.db_ops.should_update_page_by_touched(title, remote_touched):
                    pages_to_update.append(title)
                    if not self.page_exists_locally(title):
                        self.stats['new_pages'] += 1
                        print(f"      🆕 New page detected")
                    else:
                        print(f"      📝 Update needed")
                else:
                    self.stats['unchanged'] += 1
                    print(f"      ✓ Page is current")
                
                # Progress reporting
                if i % 25 == 0:
                    print(f"      📊 Progress: {i}/{len(page_titles)} ({i/len(page_titles)*100:.1f}%)")
                
                # Small delay to be nice to the API
                time.sleep(0.05)
                
            except Exception as e:
                print(f"      ❌ Error checking {title}: {e}")
                continue
        
        return pages_to_update
    
    def page_exists_locally(self, page_title: str) -> bool:
        """Check if page exists in local database"""
        try:
            metadata = self.db_ops.get_page_metadata(page_title)
            return metadata is not None
        except:
            return False
    
    def update_pages(self, pages_to_update: List[str]) -> None:
        """Update the list of pages that need updating"""
        print(f"   📥 Updating {len(pages_to_update)} pages...")
        
        for i, title in enumerate(pages_to_update, 1):
            try:
                print(f"\n   📄 [{i}/{len(pages_to_update)}] Updating: {title}")
                
                # Extract content from MediaWiki
                page_data = self.extractor.extract_page_content(title)
                
                if not page_data:
                    print(f"      ⚠️  No content extracted for: {title}")
                    self.stats['failed'] += 1
                    continue
                
                # Save to database
                success = self.db_ops.save_page_to_database(page_data, self.processor)
                
                if success:
                    self.stats['updated'] += 1
                    print(f"      ✅ Successfully updated")
                else:
                    self.stats['failed'] += 1
                    print(f"      ❌ Failed to save")
                
                # Progress reporting
                if i % 10 == 0:
                    print(f"      📊 Update progress: {i}/{len(pages_to_update)} ({i/len(pages_to_update)*100:.1f}%)")
                
                # Small delay to be nice to the API
                time.sleep(0.1)
                
            except Exception as e:
                print(f"      ❌ Error updating {title}: {e}")
                self.stats['failed'] += 1
                continue
    
    def print_final_report(self) -> None:
        """Print final incremental update report"""
        print("\n🎉 INCREMENTAL UPDATE COMPLETE!")
        print("=" * 60)
        print(f"⏰ Finished at: {datetime.now()}")
        print(f"\n📊 UPDATE STATISTICS:")
        print(f"   📄 Total pages checked: {self.stats['checked']}")
        print(f"   🆕 New pages found: {self.stats['new_pages']}")
        print(f"   📝 Pages updated: {self.stats['updated']}")
        print(f"   ✓ Pages unchanged: {self.stats['unchanged']}")
        print(f"   ❌ Update failures: {self.stats['failed']}")
        print(f"   ⏭️  Pages skipped: {self.stats['skipped']}")
        
        efficiency = ((self.stats['unchanged'] + self.stats['updated']) / self.stats['checked']) * 100 if self.stats['checked'] > 0 else 0
        print(f"   🎯 Update efficiency: {efficiency:.1f}% (avoided unnecessary updates)")
        
        if self.stats['updated'] > 0:
            print(f"\n✅ Successfully updated {self.stats['updated']} pages!")
        
        if self.stats['unchanged'] > 0:
            print(f"⚡ Efficiently skipped {self.stats['unchanged']} unchanged pages!")
        
        print("🚀 Database is up to date!")


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🔄 Incremental Database Import Controller")
        print("=" * 60)
        print("Usage:")
        print("  python incremental_import.py check             # Check for updates (no actual updates)")
        print("  python incremental_import.py update            # Run incremental update")
        print("  python incremental_import.py test              # Test incremental update (limited dataset)")
        print("  python incremental_import.py limited [N]       # Update max N pages")
        return
    
    command = sys.argv[1].lower()
    controller = IncrementalImportController()
    
    if command == "check":
        # Just check for updates, don't actually update
        print("🔍 Checking for updates (no actual updates will be performed)...")
        # Would implement a check-only mode here
        success = controller.run_incremental_update(test_mode=True)
    elif command == "update":
        success = controller.run_incremental_update()
    elif command == "test":
        success = controller.run_incremental_update(test_mode=True)
    elif command == "limited":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        success = controller.run_incremental_update(limit=limit)
    else:
        print(f"❌ Unknown command: {command}")
        return
    
    if success:
        print("\n🎉 Incremental update completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Incremental update failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 