# **AI Wisdom Module Refactor Plan**

## **Overview**

Following our successful db_populator cleanup that removed artificial category classification and established real MediaWiki category usage, we now need to refactor the AI Wisdom module to leverage this simplified, category-based backend. This refactor will eliminate complex legacy logic and replace it with clean, category-driven searches.

## **Key Learnings from DB Populator Cleanup**

### **✅ Confirmed Working Systems**
- **Real MediaWiki categories** are now stored in `wiki_pages.categories` (array field)
- **Category extraction** works correctly via `get_combined_page_data()` in API client
- **Database uses GIN indexes** on categories for fast category-based searches
- **No artificial classification** - all categories come directly from MediaWiki
- **Clean fallback handling** for pages without categories ('General Information')

### **✅ Available Infrastructure** 
- **`search_pages(categories=List[str])`** method supports category filtering
- **`_get_actual_log_categories_from_db()`** dynamically gets log categories from database
- **Category-based queries** using `WHERE categories && %s` array operations
- **Hierarchical search** with category filtering + full-text search

## **Current State Analysis**

### **Legacy System Issues (CONFIRMED in current code)**
- **Complex ship detection logic** in `content_retriever.py` - `is_ship_log_title()` function (~100+ lines of regex patterns)
- **Hardcoded ship name lists** in `log_patterns.py` - `SHIP_NAMES` array with manual ship detection
- **Multiple overlapping search strategies** with complex fallback logic
- **Character detection heuristics** instead of direct category queries
- **Mixed page type and category filtering** causing confusion

### **Current Category Reality (from database)**
After the db_populator cleanup, the actual categories in use are:

#### **Log Categories (Dynamic)**
- **Pattern**: Categories containing "Log" (e.g., "Stardancer Log", "Adagio Log")
- **Detection**: `WHERE LOWER(category) LIKE '%log%'` 
- **Current method**: `_get_actual_log_categories_from_db()` ✅ Already implemented

#### **Character Categories (Dynamic)**
- **"Characters"** - Main character category
- **"NPCs"** - Non-player characters
- **Exception**: **"NPC Starships"** - Ships, not characters (exclude from character searches)

#### **Ship Categories (Dynamic)**
- **"Ship Information"** - General ship data
- **"NPC Starships"** - NPC-controlled ships
- **Detection**: `WHERE LOWER(category) LIKE '%ship%' OR LOWER(category) LIKE '%starship%'`

#### **Other Categories**
- **"General Information"** - Fallback category
- **Various specific categories** from actual MediaWiki

## **Refactor Plan**

### **Phase 1: Database Controller Enhancement**

**✅ ALREADY PARTIALLY IMPLEMENTED** - `search_pages()` supports `categories` parameter

