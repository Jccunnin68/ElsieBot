# Elsie Brain Database Setup

This document describes the new architecture where Elsie uses a dedicated PostgreSQL database called "elsiebrain" that is populated separately and then used by the AI agent.

## Architecture Overview

- **elsiebrain database**: PostgreSQL database containing all fleet wiki content
- **setup_elsiebrain_db.py**: External script to create schema and populate data from flat files
- **wiki_crawler_db.py**: New database-enabled web crawler with differential updates
- **AI Agent**: Read-only access to the populated database
- **Docker Compose**: Orchestrates PostgreSQL service with the application

## Setup Process

### 1. Start the Database Service

```bash
# Start only the database service
docker-compose up elsiebrain_db -d

# Wait for database to be ready
docker-compose logs -f elsiebrain_db
```

### 2. Populate the Database

**Option A: From Flat File (Legacy)**
```bash
# Make sure you have the flat file available
python setup_elsiebrain_db.py fleet_wiki_content.txt

# Or clear existing data first
python setup_elsiebrain_db.py fleet_wiki_content.txt --clear
```

**Option B: Direct Web Crawling (Recommended)**
```bash
# Standard crawl (~15 curated pages, fast)
python wiki_crawler_db.py

# Comprehensive crawl (all pages, slow)
python wiki_crawler_db.py --comprehensive

# Force update all pages (ignore change detection)
python wiki_crawler_db.py --force

# Show database statistics
python wiki_crawler_db.py --stats
```

### 3. Deploy the Application

```bash
# Build and start all services
docker-compose up --build
```

## Database Configuration

The database connection uses these environment variables (with defaults):

- `DB_HOST`: Database host (default: localhost, docker: elsiebrain_db)
- `DB_NAME`: Database name (default: elsiebrain)
- `DB_USER`: Database user (default: elsie)
- `DB_PASSWORD`: Database password (default: elsie123)
- `DB_PORT`: Database port (default: 5432)

## Database Schema

### `wiki_pages` table contains:

- `id`: Primary key
- `title`: Page title
- `content`: Processed page content
- `raw_content`: Original raw content
- `url`: Source URL
- `crawl_date`: When the page was crawled
- `page_type`: Classified type (mission_log, ship_info, personnel, location, general)
- `ship_name`: Associated ship name (if applicable)
- `log_date`: Mission log date (if applicable)
- `created_at`, `updated_at`: Timestamps

### `page_metadata` table (NEW) contains:

- `id`: Primary key
- `page_title`: Page title (unique)
- `url`: Source URL
- `last_crawled`: When the page was last crawled
- `last_modified`: When the page was last modified (if available)
- `content_hash`: SHA-256 hash of content for change detection
- `crawl_count`: Number of times page has been crawled
- `status`: Page status (active, error)
- `error_message`: Error details if crawl failed
- `created_at`, `updated_at`: Timestamps

## Full-Text Search Indexes

The database includes PostgreSQL full-text search indexes on:
- Title content
- Page content
- Combined title + content

Plus regular indexes on:
- page_type
- ship_name  
- log_date
- page_metadata.page_title
- page_metadata.last_crawled
- page_metadata.status

## Web Crawler Features

### Differential Updates
The new `wiki_crawler_db.py` supports:
- **Content Hash Tracking**: Only updates pages when content actually changes
- **Metadata Logging**: Tracks crawl history and error states
- **Selective Updates**: Skip unchanged pages to improve performance
- **Error Handling**: Records and handles crawl failures gracefully

### Crawler Usage Examples

```bash
# Quick update (only changed pages)
python wiki_crawler_db.py

# Force full refresh
python wiki_crawler_db.py --force

# Crawl all 1400+ pages (slow)
python wiki_crawler_db.py --comprehensive

# Check what's in the database
python wiki_crawler_db.py --stats
```

### Output Example
```
[1/15] Processing: USS Stardancer
Crawling: USS Stardancer
  ✓ Successfully extracted 2847 characters
  ✓ Updated existing page: USS Stardancer

[2/15] Processing: 22nd Mobile Daedalus Wiki  
Crawling: 22nd Mobile Daedalus Wiki
  ⏭️  Skipping - no changes detected

Crawling complete!
✓ Successfully crawled: 14 pages
✓ Updated: 1 pages
⏭️  Skipped (unchanged): 13 pages
```

## Benefits of This Architecture

1. **Separation of Concerns**: Data import is separate from the AI agent
2. **Performance**: PostgreSQL with full-text search is much faster than flat file parsing
3. **Differential Updates**: Only crawl changed content, saving time and bandwidth
4. **Metadata Tracking**: Track crawl history and detect errors
5. **Scalability**: Database can be populated/updated independently
6. **Containerization**: Database state persists in Docker volumes
7. **Development**: Easier to test and debug with structured data

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps elsiebrain_db

# View database logs
docker-compose logs elsiebrain_db

# Connect manually to test
docker-compose exec elsiebrain_db psql -U elsie -d elsiebrain
```

### Crawler Issues
```bash
# Check if you have required packages
pip install fandom-py psycopg2-binary requests beautifulsoup4

# Test database connection
python -c "from wiki_crawler_db import WikiCrawlerDB; WikiCrawlerDB()"

# Show detailed stats
python wiki_crawler_db.py --stats
```

### Data Import Issues
```bash
# Check if flat file exists (legacy method)
ls -la fleet_wiki_content.txt

# Run setup with verbose output
python setup_elsiebrain_db.py fleet_wiki_content.txt --clear
```

### AI Agent Issues
```bash
# Check AI agent logs
docker-compose logs ai_agent

# Test database connection from agent
docker-compose exec ai_agent python -c "from database_controller import get_db_controller; print(get_db_controller().get_stats())"
```

## Migration Path

1. **From Flat Files**: Use `setup_elsiebrain_db.py` to import existing data
2. **To Live Crawling**: Use `wiki_crawler_db.py` for fresh, up-to-date content
3. **Hybrid Approach**: Import flat files, then use crawler for updates 