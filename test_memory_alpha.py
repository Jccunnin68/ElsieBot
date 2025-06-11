#!/usr/bin/env python3
"""
Test script for Memory Alpha integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_agent'))

from content_retrieval_db import search_memory_alpha

def test_memory_alpha_search():
    """Test the Memory Alpha search functionality"""
    
    print("🧪 TESTING MEMORY ALPHA INTEGRATION")
    print("=" * 50)
    
    # Test queries
    test_queries = [
        "USS Enterprise",
        "Jean-Luc Picard", 
        "Data",
        "Vulcans",
        "Klingon Empire",
        "Warp drive"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Testing query: '{query}'")
        print("-" * 30)
        
        result = search_memory_alpha(query, limit=2)
        
        if result:
            print(f"✅ SUCCESS: Found {len(result)} characters of content")
            # Show first 200 characters as preview
            preview = result[:200] + "..." if len(result) > 200 else result
            print(f"Preview: {preview}")
        else:
            print("❌ FAILED: No content returned")
    
    print("\n" + "=" * 50)
    print("🧪 MEMORY ALPHA TESTING COMPLETE")

if __name__ == "__main__":
    test_memory_alpha_search() 