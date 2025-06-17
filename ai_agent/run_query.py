#!/usr/bin/env python3
"""
Interactive query script for Elsie AI Agent Database
Allows running custom SQL queries and provides example queries
"""

import sys
import os
import json
from datetime import datetime
from typing import List

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_controller import get_db_controller

def print_header():
    """Print the query tool header"""
    print("🚀 ELSIE DATABASE QUERY TOOL")
    print("=" * 60)

def print_examples():
    """Print example queries"""
    print("\n📚 EXAMPLE QUERIES:")
    print("-" * 30)
    print("1. Show all ships:")
    print("   SELECT DISTINCT ship_name FROM wiki_pages WHERE ship_name IS NOT NULL;")
    print("\n2. Count logs per ship:")
    print("   SELECT ship_name, COUNT(*) as log_count FROM wiki_pages WHERE 'Stardancer Log' = ANY(categories) OR 'Adagio Log' = ANY(categories) GROUP BY ship_name ORDER BY log_count DESC;")
    print("\n3. Recent mission logs:")
    print("   SELECT title, ship_name, log_date FROM wiki_pages WHERE categories && ARRAY['Stardancer Log', 'Adagio Log', 'Pilgrim Log'] ORDER BY log_date DESC LIMIT 10;")
    print("\n4. Search content:")
    print("   SELECT title, categories, ship_name FROM wiki_pages WHERE raw_content ILIKE '%combat%' LIMIT 5;")
    print("\n5. Database statistics:")
    print("   SELECT unnest(categories) as category, COUNT(*) as count FROM wiki_pages WHERE categories IS NOT NULL GROUP BY unnest(categories) ORDER BY count DESC;")
    print("\n6. Find specific character mentions:")
    print("   SELECT title, ship_name FROM wiki_pages WHERE raw_content ILIKE '%captain%' AND categories && ARRAY['Stardancer Log', 'Adagio Log'] LIMIT 10;")
    print("\n7. Content access statistics:")
    print("   SELECT title, categories, content_accessed FROM wiki_pages WHERE content_accessed > 0 ORDER BY content_accessed DESC LIMIT 10;")
    print("\n8. Category breakdown:")
    print("   SELECT unnest(categories) as category, COUNT(*) as count FROM wiki_pages WHERE categories IS NOT NULL GROUP BY unnest(categories) ORDER BY count DESC LIMIT 15;")

def print_tables():
    """Show available tables and their structure"""
    try:
        controller = get_db_controller()
        schema_info = controller.get_schema_info()
        
        print("\n🗄️  DATABASE SCHEMA:")
        print("-" * 30)
        
        for table_name, columns in schema_info.items():
            print(f"\n📋 Table: {table_name}")
            for col in columns:
                col_info = f"  • {col['column_name']} ({col['data_type']}"
                if col['is_nullable'] == 'NO':
                    col_info += ", NOT NULL"
                col_info += ")"
                print(col_info)
                
    except Exception as e:
        print(f"❌ Error getting schema info: {e}")

def execute_query(query: str, show_full: bool = False) -> bool:
    """Execute a custom SQL query and display results"""
    try:
        controller = get_db_controller()
        
        with controller.get_connection() as conn:
            with conn.cursor() as cur:
                # Execute the query
                cur.execute(query)
                
                # Check if it's a SELECT query
                if query.strip().upper().startswith('SELECT'):
                    results = cur.fetchall()
                    column_names = [desc[0] for desc in cur.description]
                    
                    print(f"\n📊 QUERY RESULTS ({len(results)} rows):")
                    print("-" * 50)
                    
                    if results:
                        # Print column headers
                        header = " | ".join(column_names)
                        print(header)
                        print("-" * len(header))
                        
                        # Print rows with full data
                        for i, row in enumerate(results, 1):
                            print(f"\nRow {i}:")
                            for col_name, val in zip(column_names, row):
                                # Handle None values
                                display_val = str(val) if val is not None else "NULL"
                                
                                # For very long content, show first 200 chars unless show_full is True
                                if len(display_val) > 200 and not show_full:
                                    print(f"  {col_name}: {display_val[:200]}... [CONTENT TRUNCATED - {len(display_val)} total chars]")
                                    print(f"    (Use 'full' command to see complete content)")
                                else:
                                    print(f"  {col_name}: {display_val}")
                            print("-" * 50)
                    else:
                        print("No results found.")
                        
                else:
                    # For non-SELECT queries, show affected rows
                    print(f"\n✅ Query executed successfully. Rows affected: {cur.rowcount}")
                    
        return True
        
    except Exception as e:
        print(f"❌ Error executing query: {e}")
        return False

