#!/usr/bin/env python3

import psycopg2

def check_page_types():
    # Connect to database
    conn = psycopg2.connect(
        host='localhost',
        database='elsiebrain',
        user='elsiebrain',
        password='elsiebrain',
        port=5432
    )
    
    cursor = conn.cursor()
    
    # Get page type distribution
    cursor.execute('''
        SELECT page_type, COUNT(*) as count 
        FROM pages 
        GROUP BY page_type 
        ORDER BY count DESC
    ''')
    
    results = cursor.fetchall()
    
    print('Page Type Distribution:')
    print('=' * 50)
    for page_type, count in results:
        print(f'{page_type}: {count}')
    
    print(f'\nTotal pages: {sum(count for _, count in results)}')
    
    # Also check for any NULL or empty page types
    cursor.execute('''
        SELECT COUNT(*) as null_count 
        FROM pages 
        WHERE page_type IS NULL OR page_type = ''
    ''')
    
    null_count = cursor.fetchone()[0]
    if null_count > 0:
        print(f'Pages with NULL/empty page_type: {null_count}')
    
    # Let's also check some sample mission log titles to see what's happening
    print('\nSample Mission Log titles:')
    print('-' * 30)
    cursor.execute('''
        SELECT title 
        FROM pages 
        WHERE page_type = 'mission_log' 
        ORDER BY title 
        LIMIT 10
    ''')
    
    mission_logs = cursor.fetchall()
    for (title,) in mission_logs:
        print(f'- {title}')
    
    # Check if there are mission logs that might be misclassified
    print('\nPages with "Mission" in title but not classified as mission_log:')
    print('-' * 60)
    cursor.execute('''
        SELECT title, page_type 
        FROM pages 
        WHERE LOWER(title) LIKE '%mission%' 
        AND page_type != 'mission_log'
        ORDER BY title 
        LIMIT 10
    ''')
    
    other_missions = cursor.fetchall()
    for title, page_type in other_missions:
        print(f'- {title} ({page_type})')
    
    conn.close()

if __name__ == "__main__":
    check_page_types() 