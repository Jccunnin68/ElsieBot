# Content Processor Revision Plan

## Problem Analysis

The `content_processor.py` file contains a `classify_content()` method that artificially creates categories based on heuristics and pattern matching. This is problematic because:

1. **Overrides Real Wiki Categories**: The artificial classification replaces actual categories from the wiki
2. **Creates Inconsistent Data**: Generated categories don't match the real wiki structure
3. **Unnecessary Complexity**: ~200+ lines of complex classification logic that's no longer needed
4. **Migration Issues**: Pages are being "migrated" when they shouldn't be

## Current Classification Logic (TO BE REMOVED)

### In `content_processor.py`:
- `classify_content()` method (~150 lines)
- `_detect_character_page()` method (~100+ lines)
- `extract_ship_name_from_title()` method
- Complex regex patterns for ship detection
- Hardcoded ship name lists
- Character detection heuristics
- Technology/location classification

### Usage Points (TO BE UPDATED):
- `db_operations.py` line 168: `categories = content_processor.classify_content(title, content)`
- `fresh_import.py` line 121: `categories = self.processor.classify_content(title, page_data['raw_content'])`
- `test_fresh_import.py` line 53: `result_categories = processor.classify_content(title, content)`

## Solution: Use Real Wiki Categories

### Phase 1: Extract Categories from MediaWiki API

The MediaWiki API already provides category information. We need to extract this instead of generating artificial categories.

#### Update `api_client.py`:
```python
def get_page_categories(self, page_title: str) -> List[str]:
    """Get actual categories from MediaWiki API"""
    try:
        params = {
            'action': 'query',
            'format': 'json',
            'titles': page_title,
            'prop': 'categories',
            'cllimit': 'max'  # Get all categories
        }
        
        response = requests.get(self.api_url, params=params, headers=self.headers)
        data = response.json()
        
        if 'query' not in data or 'pages' not in data['query']:
            return []
        
        page = next(iter(data['query']['pages'].values()))
        
        if 'categories' not in page:
            return []
        
        # Extract category names (remove "Category:" prefix)
        categories = []
        for cat in page['categories']:
            cat_title = cat.get('title', '')
            if cat_title.startswith('Category:'):
                categories.append(cat_title[9:])  # Remove "Category:" prefix
        
        return categories
        
    except Exception as e:
        print(f"  ⚠️  Error getting categories: {e}")
        return []
```

#### Update `get_combined_page_data()` in `api_client.py`:
```python
def get_combined_page_data(self, page_title: str) -> Dict:
    """Optimized method to get multiple types of content in fewer API calls"""
    try:
        # Single API call to get parsed content, extract, page info, AND categories
        params = {
            'action': 'query',
            'format': 'json',
            'titles': page_title,
            'prop': 'extracts|info|revisions|categories',  # ADD categories
            'inprop': 'url|touched',
            'exintro': False,
            'explaintext': True,
            'exsectionformat': 'plain',
            'rvprop': 'content',
            'rvslots': '*',
            'cllimit': 'max'  # Get all categories
        }
        
        response = requests.get(self.api_url, params=params, headers=self.headers)
        data = response.json()
        
        if 'query' not in data or 'pages' not in data['query']:
            return {}
        
        page = next(iter(data['query']['pages'].values()))
        
        # Extract categories from API response
        categories = []
        if 'categories' in page:
            for cat in page['categories']:
                cat_title = cat.get('title', '')
                if cat_title.startswith('Category:'):
                    categories.append(cat_title[9:])  # Remove "Category:" prefix
        
        # Extract all available data from single response
        result = {
            'title': page_title,
            'page_id': page.get('pageid', -1),
            'extract': page.get('extract', '').strip() if 'extract' in page else '',
            'raw_wikitext': '',
            'page_exists': page.get('pageid', -1) != -1,
            'canonical_url': page.get('canonicalurl', ''),
            'touched': page.get('touched', ''),
            'lastrevid': page.get('lastrevid', 0),
            'categories': categories  # ADD real categories
        }
        
        # Get raw wikitext if available
        if 'revisions' in page and page['revisions']:
            result['raw_wikitext'] = page['revisions'][0]['slots']['main']['*']
        
        return result
        
    except Exception as e:
        print(f"  ⚠️  Error in combined API call: {e}")
        return {}
```