def interactive_mode():
    """Run in interactive mode"""
    print("\n🔧 INTERACTIVE MODE")
    print("Type your SQL queries (or 'help', 'examples', 'tables', 'full', 'exit'):")
    print("  - Use 'full' before a query to show complete content without truncation")
    print("-" * 50)
    
    show_full = False
    
    while True:
        try:
            query = input("\n📝 SQL> ").strip()
            
            if not query:
                continue
                
            if query.lower() == 'exit':
                print("👋 Goodbye!")
                break
            elif query.lower() == 'help':
                print_examples()
                continue
            elif query.lower() == 'examples':
                print_examples()
                continue
            elif query.lower() == 'tables':
                print_tables()
                continue
            elif query.lower() == 'full':
                show_full = not show_full
                status = "enabled" if show_full else "disabled"
                print(f"🔧 Full content display {status}")
                continue
                
            # Execute the query
            print(f"\n🔍 Executing: {query}")
            if show_full:
                print("📄 (Showing full content - no truncation)")
            execute_query(query, show_full)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def run_predefined_query(query_name: str, show_full: bool = False) -> bool:
    """Run a predefined query by name"""
    predefined_queries = {
        "ships": "SELECT DISTINCT ship_name FROM wiki_pages WHERE ship_name IS NOT NULL ORDER BY ship_name;",
        "stats": "SELECT unnest(categories) as category, COUNT(*) as count FROM wiki_pages WHERE categories IS NOT NULL GROUP BY unnest(categories) ORDER BY count DESC LIMIT 15;",
        "recent": "SELECT title, ship_name, log_date FROM wiki_pages WHERE categories && ARRAY['Stardancer Log', 'Adagio Log', 'Pilgrim Log', 'Banshee Log', 'Gigantes Log'] ORDER BY log_date DESC LIMIT 10;",
        "ship_counts": "SELECT ship_name, COUNT(*) as log_count FROM wiki_pages WHERE categories && ARRAY['Stardancer Log', 'Adagio Log', 'Pilgrim Log', 'Banshee Log', 'Gigantes Log'] AND ship_name IS NOT NULL GROUP BY ship_name ORDER BY log_count DESC;",
        "characters": "SELECT title, ship_name FROM wiki_pages WHERE raw_content ILIKE '%captain%' AND categories && ARRAY['Stardancer Log', 'Adagio Log', 'Pilgrim Log'] LIMIT 10;",
        "access": "SELECT title, categories, content_accessed FROM wiki_pages WHERE content_accessed > 0 ORDER BY content_accessed DESC LIMIT 10;",
        "categories": "SELECT unnest(categories) as category, COUNT(*) as count FROM wiki_pages WHERE categories IS NOT NULL GROUP BY unnest(categories) ORDER BY count DESC;",
        "ship_categories": "SELECT DISTINCT unnest(categories) as category FROM wiki_pages WHERE categories IS NOT NULL AND EXISTS (SELECT 1 FROM unnest(categories) cat WHERE LOWER(cat) LIKE '%ship%') ORDER BY category;"
    }
    
    if query_name not in predefined_queries:
        print(f"❌ Unknown predefined query: {query_name}")
        print(f"Available queries: {', '.join(predefined_queries.keys())}")
        return False
    
    query = predefined_queries[query_name]
    print(f"🔍 Running predefined query '{query_name}':")
    print(f"   {query}")
    
    return execute_query(query, show_full)

def test_enhanced_search(query: str, debug_level: int = 2) -> bool:
    """Test the enhanced search functionality with debug output"""
    try:
        controller = get_db_controller()
        
        print(f"\n🔧 TESTING ENHANCED SEARCH")
        print(f"Query: '{query}', Debug Level: {debug_level}")
        print("-" * 50)
        
        # Test regular search
        print(f"\n📋 REGULAR SEARCH:")
        results = controller.search_pages(query, limit=5, debug_level=debug_level)
        
        # Test log-only search
        print(f"\n📋 LOG-ONLY SEARCH:")
        log_results = controller.search_pages(query, limit=5, force_mission_logs_only=True, debug_level=debug_level)
        
        # Test ship-specific search if query contains ship name
        ship_names = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta']
        for ship in ship_names:
            if ship in query.lower():
                print(f"\n📋 SHIP-SPECIFIC SEARCH ({ship.upper()}):")
                ship_results = controller.search_pages(query, ship_name=ship, limit=3, debug_level=debug_level)
                break
        
        return True
        
    except Exception as e:
        print(f"❌ Error in enhanced search test: {e}")
        return False

