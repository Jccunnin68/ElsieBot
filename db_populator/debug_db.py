#!/usr/bin/env python3

import psycopg2

def debug_database():
    # Try different database configurations
    configs = [
        {
            'dbname': 'elsiebrain',
            'user': 'elsie',
            'password': 'elsie123',
            'host': 'localhost',
            'port': '5433'
        },
        {
            'dbname': 'elsiebrain',
            'user': 'elsiebrain',
            'password': 'elsiebrain',
            'host': 'localhost',
            'port': '5432'
        }
    ]
    
    for i, config in enumerate(configs):
        print(f"\n--- Testing configuration {i+1} ---")
        try:
            conn = psycopg2.connect(**config)
            cursor = conn.cursor()
            
            print(f"✓ Connected successfully with config: {config}")
            
            # Check what tables exist
            cursor.execute('''
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            ''')
            
            tables = cursor.fetchall()
            print(f"Tables found: {[t[0] for t in tables]}")
            
            # Check if wiki_pages table exists and has data
            try:
                cursor.execute('SELECT COUNT(*) FROM wiki_pages')
                count = cursor.fetchone()[0]
                print(f"wiki_pages table has {count} rows")
                
                if count > 0:
                    # Check columns
                    cursor.execute('''
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'wiki_pages'
                        ORDER BY ordinal_position
                    ''')
                    columns = cursor.fetchall()
                    print(f"Columns in wiki_pages: {[c[0] for c in columns]}")
                    
                    # Get page type distribution
                    cursor.execute('''
                        SELECT page_type, COUNT(*) as count 
                        FROM wiki_pages 
                        GROUP BY page_type 
                        ORDER BY count DESC
                    ''')
                    
                    results = cursor.fetchall()
                    print('\nPage Type Distribution:')
                    print('=' * 50)
                    for page_type, count in results:
                        print(f'{page_type}: {count}')
                    
                    return  # Success, exit
                    
            except Exception as e:
                print(f"Error querying wiki_pages: {e}")
                
            # Check if pages table exists instead
            try:
                cursor.execute('SELECT COUNT(*) FROM pages')
                count = cursor.fetchone()[0]
                print(f"pages table has {count} rows")
                
                if count > 0:
                    # Check columns
                    cursor.execute('''
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'pages' 
                        ORDER BY ordinal_position
                    ''')
                    columns = cursor.fetchall()
                    print(f"Columns in pages: {[c[0] for c in columns]}")
                    
                    # Get page type distribution
                    cursor.execute('''
                        SELECT page_type, COUNT(*) as count 
                        FROM pages 
                        GROUP BY page_type 
                        ORDER BY count DESC
                    ''')
                    
                    results = cursor.fetchall()
                    print('\nPage Type Distribution:')
                    print('=' * 50)
                    for page_type, count in results:
                        print(f'{page_type}: {count}')
                    
                    return  # Success, exit
                    
            except Exception as e:
                print(f"Error querying pages: {e}")
            
            conn.close()
            
        except Exception as e:
            print(f"✗ Failed to connect: {e}")

if __name__ == "__main__":
    debug_database() 