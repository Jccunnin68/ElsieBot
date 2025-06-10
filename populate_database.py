#!/usr/bin/env python3
"""
Standalone script to run database population
"""

import subprocess
import sys
import time

def run_populator():
    """Run the database populator service"""
    print("🚀 Starting Database Population Process")
    print("========================================")
    
    try:
        # First, make sure the database is running
        print("1️⃣ Starting database service...")
        subprocess.run([
            "docker-compose", "up", "-d", "elsiebrain_db"
        ], check=True, cwd=".")
        
        # Wait a moment for database to be ready
        print("⏳ Waiting for database to initialize...")
        time.sleep(10)
        
        # Build and run the populator
        print("2️⃣ Building and running database populator...")
        result = subprocess.run([
            "docker-compose", "up", "--build", "db_populator"
        ], cwd=".")
        
        if result.returncode == 0:
            print("\n✅ Database population completed successfully!")
            
            # Show the populated data
            print("3️⃣ Verifying database content...")
            subprocess.run([
                "docker-compose", "exec", "elsiebrain_db", 
                "psql", "-U", "elsie", "-d", "elsiebrain", 
                "-c", "SELECT page_type, COUNT(*) FROM wiki_pages GROUP BY page_type ORDER BY page_type;"
            ], cwd=".")
            
        else:
            print("❌ Database population failed!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running commands: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("🧠 Elsiebrain Database Population Tool")
    print("======================================")
    
    if run_populator():
        print("\n🎉 Database is ready for use!")
        print("   You can now start the AI agent and Discord bot.")
    else:
        print("\n❌ Population failed. Please check the logs.")
        sys.exit(1)

if __name__ == "__main__":
    main() 