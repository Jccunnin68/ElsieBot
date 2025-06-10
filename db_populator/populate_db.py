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
                    content TEXT NOT NULL,
                    raw_content TEXT NOT NULL,
                    url VARCHAR(500),
                    crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    page_type VARCHAR(50),
                    ship_name VARCHAR(100),
                    log_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create page_metadata table
            cur.execute("""
                CREATE TABLE page_metadata (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL UNIQUE,
                    url VARCHAR(500) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    crawl_count INTEGER DEFAULT 1,
                    status VARCHAR(20) DEFAULT 'active',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Create indexes
            cur.execute("CREATE INDEX idx_wiki_pages_title ON wiki_pages(title);")
            cur.execute("CREATE INDEX idx_wiki_pages_type ON wiki_pages(page_type);")
            cur.execute("CREATE INDEX idx_wiki_pages_ship ON wiki_pages(ship_name);")
            cur.execute("CREATE INDEX idx_page_metadata_title ON page_metadata(title);")
            cur.execute("CREATE INDEX idx_page_metadata_status ON page_metadata(status);")
            cur.execute("CREATE INDEX idx_page_metadata_last_crawled ON page_metadata(last_crawled);")
            
            # Create full-text search index
            cur.execute("CREATE INDEX idx_wiki_pages_content_search ON wiki_pages USING gin(to_tsvector('english', title || ' ' || content));")
            
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
        
        # Comprehensive sample data covering various categories
        sample_data = [
            # Ships
            (
                "USS Enterprise (NCC-1701)",
                "The USS Enterprise (NCC-1701) was a Constitution-class starship that served as the flagship of Starfleet in the 23rd century. Under the command of Captain James T. Kirk, the Enterprise completed a historic five-year mission of exploration from 2264 to 2269. The ship was equipped with advanced technology including warp drive, transporters, and phasers. The Enterprise crew made first contact with numerous alien species and helped establish peaceful relations throughout the galaxy.",
                "The USS Enterprise (NCC-1701) was a Constitution-class starship that served as the flagship of Starfleet in the 23rd century.",
                "https://memory-alpha.fandom.com/wiki/USS_Enterprise_(NCC-1701)",
                "ship_info",
                "enterprise"
            ),
            (
                "USS Enterprise (NCC-1701-D)",
                "The USS Enterprise (NCC-1701-D) was a Galaxy-class starship that served as the flagship of Starfleet in the 24th century. Under the command of Captain Jean-Luc Picard, the Enterprise-D explored the galaxy from 2364 to 2371. The ship was much larger than its predecessors and included facilities for families. The Enterprise-D was equipped with advanced holodeck technology, improved shields, and powerful phaser arrays.",
                "The USS Enterprise (NCC-1701-D) was a Galaxy-class starship that served as the flagship of Starfleet in the 24th century.",
                "https://memory-alpha.fandom.com/wiki/USS_Enterprise_(NCC-1701-D)",
                "ship_info",
                "enterprise"
            ),
            (
                "USS Voyager (NCC-74656)",
                "The USS Voyager was an Intrepid-class starship that became stranded in the Delta Quadrant in 2371. Under Captain Kathryn Janeway's command, Voyager spent seven years finding its way home through uncharted space. The ship featured bio-neural circuitry and variable geometry warp nacelles. Voyager made contact with many Delta Quadrant species including the Borg.",
                "The USS Voyager was an Intrepid-class starship that became stranded in the Delta Quadrant.",
                "https://memory-alpha.fandom.com/wiki/USS_Voyager_(NCC-74656)",
                "ship_info",
                "voyager"
            ),
            
            # Personnel
            (
                "James T. Kirk",
                "James Tiberius Kirk was a renowned Starfleet captain who commanded the USS Enterprise during its five-year mission from 2264 to 2269. Born in Iowa in 2233, Kirk was known for his leadership skills, tactical brilliance, and ability to inspire his crew. He was instrumental in numerous first contact situations and diplomatic missions. Kirk's command style emphasized human intuition and emotion alongside logical analysis.",
                "James Tiberius Kirk was a renowned Starfleet captain who commanded the USS Enterprise.",
                "https://memory-alpha.fandom.com/wiki/James_T._Kirk",
                "personnel",
                "enterprise"
            ),
            (
                "Spock",
                "Spock was a Vulcan-Human hybrid who served as first officer and science officer aboard the USS Enterprise under Captain Kirk. Born in 2230, Spock struggled with his dual heritage throughout his life. His logical Vulcan training often conflicted with his human emotions. Spock was known for his analytical mind, scientific expertise, and the Vulcan nerve pinch. He formed a deep friendship with both Kirk and Dr. McCoy.",
                "Spock was a Vulcan-Human hybrid who served as first officer and science officer aboard the USS Enterprise.",
                "https://memory-alpha.fandom.com/wiki/Spock",
                "personnel",
                "enterprise"
            ),
            (
                "Jean-Luc Picard",
                "Jean-Luc Picard was a celebrated Starfleet captain who commanded the USS Enterprise-D and later the USS Enterprise-E. Born in France in 2305, Picard was known for his diplomatic skills, archaeological interests, and strong moral compass. He successfully handled first contact with numerous species and navigated complex political situations. Picard's command philosophy emphasized negotiation and understanding over force.",
                "Jean-Luc Picard was a celebrated Starfleet captain who commanded the USS Enterprise-D.",
                "https://memory-alpha.fandom.com/wiki/Jean-Luc_Picard",
                "personnel",
                "enterprise"
            ),
            (
                "Kathryn Janeway",
                "Kathryn Janeway was the first female captain to command a starship in the Star Trek series. As captain of USS Voyager, she led her crew through seven years in the Delta Quadrant, making difficult decisions to get her people home. Janeway was known for her scientific background, strong leadership, and willingness to bend Starfleet protocols when necessary for the survival of her crew.",
                "Kathryn Janeway was the captain of USS Voyager, stranded in the Delta Quadrant.",
                "https://memory-alpha.fandom.com/wiki/Kathryn_Janeway",
                "personnel",
                "voyager"
            ),
            
            # Technology
            (
                "Warp Drive",
                "Warp drive is a faster-than-light propulsion system that works by distorting spacetime around a starship. The technology creates a subspace bubble around the vessel, allowing it to travel at multiples of the speed of light without violating relativistic physics. Warp factors are measured on a logarithmic scale, with Warp 1 being the speed of light and higher factors representing exponentially faster speeds.",
                "Warp drive is a faster-than-light propulsion system used by Starfleet vessels.",
                "https://memory-alpha.fandom.com/wiki/Warp_drive",
                "technology",
                None
            ),
            (
                "Transporter",
                "The transporter is a technology that converts matter into energy, transmits it to another location, and reconverts it back into matter. This allows for near-instantaneous transportation of people and objects across space. The process involves scanning the subject at the quantum level, storing the pattern in a buffer, and reassembling it at the destination. Transporter technology revolutionized space travel and exploration.",
                "The transporter converts matter into energy for instantaneous transportation.",
                "https://memory-alpha.fandom.com/wiki/Transporter",
                "technology",
                None
            ),
            
            # Organizations
            (
                "Starfleet",
                "Starfleet is the deep-space exploratory and peacekeeping armada of the United Federation of Planets. Founded in 2161, Starfleet's mission is to seek out new life and new civilizations, to boldly go where no one has gone before. The organization operates under principles of peaceful exploration, scientific discovery, and diplomatic contact. Starfleet Academy trains officers in San Francisco, Earth.",
                "Starfleet is the exploratory and peacekeeping armada of the United Federation of Planets.",
                "https://memory-alpha.fandom.com/wiki/Starfleet",
                "general",
                None
            ),
            (
                "United Federation of Planets",
                "The United Federation of Planets is an interstellar government composed of planetary governments and colonies. Founded in 2161 by Earth, Vulcan, Andoria, and Tellar, the Federation promotes peace, cooperation, and mutual understanding among its member worlds. The Federation operates on principles of equality, justice, and progress, with its capital located in Paris, Earth.",
                "The United Federation of Planets is an interstellar government promoting peace and cooperation.",
                "https://memory-alpha.fandom.com/wiki/United_Federation_of_Planets",
                "general",
                None
            ),
            
            # Mission Logs
            (
                "Captain's Log, Stardate 1513.1",
                "Captain's log, stardate 1513.1. The Enterprise is en route to the planet M-113 for a routine medical examination of archaeologist Robert Crater and his wife Nancy. Dr. McCoy has a personal history with Nancy Crater, having known her before she married Robert. This will be an opportunity for the doctor to reunite with an old friend while we conduct our standard crew medical examinations.",
                "Mission log entry for routine medical examination mission to M-113.",
                "https://memory-alpha.fandom.com/wiki/The_Man_Trap",
                "mission_log",
                "enterprise"
            )
        ]
        
        with conn.cursor() as cur:
            inserted_count = 0
            
            for title, content, raw_content, url, page_type, ship_name in sample_data:
                try:
                    # Generate content hash
                    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    
                    # Insert into wiki_pages
                    cur.execute("""
                        INSERT INTO wiki_pages (title, content, raw_content, url, page_type, ship_name)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (title, content, raw_content, url, page_type, ship_name))
                    
                    # Insert into page_metadata
                    cur.execute("""
                        INSERT INTO page_metadata (url, title, content_hash, status)
                        VALUES (%s, %s, %s, 'active')
                    """, (url, title, content_hash))
                    
                    inserted_count += 1
                    print(f"   ✅ Inserted: {title} ({page_type})")
                    
                except Exception as e:
                    print(f"   ❌ Error inserting {title}: {e}")
                    continue
            
            # Get statistics
            cur.execute("SELECT COUNT(*) FROM wiki_pages;")
            total_count = cur.fetchone()[0]
            
            cur.execute("SELECT page_type, COUNT(*) FROM wiki_pages GROUP BY page_type ORDER BY page_type;")
            type_counts = cur.fetchall()
            
            conn.commit()
            
        conn.close()
        
        print(f"\n🎉 Sample data populated successfully!")
        print(f"   📊 Total pages: {total_count}")
        print(f"   📝 Pages inserted this run: {inserted_count}")
        
        for page_type, count in type_counts:
            print(f"   📄 {page_type}: {count}")
            
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