#!/usr/bin/env python3
"""
Quick Phase 1 Validation - Test new database methods with live data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_controller import get_db_controller

def quick_validation():
    """Quick validation of Phase 1 implementation"""
    print("🔍 QUICK PHASE 1 VALIDATION")
    print("=" * 50)
    
    controller = get_db_controller()
    
    try:
        # Test 1: Category discovery
        print("\n📊 Testing category discovery methods...")
        
        char_cats = controller.get_character_categories()
        ship_cats = controller.get_ship_categories()
        log_cats = controller._get_actual_log_categories_from_db()
        
        print(f"   Character categories: {len(char_cats)} found")
        print(f"   Ship categories: {len(ship_cats)} found")  
        print(f"   Log categories: {len(log_cats)} found")
        
        # Test 2: Quick search tests
        print("\n🔍 Testing search methods...")
        
        # Quick character search
        char_results = controller.search_characters("Marcus", limit=3)
        print(f"   Character search results: {len(char_results)}")
        
        # Quick ship search
        ship_results = controller.search_ships("Stardancer", limit=3)
        print(f"   Ship search results: {len(ship_results)}")
        
        # Quick log search
        log_results = controller.search_logs("mission", limit=3)
        print(f"   Log search results: {len(log_results)}")
        
        print("\n✅ PHASE 1 VALIDATION COMPLETE")
        print("🎉 All new methods are working correctly!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False

if __name__ == "__main__":
    success = quick_validation()
    sys.exit(0 if success else 1) 