def test_character_disambiguation(test_cases: List[str]) -> bool:
    """Test character name disambiguation with different contexts"""
    try:
        from handlers.ai_wisdom.log_patterns import resolve_character_name_with_context
        
        print(f"\n🎭 TESTING CHARACTER DISAMBIGUATION")
        print("-" * 50)
        
        for i, case in enumerate(test_cases, 1):
            parts = case.split('|')
            name = parts[0].strip()
            ship_context = parts[1].strip() if len(parts) > 1 else None
            surrounding_text = parts[2].strip() if len(parts) > 2 else ""
            
            print(f"\nTest {i}: '{name}'")
            print(f"   Ship Context: {ship_context or 'None'}")
            print(f"   Surrounding: '{surrounding_text}'")
            
            resolved = resolve_character_name_with_context(name, ship_context, surrounding_text)
            print(f"   → Resolved: '{resolved}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in character disambiguation test: {e}")
        return False

def test_log_category_filtering() -> bool:
    """Test the new log category filtering functionality using actual database categories"""
    try:
        controller = get_db_controller()
        
        print(f"\n📊 TESTING LOG CATEGORY FILTERING")
        print("-" * 50)
        
        # Get actual log categories from database
        print(f"Getting actual log categories from database:")
        log_categories = controller._get_actual_log_categories_from_db()
        
        print(f"\nActual log categories found in database:")
        for cat in log_categories:
            print(f"   - {cat}")
        
        # Test category detection logic
        test_categories = [
            'Stardancer Log', 'Ship Information', 'Stardancer Episode Summary', 
            'Mission Log', 'Characters', 'Medical Log', 'General Information',
            'Adagio Episode Summary', 'Pilgrim Log'
        ]
        
        print(f"\nTesting category filtering logic:")
        for cat in test_categories:
            is_log = 'log' in cat.lower() and 'episode summary' not in cat.lower()
            print(f"   '{cat}': {'✓ LOG' if is_log else '✗ NOT LOG'}")
        
        # Test filtering
        print(f"\nFiltering test categories:")
        filtered = [cat for cat in test_categories if 'log' in cat.lower() and 'episode summary' not in cat.lower()]
        print(f"   Original: {len(test_categories)} categories")
        print(f"   Filtered: {len(filtered)} log categories")
        for cat in filtered:
            print(f"   - {cat}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in log category filtering test: {e}")
        return False

