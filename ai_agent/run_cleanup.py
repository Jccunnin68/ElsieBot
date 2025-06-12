#!/usr/bin/env python3
"""
Database cleanup script for Elsie AI Agent
Extracts ship names from mission log titles and removes seed data
"""

import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from handlers.ai_wisdom.content_retrieval_db import run_database_cleanup, cleanup_ship_names_only, cleanup_seed_data_only

def main():
    """Main cleanup function"""
    print("🚀 ELSIE DATABASE CLEANUP TOOL")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        operation = sys.argv[1].lower()
        
        if operation == "ships":
            print("🚢 Running ship name cleanup only...")
            result = cleanup_ship_names_only()
            
        elif operation == "seed":
            print("🗑️  Running seed data cleanup only...")
            result = cleanup_seed_data_only()
            
        elif operation == "all":
            print("🔧 Running full database cleanup...")
            result = run_database_cleanup()
            
        else:
            print(f"❌ Unknown operation: {operation}")
            print("Usage: python run_cleanup.py [ships|seed|all]")
            return
            
    else:
        print("🔧 Running full database cleanup...")
        result = run_database_cleanup()
    
    if result:
        print("✅ Cleanup completed successfully!")
    else:
        print("❌ Cleanup failed!")

if __name__ == "__main__":
    main() 