**ADD MISSING METHODS:**
```python
# ai_agent/database_controller.py

def get_character_categories(self) -> List[str]:
    """Get all character-related categories (excluding NPC Starships)"""
    try:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT unnest(categories) as category 
                    FROM wiki_pages 
                    WHERE categories IS NOT NULL 
                    AND EXISTS (
                        SELECT 1 FROM unnest(categories) cat 
                        WHERE (LOWER(cat) LIKE '%character%' OR LOWER(cat) LIKE '%npc%')
                        AND LOWER(cat) NOT LIKE '%npc starship%'
                    )
                    ORDER BY category
                """)
                return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"✗ Error getting character categories: {e}")
        return []

def get_ship_categories(self) -> List[str]:
    """Get all ship-related categories"""
    try:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT unnest(categories) as category 
                    FROM wiki_pages 
                    WHERE categories IS NOT NULL 
                    AND EXISTS (
                        SELECT 1 FROM unnest(categories) cat 
                        WHERE LOWER(cat) LIKE '%ship%' OR LOWER(cat) LIKE '%starship%'
                    )
                    ORDER BY category
                """)
                return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"✗ Error getting ship categories: {e}")
        return []

def search_characters(self, query: str, limit: int = 10) -> List[Dict]:
    """Search character pages using category filtering"""
    character_categories = self.get_character_categories()
    if not character_categories:
        print("⚠️  No character categories found, falling back to general search")
        return self.search_pages(query, limit=limit)
    return self.search_pages(query, categories=character_categories, limit=limit)

def search_ships(self, query: str, limit: int = 10) -> List[Dict]:
    """Search ship pages using category filtering"""
    ship_categories = self.get_ship_categories()
    if not ship_categories:
        print("⚠️  No ship categories found, falling back to general search")
        return self.search_pages(query, limit=limit)
    return self.search_pages(query, categories=ship_categories, limit=limit)

def search_logs(self, query: str, ship_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """Search log pages using category filtering"""
    log_categories = self._get_actual_log_categories_from_db()  # ✅ Already exists
    if not log_categories:
        print("⚠️  No log categories found, using force_mission_logs_only fallback")
        return self.search_pages(query, ship_name=ship_name, limit=limit, force_mission_logs_only=True)
    
    if ship_name:
        # Filter to specific ship logs
        ship_log_categories = [cat for cat in log_categories 
                              if ship_name.lower() in cat.lower()]
        if ship_log_categories:
            return self.search_pages(query, categories=ship_log_categories, ship_name=ship_name, limit=limit)
    
    # Search all logs with category filtering
    return self.search_pages(query, categories=log_categories, ship_name=ship_name, limit=limit)
```

### **Phase 2: Content Retriever Simplification**

**REMOVE COMPLEX LOGIC:**
```python
# REMOVE from content_retriever.py:
def is_ship_log_title(title: str) -> bool:
    # ~100+ lines of complex regex patterns - REMOVE ENTIRELY

# REMOVE from log_patterns.py:
SHIP_NAMES = [...]  # Hardcoded ship list - REMOVE ENTIRELY
```

**REPLACE WITH SIMPLE CATEGORY-BASED SEARCHES:**
```python
# ai_agent/handlers/ai_wisdom/content_retriever.py

def get_log_content(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    """Simplified log search using categories"""
    controller = get_db_controller()
    
    # Direct category-based log search
    results = controller.search_logs(query, limit=20)
    
    if not results:
        return ""
    
    # Process results (existing logic remains)
    log_contents = []
    for result in results:
        title = result['title']
        content = result['raw_content']
        parsed_content = parse_log_characters(content, result.get('ship_name'), title)
        formatted_log = f"**{title}**\n{parsed_content}"
        log_contents.append(formatted_log)
    
    final_content = '\n\n---LOG SEPARATOR---\n\n'.join(log_contents)
    
    # Process through LLM as before
    processor = get_llm_processor()
    result = processor.process_query_results("logs", final_content, query, is_roleplay, force_processing=True)
    return result.content

def get_ship_information(ship_name: str) -> str:
    """Simplified ship search using categories"""
    controller = get_db_controller()
    
    # Direct category-based ship search
    results = controller.search_ships(ship_name, limit=10)
    
    if not results:
        return ""
    
    # Existing processing logic
    ship_info = []
    for result in results:
        title = result['title']
        content = result['raw_content']
        page_text = f"**{title}**\n{content}"
        ship_info.append(page_text)
    
    final_content = '\n\n---\n\n'.join(ship_info)
    
    # Process through LLM if needed (existing logic)
    if should_process_data(final_content):
        processor = get_llm_processor()
        result = processor.process_query_results(determine_query_type('get_ship_information'), final_content, create_query_description('get_ship_information', ship_name=ship_name), _get_roleplay_context_from_caller())
        return result.content
    
    return final_content

def get_character_context(character_name: str) -> str:
    """NEW: Simplified character search using categories"""
    controller = get_db_controller()
    
    # Direct category-based character search
    results = controller.search_characters(character_name, limit=10)
    
    if not results:
        return ""
    
    character_info = []
    for result in results:
        title = result['title']
        content = result['raw_content']
        page_text = f"**{title}**\n{content}"
        character_info.append(page_text)
    
    final_content = '\n\n---\n\n'.join(character_info)
    
    # Process through LLM if needed
    if should_process_data(final_content):
        processor = get_llm_processor()
        result = processor.process_query_results("character", final_content, f"character information for {character_name}", _get_roleplay_context_from_caller())
        return result.content
    
    return final_content
```