### Phase 2: Remove Classification Logic from Content Processor

#### Remove from `content_processor.py`:
```python
# REMOVE ENTIRELY:
def classify_content(self, title: str, content: str) -> List[str]:
    # ~150 lines of artificial classification logic

def _detect_character_page(self, title: str, content_lower: str) -> bool:
    # ~100+ lines of character detection heuristics

def extract_ship_name_from_title(self, title: str) -> Optional[str]:
    # Ship name extraction logic

# REMOVE: SHIP_NAMES list and all related constants
```

#### Replace with Simple Passthrough:
```python
def get_categories_from_page_data(self, page_data: Dict) -> List[str]:
    """Extract categories from page data (no classification)"""
    categories = page_data.get('categories', [])
    
    if not categories:
        print(f"  ⚠️  No categories found for page, using fallback")
        return ['General Information']  # Minimal fallback only
    
    print(f"  ✓ Using real wiki categories: {categories}")
    return categories
```

### Phase 3: Update Database Operations

#### Update `db_operations.py`:
```python
def save_page_to_database(self, page_data: Dict, content_processor=None) -> bool:
    """Save page content to database using real wiki categories"""
    try:
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                title = page_data['title']
                content = page_data['raw_content']
                
                # Use real categories from MediaWiki API (NO CLASSIFICATION)
                categories = page_data.get('categories', [])
                
                if not categories:
                    print(f"      ⚠️  No categories for '{title}', using fallback")
                    categories = ['General Information']
                else:
                    print(f"      ✓ Using real categories for '{title}': {categories}")
                
                # Extract MediaWiki metadata
                canonical_url = page_data.get('canonical_url') or page_data.get('url', '')
                touched = page_data.get('touched')
                
                # ... rest of the method remains the same
```

### Phase 4: Update Import Controllers

#### Update `fresh_import.py`:
```python
def process_pages(self, page_titles: List[str]) -> None:
    """Process each page and save to database"""
    print(f"   📥 Processing {len(page_titles)} pages...")
    
    for i, title in enumerate(page_titles, 1):
        try:
            print(f"\n   📄 [{i}/{len(page_titles)}] Processing: {title}")
            
            # Extract content from MediaWiki (includes real categories)
            page_data = self.extractor.extract_page_content(title)
            
            if not page_data:
                print(f"      ⚠️  No content extracted for: {title}")
                self.stats['skipped'] += 1
                continue
            
            # Save to database (NO classification, use real categories)
            success = self.db_ops.save_page_to_database(page_data)
            
            if success:
                self.stats['successful'] += 1
                
                # Track category statistics using REAL categories
                categories = page_data.get('categories', [])
                for category in categories:
                    self.stats['categories'][category] = self.stats['categories'].get(category, 0) + 1
            else:
                self.stats['failed'] += 1
            
            # ... rest remains the same
```

### Phase 5: Update Content Extractor

#### Update `content_extractor.py`:
```python
def get_enhanced_page_content_optimized(self, page_title: str) -> Optional[Dict]:
    """Optimized enhanced MediaWiki API content extraction with real categories"""
    try:
        print(f"  🚀 Fetching optimized content from MediaWiki API...")
        
        # Step 1: Get combined data in single API call (now includes categories)
        combined_data = self.api_client.get_combined_page_data(page_title)
        
        if not combined_data or not combined_data.get('page_exists'):
            print(f"  ⚠️  Page '{page_title}' does not exist")
            return None
        
        # ... existing content extraction logic ...
        
        if formatted_content and len(formatted_content) > 50:
            return {
                'title': page_title,
                'url': combined_data.get('canonical_url') or f"https://22ndmobile.fandom.com/wiki/{page_title.replace(' ', '_')}",
                'canonical_url': combined_data.get('canonical_url', ''),
                'touched': combined_data.get('touched', ''),
                'lastrevid': combined_data.get('lastrevid', 0),
                'raw_content': formatted_content,
                'categories': combined_data.get('categories', []),  # ADD real categories
                'crawled_at': datetime.now()
            }
        
        # ... rest of method
```

