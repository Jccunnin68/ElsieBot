# Content Access Tracking Implementation

## Overview
Added content access tracking functionality to the Elsie AI Agent database system. This feature tracks when database content is accessed through search queries, which can be used for response weighting and analytics.

## Database Schema Changes

### Added Column
- `content_accessed INTEGER DEFAULT 0` - Tracks number of times each page has been accessed

### Removed Column  
- `content` - Deprecated column removed, now using only `raw_content`

### Updated Indexes
- Full-text search index now uses `title || ' ' || raw_content` instead of including the old content column

## Code Changes

### 1. Database Controller (`database_controller.py`)

#### New Methods:
- `update_content_accessed(page_ids: List[int])` - Updates content_accessed counter for given page IDs
- `get_content_access_stats()` - Returns statistics on most accessed content

#### Modified Methods:
- `search_pages()` - Now automatically tracks access for all returned results
- `get_recent_logs()` - Now automatically tracks access for returned logs
- `get_stats()` - Enhanced to include content access statistics

#### Automatic Tracking:
- All search results returned by `search_pages()` automatically increment their `content_accessed` counter
- All recent logs returned by `get_recent_logs()` automatically increment their counter
- Updates happen transparently without affecting existing functionality

### 2. Query Tool (`run_query.py`)

#### New Features:
- Added `access` predefined query to show content access statistics
- Updated help text and examples to include content access queries
- Updated all example queries to use `raw_content` instead of `content`

#### New Query:
```sql
SELECT title, page_type, content_accessed 
FROM wiki_pages 
WHERE content_accessed > 0 
ORDER BY content_accessed DESC LIMIT 10;
```

### 3. Database Schema (`populate_db.py`)

#### Updated Schema:
- Removed `content TEXT NOT NULL` column
- Kept `raw_content TEXT NOT NULL` as the single content column
- Added `content_accessed INTEGER DEFAULT 0` column
- Updated full-text search index to use only `raw_content`

#### Sample Data:
- Fixed sample data insertion to use only `raw_content`
- Updated data tuples to match new schema

### 4. Schema Migration Tool (`run_schema_update.py`)

#### New Tool:
- Automatically detects current schema state
- Adds `content_accessed` column if missing
- Removes deprecated `content` column if present
- Updates full-text search indexes
- Shows final schema state

## Usage Examples

### Running Content Access Queries
```bash
# Show most accessed content
python run_query.py access

# Show access stats with full content
python run_query.py full access

# Custom access query
python run_query.py custom "SELECT title, content_accessed FROM wiki_pages WHERE content_accessed > 5"
```

### Schema Migration
```bash
# Update existing database schema
python run_schema_update.py
```

### Programmatic Access
```python
from ai_agent.handlers.ai_knowledge.database_controller import get_db_controller

controller = get_db_controller()

# Get access statistics
stats = controller.get_content_access_stats()

# Manual content access tracking (usually automatic)
page_ids = [1, 2, 3]
controller.update_content_accessed(page_ids)

# View enhanced stats including access counts
overall_stats = controller.get_stats()
print(f"Total accesses: {overall_stats['total_accesses']}")
print(f"Average accesses per page: {overall_stats['avg_accesses_per_page']}")
```

## How It Works

1. **Search Execution**: When any search method is called (`search_pages`, `get_recent_logs`, etc.)
2. **Result Processing**: Results are processed and returned to the caller as normal
3. **Access Tracking**: After results are prepared, page IDs are extracted and passed to `update_content_accessed()`
4. **Database Update**: The `content_accessed` counter is incremented for each returned page
5. **Timestamp Update**: The `updated_at` timestamp is also updated for tracking purposes

## Benefits

### For Response Weighting:
- Popular content can be prioritized in future searches
- Trending topics can be identified
- User interest patterns can be analyzed

### For Analytics:
- Track which content is most valuable
- Identify gaps in content usage
- Monitor search effectiveness
- Performance optimization opportunities

### For Content Management:
- Find unused content
- Identify high-value content for protection
- Guide content creation priorities

## Future Enhancements

Potential improvements for response weighting:
- Decay functions (older accesses count less)
- User-specific access patterns
- Context-aware weighting (ship-specific, mission-type, etc.)
- Time-based trending analysis
- Search quality scoring based on access patterns

## Files Modified

1. `ai_agent/database_controller.py` - Core tracking functionality
2. `ai_agent/run_query.py` - Query tool updates
3. `db_populator/populate_db.py` - Schema and sample data
4. `ai_agent/run_schema_update.py` - New migration tool
5. `CONTENT_ACCESS_TRACKING.md` - This documentation

## Backward Compatibility

- All existing search functionality remains unchanged
- Content access tracking is automatic and transparent
- New features are additive only
- Schema migration tool handles updates safely 