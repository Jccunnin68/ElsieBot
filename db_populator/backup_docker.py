#!/usr/bin/env python3
"""
Docker-based Database Backup Script for Elsie
Uses Docker containers to backup and restore the elsiebrain database.
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path


def run_docker_command(cmd, capture_output=True):
    """Run a docker command and return the result"""
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, shell=True)
        return result
    except Exception as e:
        print(f"❌ Error running Docker command: {e}")
        return None


def create_backup(backup_dir='backups', is_seed=False):
    """Create a database backup using Docker"""
    print("🐳 Creating database backup using Docker...")
    
    # Create backup directory if it doesn't exist
    backup_path = Path(__file__).parent / backup_dir
    backup_path.mkdir(exist_ok=True)
    
    # Set filename based on whether this is a seed backup or not
    if is_seed:
        filename = 'seed_backup.sql'
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.sql'
    
    backup_file = backup_path / filename
    
    try:
        # Use docker exec to run pg_dump inside the database container
        # This assumes the database container is named 'elsiebrain_postgres'
        cmd = f'''docker exec elsiebrain_postgres pg_dump -U elsie -d elsiebrain > "{backup_file}"'''
        
        print(f"📦 Running backup command...")
        result = run_docker_command(cmd, capture_output=False)
        
        if result and result.returncode == 0:
            if backup_file.exists() and backup_file.stat().st_size > 0:
                print(f"✅ Database backup created successfully: {backup_file}")
                print(f"📏 Backup size: {backup_file.stat().st_size:,} bytes")
                return str(backup_file)
            else:
                print(f"❌ Backup file was created but appears to be empty")
                return None
        else:
            print(f"❌ Error creating backup")
            if result:
                print(f"   Error output: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error during backup: {e}")
        return None


def restore_backup(backup_file=None):
    """Restore database from backup using Docker"""
    print("🐳 Restoring database backup using Docker...")
    
    # If no backup file specified, use seed backup
    if not backup_file:
        backup_file = Path(__file__).parent / 'backups' / 'seed_backup.sql'
    else:
        backup_file = Path(backup_file)
    
    if not backup_file.exists():
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    try:
        print(f"📦 Restoring from: {backup_file}")
        
        # Copy backup file into container and restore
        container_backup_path = "/tmp/restore_backup.sql"
        
        # Copy file to container
        copy_cmd = f'docker cp "{backup_file}" elsiebrain_postgres:{container_backup_path}'
        print("📋 Copying backup file to container...")
        result = run_docker_command(copy_cmd)
        
        if result.returncode != 0:
            print(f"❌ Error copying backup file to container: {result.stderr}")
            return False
        
        # Restore database
        restore_cmd = f'docker exec elsiebrain_postgres psql -U elsie -d elsiebrain -f {container_backup_path}'
        print("🔄 Restoring database...")
        result = run_docker_command(restore_cmd, capture_output=False)
        
        if result and result.returncode == 0:
            print(f"✅ Database restored successfully from: {backup_file}")
            
            # Clean up temporary file
            cleanup_cmd = f'docker exec elsiebrain_postgres rm {container_backup_path}'
            run_docker_command(cleanup_cmd)
            
            return True
        else:
            print(f"❌ Error restoring database")
            if result:
                print(f"   Error output: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error during restore: {e}")
        return False


def list_containers():
    """List Docker containers to help with troubleshooting"""
    print("🐳 Docker containers:")
    result = run_docker_command("docker ps -a", capture_output=False)
    return result


def test_connection():
    """Test database connection using Docker"""
    print("🐳 Testing database connection...")
    
    cmd = 'docker exec elsiebrain_postgres psql -U elsie -d elsiebrain -c "SELECT version();"'
    result = run_docker_command(cmd)
    
    if result and result.returncode == 0:
        print("✅ Database connection successful")
        print("📊 Database info:")
        print(result.stdout)
        return True
    else:
        print("❌ Database connection failed")
        if result:
            print(f"   Error: {result.stderr}")
        print("\n💡 Troubleshooting:")
        print("   - Check if Docker containers are running: docker ps")
        print("   - Check if database container is named 'elsiebrain_postgres'")
        print("   - Try: docker exec elsiebrain_postgres pg_isready -U elsie")
        return False


def show_stats():
    """Show database statistics using Docker"""
    print("🐳 Database statistics:")
    
    cmd = '''docker exec elsiebrain_postgres psql -U elsie -d elsiebrain -c "
        SELECT 
            COUNT(*) as total_pages,
            COUNT(CASE WHEN page_type = 'mission_log' THEN 1 END) as mission_logs,
            COUNT(CASE WHEN page_type = 'ship_info' THEN 1 END) as ship_info,
            COUNT(CASE WHEN page_type = 'personnel' THEN 1 END) as personnel
        FROM wiki_pages;"'''
    
    result = run_docker_command(cmd, capture_output=False)
    return result


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🐳 Elsie Docker Database Backup Tool")
        print("=" * 60)
        print("Usage:")
        print("  python backup_docker.py backup              # Create a timestamped backup")
        print("  python backup_docker.py seed                # Create/update seed backup")
        print("  python backup_docker.py restore [file]      # Restore from backup")
        print("  python backup_docker.py test                # Test database connection")
        print("  python backup_docker.py stats               # Show database statistics")
        print("  python backup_docker.py containers          # List Docker containers")
        print("\nRequirements:")
        print("  - Docker must be running")
        print("  - Database container must be named 'elsiebrain_postgres'")
        print("  - Container must be accessible via docker exec")
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
    elif command == "test":
        test_connection()
    elif command == "stats":
        show_stats()
    elif command == "containers":
        list_containers()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use no arguments to see available commands")


if __name__ == "__main__":
    main() 