**SIMPLIFY SEARCH STRATEGY:**
```python
def get_relevant_wiki_context(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    """Simplified unified search strategy using categories"""
    controller = get_db_controller()
    
    # Simple query type detection
    if mission_logs_only or any(indicator in query.lower() for indicator in ['log', 'mission', 'stardate', 'what happened']):
        return get_log_content(query, mission_logs_only, is_roleplay)
    elif any(indicator in query.lower() for indicator in ['who is', 'tell me about', 'character', 'person', 'crew']):
        # Extract potential character name and search
        character_name = query  # Simple extraction - could be enhanced
        return get_character_context(character_name)
    elif any(indicator in query.lower() for indicator in ['uss', 'ship', 'vessel', 'starship', 'specs', 'class']):
        # Extract potential ship name and search
        ship_name = query  # Simple extraction - could be enhanced
        return get_ship_information(ship_name)
    else:
        # General search - use existing logic
        results = controller.search_pages(query, limit=20)
        if not results:
            return ""
        
        context_parts = []
        for result in results:
            title = result['title']
            content = result['raw_content']
            page_text = f"**{title}**\n{content}"
            context_parts.append(page_text)
        
        return '\n\n---\n\n'.join(context_parts)
```

### **Phase 3: Context Builder Updates**

**UPDATE NON-ROLEPLAY CONTEXT BUILDER:**
```python
# ai_agent/handlers/ai_wisdom/non_roleplay_context_builder.py

def get_character_context(user_message: str, strategy: Dict[str, Any] = None, is_roleplay: bool = False) -> str:
    """Simplified character context using categories"""
    # Extract character name from message (enhance this as needed)
    character_name = user_message  # Could extract more intelligently
    
    # Use new character search function
    return get_character_context(character_name)

def get_logs_context(user_message: str, strategy: Dict[str, Any], is_roleplay: bool = False) -> str:
    """Simplified logs context using categories"""
    # Extract ship name if specified in strategy
    ship_name = strategy.get('ship_name') or strategy.get('target_ship')
    
    # Use simplified log search
    controller = get_db_controller()
    results = controller.search_logs(user_message, ship_name=ship_name, limit=15)
    
    if not results:
        return f"No logs found for: {user_message}"
    
    # Process results
    log_contents = []
    for result in results:
        content = result['raw_content']
        log_date = result.get('log_date', 'Unknown Date')
        ship = result.get('ship_name', 'Unknown Ship')
        title = result['title']
        
        type_indicator = f" [Mission Log - {log_date}]"
        if ship and ship.lower() != 'unknown ship':
            type_indicator += f" ({ship.upper()})"
        
        log_contents.append(f"**{title}{type_indicator}**\n{content}")
    
    return '\n\n---\n\n'.join(log_contents)
```

### **Phase 4: Code Cleanup and Removal**

**FILES TO SIGNIFICANTLY SIMPLIFY:**
- `content_retriever.py` - Remove ~150-200 lines of complex ship detection
- `log_patterns.py` - Remove hardcoded `SHIP_NAMES` list and related functions
- `non_roleplay_context_builder.py` - Simplify search strategies
- `roleplay_context_builder.py` - Simplify database context building

**FUNCTIONS TO REMOVE:**
```python
# REMOVE from content_retriever.py:
- is_ship_log_title() - ~100+ lines of regex patterns
- Complex ship name extraction from `SHIP_NAMES` list
- Multiple search strategy fallbacks in `get_log_content()`

# REMOVE from log_patterns.py:
- `SHIP_NAMES` array - Hardcoded ship list
- Ship-specific regex patterns
- `extract_ship_name_from_log_content()` - if it uses hardcoded ship names

# SIMPLIFY throughout:
- All search functions to use direct category queries
- Remove complex heuristics and fallback logic
- Unify search approaches across roleplay/non-roleplay
```

