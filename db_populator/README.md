# Elsie Database Backup System

This directory contains tools for managing the Elsie database, including backup and restore functionality.

## Quick Start

1. Create initial seed after database population:
```bash
python backup_db.py seed
```

2. Restore from seed backup:
```bash
python backup_db.py restore
```

## Features

- **Seed Backup**: Creates/updates the base database state (`seed_backup.sql`)
- **Timestamped Backups**: Creates point-in-time backups with timestamps
- **Flexible Restore**: Can restore from seed or any backup file
- **Environment Based**: Uses `.env` file for configuration

## Usage

### Creating Backups

1. Create a timestamped backup:
```bash
python backup_db.py backup
```

2. Create/update seed backup:
```bash
python backup_db.py seed
```

### Restoring Backups

1. Restore from seed backup:
```bash
python backup_db.py restore
```

2. Restore from specific backup:
```bash
python backup_db.py restore path/to/backup.sql
```

## Backup Files

- `backups/seed_backup.sql`: Base database state (tracked in git)
- `backups/backup_YYYYMMDD_HHMMSS.sql`: Timestamped backups (not tracked in git)

## Environment Variables

Required variables in `.env`:
- `DB_NAME`: Database name (default: elsiebrain)
- `DB_USER`: Database user (default: elsie)
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)

## Notes

- The seed backup is tracked in git for easy deployment
- Timestamped backups are ignored by git
- Always create a new seed backup after significant database changes
- Use timestamped backups for regular backups during development 