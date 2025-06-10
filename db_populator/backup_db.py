#!/usr/bin/env python3
"""
PostgreSQL Database Backup and Restore Script for Elsie
This script handles backing up and restoring the elsiebrain database.
"""

import os
import sys
import subprocess
from datetime import datetime
from os.path import join, dirname
from dotenv import load_dotenv

# Load environment variables
dotenv_path = join(dirname(__file__), '../../.env')
load_dotenv(dotenv_path)

def get_db_config():
    """Get database configuration from environment variables"""
    return {
        'dbname': os.getenv('DB_NAME', 'elsiebrain'),
        'user': os.getenv('DB_USER', 'elsie'),
        'password': os.getenv('DB_PASSWORD', 'elsie123'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432')
    }

def create_backup(backup_dir='backups', is_seed=False):
    """Create a database backup"""
    db_config = get_db_config()
    
    # Create backup directory if it doesn't exist
    backup_dir = join(dirname(__file__), backup_dir)
    os.makedirs(backup_dir, exist_ok=True)
    
    # Set filename based on whether this is a seed backup or not
    if is_seed:
        filename = 'seed_backup.sql'
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.sql'
    
    backup_path = join(backup_dir, filename)
    
    # Set environment variables for pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    try:
        # Create backup using pg_dump
        cmd = [
            'pg_dump',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-d', db_config['dbname'],
            '-F', 'p',  # plain text format
            '-f', backup_path
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Database backup created successfully: {backup_path}")
            return backup_path
        else:
            print(f"❌ Error creating backup: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error during backup: {e}")
        return None

def restore_backup(backup_file=None):
    """Restore database from backup"""
    db_config = get_db_config()
    
    # If no backup file specified, use seed backup
    if not backup_file:
        backup_file = join(dirname(__file__), 'backups', 'seed_backup.sql')
    
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    # Set environment variables for psql
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    try:
        # First, terminate existing connections
        terminate_cmd = [
            'psql',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-d', 'postgres',
            '-c', f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{db_config['dbname']}' AND pid <> pg_backend_pid();"
        ]
        
        subprocess.run(terminate_cmd, env=env, capture_output=True)
        
        # Drop and recreate database
        drop_cmd = [
            'psql',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-d', 'postgres',
            '-c', f"DROP DATABASE IF EXISTS {db_config['dbname']};"
        ]
        
        create_cmd = [
            'psql',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-d', 'postgres',
            '-c', f"CREATE DATABASE {db_config['dbname']};"
        ]
        
        subprocess.run(drop_cmd, env=env, capture_output=True)
        subprocess.run(create_cmd, env=env, capture_output=True)
        
        # Restore from backup
        restore_cmd = [
            'psql',
            '-h', db_config['host'],
            '-p', db_config['port'],
            '-U', db_config['user'],
            '-d', db_config['dbname'],
            '-f', backup_file
        ]
        
        result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Database restored successfully from: {backup_file}")
            return True
        else:
            print(f"❌ Error restoring database: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error during restore: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        print("Elsie Database Backup and Restore Tool")
        print("=" * 60)
        print("Usage:")
        print("  python backup_db.py backup              # Create a timestamped backup")
        print("  python backup_db.py seed               # Create/update seed backup")
        print("  python backup_db.py restore [file]     # Restore from backup (uses seed if no file)")
        print("\nEnvironment Variables (from .env):")
        print("  DB_NAME     - Database name")
        print("  DB_USER     - Database user")
        print("  DB_PASSWORD - Database password")
        print("  DB_HOST     - Database host")
        print("  DB_PORT     - Database port")
        print("=" * 60)
        return

    command = sys.argv[1].lower()
    
    if command == "backup":
        create_backup()
    elif command == "seed":
        create_backup(is_seed=True)
    elif command == "restore":
        backup_file = sys.argv[2] if len(sys.argv) > 2 else None
        restore_backup(backup_file)
    else:
        print(f"❌ Unknown command: {command}")
        print("Use --help to see available commands")

if __name__ == "__main__":
    main() 