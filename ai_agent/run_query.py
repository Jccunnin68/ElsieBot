#!/usr/bin/env python3
"""
Interactive query script for Elsie AI Agent Database
Allows running custom SQL queries and provides example queries
"""

import sys
import os
import json
from datetime import datetime

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
    print("   SELECT ship_name, COUNT(*) as log_count FROM wiki_pages WHERE page_type = 'mission_log' GROUP BY ship_name ORDER BY log_count DESC;")
    print("\n3. Recent mission logs:")
    print("   SELECT title, ship_name, log_date FROM wiki_pages WHERE page_type = 'mission_log' ORDER BY log_date DESC LIMIT 10;")
    print("\n4. Search content:")
    print("   SELECT title, page_type, ship_name FROM wiki_pages WHERE content ILIKE '%combat%' LIMIT 5;")
    print("\n5. Database statistics:")
    print("   SELECT page_type, COUNT(*) as count FROM wiki_pages GROUP BY page_type ORDER BY count DESC;")
    print("\n6. Find specific character mentions:")
    print("   SELECT title, ship_name FROM wiki_pages WHERE content ILIKE '%captain%' AND page_type = 'mission_log' LIMIT 10;")

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
        "stats": "SELECT page_type, COUNT(*) as count FROM wiki_pages GROUP BY page_type ORDER BY count DESC;",
        "recent": "SELECT title, ship_name, log_date FROM wiki_pages WHERE page_type = 'mission_log' ORDER BY log_date DESC LIMIT 10;",
        "ship_counts": "SELECT ship_name, COUNT(*) as log_count FROM wiki_pages WHERE page_type = 'mission_log' GROUP BY ship_name ORDER BY log_count DESC;",
        "characters": "SELECT title, ship_name FROM wiki_pages WHERE content ILIKE '%captain%' AND page_type = 'mission_log' LIMIT 10;"
    }
    
    if query_name not in predefined_queries:
        print(f"❌ Unknown predefined query: {query_name}")
        print(f"Available queries: {', '.join(predefined_queries.keys())}")
        return False
    
    query = predefined_queries[query_name]
    print(f"🔍 Running predefined query '{query_name}':")
    print(f"   {query}")
    
    return execute_query(query, show_full)

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
            
        elif command in ["ships", "stats", "recent", "ship_counts", "characters"]:
            run_predefined_query(command)
            
        elif command == "custom" and len(sys.argv) > 2:
            # Run custom query passed as argument
            custom_query = " ".join(sys.argv[2:])
            print(f"🔍 Running custom query: {custom_query}")
            execute_query(custom_query)
            
        elif command == "full" and len(sys.argv) > 2:
            # Run any command with full content display
            sub_command = sys.argv[2].lower()
            if sub_command in ["ships", "stats", "recent", "ship_counts", "characters"]:
                print("📄 (Showing full content - no truncation)")
                run_predefined_query(sub_command, show_full=True)
            elif sub_command == "custom" and len(sys.argv) > 3:
                custom_query = " ".join(sys.argv[3:])
                print(f"🔍 Running custom query with full content: {custom_query}")
                print("📄 (Showing full content - no truncation)")
                execute_query(custom_query, show_full=True)
            else:
                print("Usage: python run_query.py full [ships|stats|recent|ship_counts|characters]")
                print("   or: python run_query.py full custom 'SQL_QUERY'")
            
        else:
            print(f"❌ Unknown command: {command}")
            print("Usage:")
            print("  python run_query.py interactive    # Interactive mode")
            print("  python run_query.py examples       # Show example queries")
            print("  python run_query.py tables         # Show database schema")
            print("  python run_query.py ships          # List all ships")
            print("  python run_query.py stats          # Database statistics") 
            print("  python run_query.py recent         # Recent mission logs")
            print("  python run_query.py ship_counts    # Log counts per ship")
            print("  python run_query.py characters     # Find character mentions")
            print("  python run_query.py custom 'SQL'   # Run custom SQL query")
            print("  python run_query.py full [command] # Show full content without truncation")
            
    else:
        # Default: show examples and enter interactive mode
        print_examples()
        print_tables()
        interactive_mode()

if __name__ == "__main__":
    main() 