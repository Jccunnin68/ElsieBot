# Elsie Development Environment Setup

## Overview

The development environment has been split into two separate Docker Compose files to prevent database data loss during application rebuilds:

- `docker-compose.db.yml` - Database only (persistent)
- `docker-compose.yml` - Application services (ai_agent, discord_bot, etc.)

## Quick Start

### Option 1: Use the startup scripts

**Windows (PowerShell):**
```powershell
.\start-dev.ps1
```

**Linux/Mac (Bash):**
```bash
./start-dev.sh
```

### Option 2: Manual startup

1. **Start the database:**
   ```bash
   docker-compose -f docker-compose.db.yml up -d
   ```

2. **Wait for database to be healthy, then start applications:**
   ```bash
   docker-compose up -d
   ```

Note: Docker Compose automatically creates the shared network when needed.

## Management Commands

### Database Management
- **Start database only:** `docker-compose -f docker-compose.db.yml up -d`
- **Stop database only:** `docker-compose -f docker-compose.db.yml down`
- **View database logs:** `docker-compose -f docker-compose.db.yml logs -f`

### Application Management
- **Start applications:** `docker-compose up -d`
- **Stop applications:** `docker-compose down`
- **Rebuild applications:** `docker-compose down && docker-compose up --build -d`
- **View application logs:** `docker-compose logs -f [service_name]`

### Full Environment
- **Stop everything:** `docker-compose down && docker-compose -f docker-compose.db.yml down`
- **Restart everything:** Follow the Quick Start steps

## Benefits of This Setup

1. **Database Persistence:** The database remains running and retains data even when rebuilding application containers
2. **Faster Development:** Only rebuild the services you're working on
3. **Data Safety:** No risk of accidentally losing database data during development
4. **Resource Efficiency:** Database doesn't need to restart every time you change application code

## Services and Ports

- **PostgreSQL Database:** `localhost:5433`
- **AI Agent:** `localhost:8000`
- **Discord Bot:** Internal only (connects to AI Agent)

## Troubleshooting

### Network Issues
If services can't communicate:
```bash
docker network inspect elsie_dev_network
```

### Database Connection Issues
Check if database is healthy:
```bash
docker-compose -f docker-compose.db.yml ps
```

### Volume Issues
If you need to reset the database:
```bash
docker-compose -f docker-compose.db.yml down -v
docker volume rm elsiebrain_dev_data
```

## Development Workflow

1. **Daily startup:** Run the startup script or manual commands
2. **Code changes:** Just restart the affected service: `docker-compose restart ai_agent`
3. **Major changes:** Rebuild applications: `docker-compose down && docker-compose up --build -d`
4. **Database changes:** Use the db_populator or restore from backup
5. **End of day:** Optionally stop applications but leave database running

The database will persist between sessions, making development much more efficient! 