def test_ship_categories() -> bool:
    """Test the ship category detection functionality"""
    try:
        controller = get_db_controller()
        
        print(f"\n🚢 TESTING SHIP CATEGORY DETECTION")
        print("-" * 50)
        
        # Test the get_ship_categories method
        print(f"Getting ship categories from database:")
        ship_categories = controller.get_ship_categories()
        
        print(f"\nShip categories found ({len(ship_categories)}):")
        for cat in sorted(ship_categories):
            print(f"   - {cat}")
        
        # Test search_ships method with USS Stardancer
        print(f"\n🔍 TESTING SEARCH_SHIPS METHOD:")
        print(f"Searching for 'USS Stardancer'...")
        
        ship_results = controller.search_ships("USS Stardancer", limit=5)
        
        print(f"\nShip search results:")
        if ship_results:
            for i, result in enumerate(ship_results, 1):
                title = result.get('title', 'No title')
                raw_content = result.get('raw_content', '')
                content_preview = raw_content[:200] + '...' if len(raw_content) > 200 else raw_content
                categories = result.get('categories', [])
                
                print(f"\n   Result {i}: {title}")
                print(f"   Categories: {categories}")
                print(f"   Content length: {len(raw_content)} characters")
                print(f"   Content preview: {content_preview}")
        else:
            print("   No results found")
        
        # Test with different ship names
        test_ships = ['Stardancer', 'USS Stardancer', 'stardancer']
        
        print(f"\n🔍 TESTING DIFFERENT SHIP NAME FORMATS:")
        for ship_name in test_ships:
            print(f"\nTesting: '{ship_name}'")
            results = controller.search_ships(ship_name, limit=2)
            print(f"   Found {len(results)} results")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in ship category test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stardancer_query() -> bool:
    """Test the specific USS Stardancer query that was having issues"""
    try:
        controller = get_db_controller()
        
        print(f"\n🌟 TESTING USS STARDANCER QUERY")
        print("-" * 50)
        
        # Test the exact query that was problematic
        query = "Tell me about the stardancer"
        
        print(f"Query: '{query}'")
        print(f"\n1. Testing regular search_pages:")
        regular_results = controller.search_pages(query, limit=5, debug_level=2)
        
        print(f"\n2. Testing search_ships:")
        ship_results = controller.search_ships("stardancer", limit=5)
        
        print(f"\n3. Testing search_pages with ship_name parameter:")
        ship_param_results = controller.search_pages(query, ship_name="stardancer", limit=5, debug_level=2)
        
        # Compare results
        print(f"\n📊 RESULTS COMPARISON:")
        print(f"   Regular search: {len(regular_results)} results")
        print(f"   Ship search: {len(ship_results)} results")
        print(f"   Ship param search: {len(ship_param_results)} results")
        
        # Show detailed content from ship search
        if ship_results:
            print(f"\n📄 DETAILED SHIP SEARCH RESULTS:")
            for i, result in enumerate(ship_results[:2], 1):
                title = result.get('title', 'No title')
                raw_content = result.get('raw_content', '')
                categories = result.get('categories', [])
                
                print(f"\n   Result {i}: {title}")
                print(f"   Categories: {categories}")
                print(f"   Content length: {len(raw_content)} characters")
                print(f"   Content preview (first 500 chars):")
                print(f"   {raw_content[:500]}{'...' if len(raw_content) > 500 else ''}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in USS Stardancer query test: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_content_storage() -> bool:
    """Debug content storage issues by checking raw_content vs content fields"""
    try:
        controller = get_db_controller()
        
        print(f"\n🔍 DEBUGGING CONTENT STORAGE")
        print("-" * 50)
        
        # Check USS Stardancer specifically
        print(f"Checking USS Stardancer content storage:")
        
        # Direct SQL query to check content fields
        query = """
            SELECT 
                id,
                title,
                CASE 
                    WHEN raw_content IS NULL THEN 'NULL'
                    WHEN raw_content = '' THEN 'EMPTY STRING'
                    WHEN LENGTH(raw_content) = 0 THEN 'ZERO LENGTH'
                    ELSE 'HAS CONTENT'
                END as raw_content_status,
                CASE 
                    WHEN content IS NULL THEN 'NULL'
                    WHEN content = '' THEN 'EMPTY STRING'
                    WHEN LENGTH(content) = 0 THEN 'ZERO LENGTH'
                    ELSE 'HAS CONTENT'
                END as processed_content_status,
                LENGTH(raw_content) as raw_length,
                categories
            FROM wiki_pages 
            WHERE LOWER(title) LIKE '%stardancer%'
            AND title NOT LIKE '%Log%'
            ORDER BY id;
        """
        
        print(f"Running content debug query...")
        execute_query(query, show_full=True)
        
        # Also check what search_ships returns vs direct query
        print(f"\n🔍 COMPARING SEARCH_SHIPS VS DIRECT QUERY:")
        
        print(f"\n1. search_ships('USS Stardancer') results:")
        ship_results = controller.search_ships("USS Stardancer", limit=3)
        for i, result in enumerate(ship_results, 1):
            title = result.get('title', 'No title')
            raw_content = result.get('raw_content', '')
            content = result.get('content', '')
            
            print(f"   Result {i}: {title}")
            print(f"   raw_content length: {len(raw_content) if raw_content else 0}")
            print(f"   raw_content preview: {raw_content[:100] if raw_content else 'EMPTY'}")
        
        print(f"\n2. Direct database query for same records:")
        direct_query = """
            SELECT id, title, raw_content, categories
            FROM wiki_pages 
            WHERE LOWER(title) LIKE '%stardancer%'
            AND title NOT LIKE '%Log%'
            LIMIT 3;
        """
        execute_query(direct_query, show_full=False)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in content storage debug: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print_header()
    
    # Check database connection
    try:
        controller = get_db_controller()
        stats = controller.get_stats()
        print(f"✅ Connected to database: {stats.get('total_pages', 0)} pages")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "interactive" or command == "i":
            interactive_mode()
            
        elif command == "examples":
            print_examples()
            
        elif command == "tables":
            print_tables()
            
        elif command in ["ships", "stats", "recent", "ship_counts", "characters", "access", "categories", "ship_categories"]:
            run_predefined_query(command)
            
        elif command == "test_search":
            # Test enhanced search functionality
            query = sys.argv[2] if len(sys.argv) > 2 else "Tolena"
            debug_level = int(sys.argv[3]) if len(sys.argv) > 3 else 2
            test_enhanced_search(query, debug_level)
            
        elif command == "test_characters":
            # Test character disambiguation
            test_cases = [
                "Tolena | stardancer | Ensign Tolena reported to the bridge",
                "Tolena | protector | Doctor Tolena examined the patient",
                "Blaine | stardancer | Captain Blaine issued orders",
                "Blaine | | Ensign Blaine assisted with the mission",
                "tolena | | medical emergency on deck 5"
            ]
            test_character_disambiguation(test_cases)
            
        elif command == "test_logs":
            # Test log category filtering
            test_log_category_filtering()
            
        elif command == "test_ships":
            # Test ship category detection
            test_ship_categories()
            
        elif command == "test_stardancer":
            # Test the specific USS Stardancer query
            test_stardancer_query()
            
        elif command == "debug_content":
            # Debug content storage issues
            debug_content_storage()
            
      
        elif command == "custom" and len(sys.argv) > 2:
            # Run custom query passed as argument
            custom_query = " ".join(sys.argv[2:])
            print(f"🔍 Running custom query: {custom_query}")
            execute_query(custom_query)
            
        elif command == "full" and len(sys.argv) > 2:
            # Run any command with full content display
            sub_command = sys.argv[2].lower()
            if sub_command in ["ships", "stats", "recent", "ship_counts", "characters", "access", "categories", "ship_categories"]:
                print("📄 (Showing full content - no truncation)")
                run_predefined_query(sub_command, show_full=True)
            elif sub_command == "custom" and len(sys.argv) > 3:
                custom_query = " ".join(sys.argv[3:])
                print(f"🔍 Running custom query with full content: {custom_query}")
                print("📄 (Showing full content - no truncation)")
                execute_query(custom_query, show_full=True)
            else:
                print("Usage: python run_query.py full [ships|stats|recent|ship_counts|characters|access|categories|ship_categories]")
                print("   or: python run_query.py full custom 'SQL_QUERY'")
            
        else:
            print(f"❌ Unknown command: {command}")
            print("Usage:")
            print("  python run_query.py interactive      # Interactive mode")
            print("  python run_query.py examples         # Show example queries")
            print("  python run_query.py tables           # Show database schema")
            print("  python run_query.py ships            # List all ships")
            print("  python run_query.py stats            # Database statistics") 
            print("  python run_query.py recent           # Recent mission logs")
            print("  python run_query.py ship_counts      # Log counts per ship")
            print("  python run_query.py characters       # Find character mentions")
            print("  python run_query.py access           # Content access statistics")
            print("  python run_query.py categories       # Category breakdown")
            print("  python run_query.py ship_categories  # Ship-related categories")
            print("  python run_query.py custom 'SQL'     # Run custom SQL query")
            print("  python run_query.py full [command]   # Show full content without truncation")
            print("")
            print("  NEW TESTING COMMANDS:")
            print("  python run_query.py test_search 'query' [debug_level]  # Test enhanced search")
            print("  python run_query.py test_characters   # Test character disambiguation")
            print("  python run_query.py test_logs         # Test log category filtering")
            print("  python run_query.py test_ships        # Test ship category detection")
            print("  python run_query.py test_stardancer   # Test USS Stardancer specific query")
            print("  python run_query.py debug_content     # Debug content storage issues")
            print("  python run_query.py debug_flow        # Debug content flow from DB to response")
            
    else:
        # Default: show examples and enter interactive mode
        print_examples()
        print_tables()
        interactive_mode()

if __name__ == "__main__":
    main() 