## **Implementation Strategy**

### **Phase 1: Database Controller (Day 1)**
- [ ] Add `get_character_categories()` method
- [ ] Add `get_ship_categories()` method  
- [ ] Add `search_characters()` method
- [ ] Add `search_ships()` method
- [ ] Update `search_logs()` method (enhance existing)
- [ ] Test all new database methods

### **Phase 2: Content Retriever (Day 2-3)**
- [ ] Remove `is_ship_log_title()` function entirely
- [ ] Simplify `get_log_content()` to use `controller.search_logs()`
- [ ] Simplify `get_ship_information()` to use `controller.search_ships()`
- [ ] Add `get_character_context()` using `controller.search_characters()`
- [ ] Simplify `get_relevant_wiki_context()` unified approach
- [ ] Test all updated functions

### **Phase 3: Log Patterns Cleanup (Day 4)**
- [ ] Remove `SHIP_NAMES` array from `log_patterns.py`
- [ ] Remove hardcoded ship detection functions
- [ ] Keep only the character correction logic (if still needed)
- [ ] Update imports throughout codebase

### **Phase 4: Context Builder Updates (Day 5-6)**
- [ ] Update non-roleplay context builder methods
- [ ] Update roleplay context builder methods
- [ ] Simplify search strategies across both builders
- [ ] Test roleplay and non-roleplay contexts

### **Phase 5: Testing and Validation (Day 7)**
- [ ] Create comprehensive test suite
- [ ] Test character search functionality
- [ ] Test ship search functionality  
- [ ] Test log search functionality
- [ ] Performance benchmarking
- [ ] User acceptance testing

## **Expected Benefits**

### **Code Reduction**
- **~20-25% codebase reduction** in AI Wisdom module
- **Eliminate ~150-200 lines** of complex ship detection logic
- **Remove hardcoded ship name maintenance**
- **Unified search strategy** across all contexts

### **Performance Improvements**
- **Direct database queries** using GIN indexes on categories
- **No more regex pattern matching** overhead
- **Reduced CPU usage** from complex heuristics
- **Faster category-based searches**

### **Improved Reliability**
- **Single source of truth** - database categories from MediaWiki
- **No more hardcoded ship lists** to maintain
- **Consistent search behavior** across all contexts
- **Easier debugging** with clear data flow

### **Enhanced Maintainability**
- **Categories define content types** - no artificial mapping
- **Database-driven logic** - scalable and flexible
- **Clear separation of concerns**  
- **Easier to add new content types** by adding categories in MediaWiki

## **Success Criteria**

### **Functional Requirements**
- ✅ All existing search functionality preserved
- ✅ Character searches use dynamic character categories
- ✅ Log searches use dynamic log categories (containing "Log")
- ✅ Ship searches use dynamic ship categories (containing "Ship"/"Starship")
- ✅ Performance equal or better than current system

### **Technical Requirements**
- ✅ 20%+ code reduction in AI Wisdom module
- ✅ Elimination of `is_ship_log_title()` function
- ✅ Removal of hardcoded `SHIP_NAMES` array
- ✅ Single unified search strategy using categories
- ✅ Direct database category utilization

### **Quality Requirements**
- ✅ No regression in search quality
- ✅ Improved response times via GIN indexes
- ✅ Simplified maintenance procedures
- ✅ Enhanced debugging capabilities
- ✅ Better error handling with category fallbacks

---

**This refactor will transform the AI Wisdom module from a complex, heuristic-based system into a clean, category-driven architecture that leverages our successful db_populator cleanup work.**

**STATUS: UPDATED AND READY FOR IMPLEMENTATION** 

**Next Step: Awaiting approval to begin Phase 1 implementation** 