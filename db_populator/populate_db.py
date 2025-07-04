#!/usr/bin/env python3
"""
Database populator service for elsiebrain
Runs inside Docker cluster to populate the database with Star Trek wiki content
"""

import os
import psycopg2
import time
import sys
from datetime import datetime
import hashlib

def wait_for_db():
    """Wait for database to be ready"""
    print("🔄 Waiting for database to be ready...")
    
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                host="elsiebrain_db",  # Service name in Docker network
                port="5432",
                dbname="elsiebrain",
                user="elsie",
                password="elsie123"
            )
            conn.close()
            print("✅ Database is ready!")
            return True
        except Exception as e:
            retry_count += 1
            print(f"   ⏳ Attempt {retry_count}/{max_retries} - Database not ready: {e}")
            time.sleep(2)
    
    print("❌ Database failed to become ready")
    return False

def create_schema():
    """Create database schema"""
    print("🏗️ Creating database schema...")
    
    try:
        conn = psycopg2.connect(
            host="elsiebrain_db",
            port="5432",
            dbname="elsiebrain",
            user="elsie",
            password="elsie123"
        )
        
        with conn.cursor() as cur:
            # Drop existing tables for clean setup
            cur.execute("DROP TABLE IF EXISTS page_metadata CASCADE;")
            cur.execute("DROP TABLE IF EXISTS wiki_pages CASCADE;")
            
            # Create wiki_pages table
            cur.execute("""
                CREATE TABLE wiki_pages (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    raw_content TEXT NOT NULL,
                    url VARCHAR(500),
                    crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    touched TIMESTAMP,
                    categories TEXT[] NOT NULL,
                    content_accessed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create page_metadata table
            cur.execute("""
                CREATE TABLE page_metadata (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL UNIQUE,
                    url VARCHAR(500) NOT NULL UNIQUE,
                    content_hash VARCHAR(64) NOT NULL,
                    last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    crawl_count INTEGER DEFAULT 1,
                    status VARCHAR(20) DEFAULT 'active',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes for clean schema
            cur.execute("CREATE INDEX idx_wiki_pages_title ON wiki_pages(title);")
            cur.execute("CREATE INDEX idx_wiki_pages_touched ON wiki_pages(touched);")
            cur.execute("CREATE INDEX idx_wiki_pages_categories ON wiki_pages USING GIN (categories);")
            cur.execute("CREATE INDEX idx_page_metadata_title ON page_metadata(title);")
            cur.execute("CREATE INDEX idx_page_metadata_status ON page_metadata(status);")
            cur.execute("CREATE INDEX idx_page_metadata_last_crawled ON page_metadata(last_crawled);")
            
            # Create full-text search index
            cur.execute("CREATE INDEX idx_wiki_pages_content_search ON wiki_pages USING GIN (to_tsvector('english', title || ' ' || raw_content));");
            
            conn.commit()
            print("✅ Database schema created successfully")
            
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
    
    return True

def populate_sample_data():
    """Populate with comprehensive Star Trek sample data"""
    print("🚀 Populating sample Star Trek data...")
    
    try:
        conn = psycopg2.connect(
            host="elsiebrain_db",
            port="5432",
            dbname="elsiebrain",
            user="elsie",
            password="elsie123"
        )
        
        # Comprehensive sample data with categories instead of legacy fields
        sample_data = [
            # Ships - use Ship Information category
            (
                "USS Enterprise (NCC-1701)",
                "The USS Enterprise (NCC-1701) was a Constitution-class starship that served as the flagship of Starfleet in the 23rd century.",
                "https://memory-alpha.fandom.com/wiki/USS_Enterprise_(NCC-1701)",
                ["Ship Information"]
            ),
            (
                "USS Enterprise (NCC-1701-D)",
                "The USS Enterprise (NCC-1701-D) was a Galaxy-class starship that served as the flagship of Starfleet in the 24th century.",
                "https://memory-alpha.fandom.com/wiki/USS_Enterprise_(NCC-1701-D)",
                ["Ship Information"]
            ),
            (
                "USS Voyager (NCC-74656)",
                "The USS Voyager was an Intrepid-class starship that became stranded in the Delta Quadrant.",
                "https://memory-alpha.fandom.com/wiki/USS_Voyager_(NCC-74656)",
                ["Ship Information"]
            ),
            
            # Personnel - use Characters category
            (
                "James T. Kirk",
                "James Tiberius Kirk was a renowned Starfleet captain who commanded the USS Enterprise.",
                "https://memory-alpha.fandom.com/wiki/James_T._Kirk",
                ["Characters"]
            ),
            (
                "Spock",
                "Spock was a Vulcan-Human hybrid who served as first officer and science officer aboard the USS Enterprise.",
                "https://memory-alpha.fandom.com/wiki/Spock",
                ["Characters"]
            ),
            (
                "Jean-Luc Picard",
                "Jean-Luc Picard was a celebrated Starfleet captain who commanded the USS Enterprise-D.",
                "https://memory-alpha.fandom.com/wiki/Jean-Luc_Picard",
                ["Characters"]
            ),
            (
                "Kathryn Janeway",
                "Kathryn Janeway was the captain of USS Voyager, stranded in the Delta Quadrant.",
                "https://memory-alpha.fandom.com/wiki/Kathryn_Janeway",
                ["Characters"]
            ),
            
            # Technology - use Technology category
            (
                "Warp Drive",
                "Warp drive is a faster-than-light propulsion system used by Starfleet vessels.",
                "https://memory-alpha.fandom.com/wiki/Warp_drive",
                ["Technology"]
            ),
            (
                "Transporter",
                "The transporter converts matter into energy for instantaneous transportation.",
                "https://memory-alpha.fandom.com/wiki/Transporter",
                ["Technology"]
            ),
            
            # Organizations - use General Information category
            (
                "Starfleet",
                "Starfleet is the exploratory and peacekeeping armada of the United Federation of Planets.",
                "https://memory-alpha.fandom.com/wiki/Starfleet",
                ["General Information"]
            ),
            (
                "United Federation of Planets",
                "The United Federation of Planets is an interstellar government promoting peace and cooperation.",
                "https://memory-alpha.fandom.com/wiki/United_Federation_of_Planets",
                ["General Information"]
            ),
            
            # Mission Logs - use ship-specific log categories
            (
                "Captain's Log, Stardate 1513.1",
                "Mission log entry for routine medical examination mission to M-113.",
                "https://memory-alpha.fandom.com/wiki/The_Man_Trap",
                ["Enterprise Log"]
            )
        ]
        
        with conn.cursor() as cur:
            inserted_count = 0
            
            for title, raw_content, url, categories in sample_data:
                try:
                    # Generate content hash
                    content_hash = hashlib.sha256(raw_content.encode('utf-8')).hexdigest()
                    
                    # Insert into wiki_pages with categories only
                    cur.execute("""
                        INSERT INTO wiki_pages (title, raw_content, url, categories)
                        VALUES (%s, %s, %s, %s)
                    """, (title, raw_content, url, categories))
                    
                    # Insert into page_metadata
                    cur.execute("""
                        INSERT INTO page_metadata (url, title, content_hash, status)
                        VALUES (%s, %s, %s, 'active')
                    """, (url, title, content_hash))
                    
                    inserted_count += 1
                    print(f"   ✅ Inserted: {title} (categories: {categories})")
                    
                except Exception as e:
                    print(f"   ❌ Error inserting {title}: {e}")
                    continue
            
            # Get statistics with categories
            cur.execute("SELECT COUNT(*) FROM wiki_pages;")
            total_count = cur.fetchone()[0]
            
            cur.execute("""
                SELECT unnest(categories) as category, COUNT(*) as count 
                FROM wiki_pages 
                GROUP BY unnest(categories) 
                ORDER BY count DESC;
            """)
            category_counts = cur.fetchall()
            
            conn.commit()
            
        conn.close()
        
        print(f"\n🎉 Sample data populated successfully!")
        print(f"   📊 Total pages: {total_count}")
        print(f"   📝 Pages inserted this run: {inserted_count}")
        
        print(f"\n📋 Category Distribution:")
        for category, count in category_counts:
            print(f"   📄 {category}: {count}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error populating data: {e}")
        return False

def main():
    """Main populator function"""
    print("🧠 Elsiebrain Database Populator")
    print("=================================")
    print(f"⏰ Started at: {datetime.now()}")
    
    # Wait for database
    if not wait_for_db():
        sys.exit(1)
    
    # Create schema
    if not create_schema():
        print("❌ Failed to create schema")
        sys.exit(1)
    
    # Populate data
    if not populate_sample_data():
        print("❌ Failed to populate data")
        sys.exit(1)
    
    print(f"\n✅ Database population completed successfully!")
    print(f"⏰ Finished at: {datetime.now()}")
    print("🎯 Database is ready for use!")

if __name__ == "__main__":
    main() 