## Implementation Plan

### Phase 1: API Client Enhancement (Day 1)
- [ ] Add `get_page_categories()` method to `api_client.py`
- [ ] Update `get_combined_page_data()` to include categories
- [ ] Test category extraction from MediaWiki API
- [ ] Validate category data format

### Phase 2: Content Processor Simplification (Day 2)
- [ ] Remove `classify_content()` method entirely
- [ ] Remove `_detect_character_page()` method
- [ ] Remove `extract_ship_name_from_title()` method
- [ ] Remove `SHIP_NAMES` constant and related logic
- [ ] Add simple `get_categories_from_page_data()` method
- [ ] Test content processor without classification

### Phase 3: Database Operations Update (Day 3)
- [ ] Update `save_page_to_database()` to use real categories
- [ ] Remove `content_processor` parameter dependency
- [ ] Test database saving with real categories
- [ ] Validate category storage in database

### Phase 4: Import Controller Updates (Day 4)
- [ ] Update `fresh_import.py` to use real categories
- [ ] Update `incremental_import.py` to use real categories
- [ ] Remove classification calls from import logic
- [ ] Test import process with real categories

### Phase 5: Content Extractor Updates (Day 5)
- [ ] Update `content_extractor.py` to pass through real categories
- [ ] Ensure all extraction methods include categories
- [ ] Test content extraction with categories
- [ ] Validate end-to-end category flow

### Phase 6: Testing and Validation (Day 6)
- [ ] Update `test_fresh_import.py` to test real categories
- [ ] Create comprehensive test for category extraction
- [ ] Test import process with various page types
- [ ] Validate category accuracy vs wiki

### Phase 7: Cleanup and Documentation (Day 7)
- [ ] Remove unused imports and constants
- [ ] Update documentation to reflect real category usage
- [ ] Clean up any remaining classification references
- [ ] Final integration testing

## Expected Benefits

### Data Accuracy
- **100% accurate categories** - Direct from MediaWiki, no artificial mapping
- **Consistent with wiki structure** - Categories match actual wiki organization
- **No more migration issues** - Pages won't be "migrated" unnecessarily

### Code Simplification
- **Remove ~200+ lines** of complex classification logic
- **Eliminate character detection heuristics** - No more regex patterns
- **Remove ship name extraction** - No more hardcoded ship lists
- **Simplify import process** - Direct category passthrough

### Performance Improvements
- **Faster imports** - No classification processing overhead
- **Single API call** - Categories included in existing API request
- **Reduced complexity** - Simpler code paths and fewer edge cases

### Maintainability
- **No classification maintenance** - Wiki manages categories
- **Fewer bugs** - Less complex logic means fewer failure points
- **Easier debugging** - Clear data flow from API to database

## Risk Mitigation

### Fallback Handling
- **Empty categories**: Use minimal fallback ('General Information')
- **API failures**: Graceful degradation with logging
- **Invalid categories**: Sanitize and validate category names

### Testing Strategy
- **Compare before/after**: Validate category accuracy
- **Test edge cases**: Pages with no categories, malformed data
- **Performance testing**: Ensure no regression in import speed

### Rollback Plan
- **Keep old methods**: Comment out rather than delete initially
- **Feature flag**: Allow switching between old/new logic
- **Database backup**: Before running new import process

## Success Criteria

### Functional Requirements
- ✅ All pages use real MediaWiki categories
- ✅ No artificial category generation
- ✅ Import process preserves wiki category structure
- ✅ Fallback handling for pages without categories

### Technical Requirements
- ✅ Remove all classification logic from content processor
- ✅ Single API call includes category data
- ✅ Database stores real categories only
- ✅ No performance regression in import speed

### Quality Requirements
- ✅ 100% category accuracy vs MediaWiki
- ✅ No more "migration" of existing pages
- ✅ Simplified codebase with fewer edge cases
- ✅ Comprehensive test coverage

---

**This revision will eliminate artificial category generation and ensure the database contains only real, accurate categories from the MediaWiki source.**

**Status: PLANNED - Ready for implementation** 