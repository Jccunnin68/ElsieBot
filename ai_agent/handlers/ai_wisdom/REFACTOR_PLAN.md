# **AI Wisdom Module Refactor Plan**

## **Overview**

Now that we've successfully removed artificial category mappings and established direct database category usage, we need to refactor the AI Wisdom module to take full advantage of the simplified, category-based backend. This refactor will eliminate complex legacy logic and replace it with clean, category-driven searches.

## **Current State Analysis**

### **Legacy System Issues**
- **Complex ship detection logic** in `content_retriever.py` (~50+ lines of regex patterns)
- **Multiple search strategies** that overlap and conflict
- **Hardcoded ship name lists** and pattern matching
- **Page type filtering** mixed with category filtering
- **Character detection heuristics** instead of direct category queries

### **New Category Structure (Confirmed)**
Based on specifications:

#### **Character Categories**
- **"Characters"** - Main character category
- **"NPCs"** - Non-player characters  
- **Exception**: **"NPC Starships"** - Ships, not characters (exclude from character searches)

#### **Log Categories**
- **Pattern**: `[ShipName] Log` (e.g., "Stardancer Log", "Adagio Log")
- **Universal Rule**: All log categories contain the word "Log"
- **Search Strategy**: `WHERE category LIKE '%Log%'`

#### **Ship Categories**
- **"Ship Information"** - General ship data
- **"Starship"** or **"Ship"** - Any category containing these words
- **"NPC Starships"** - NPC-controlled ships
- **Search Strategy**: `WHERE category LIKE '%Ship%' OR category LIKE '%Starship%'`

## **Refactor Plan**

### **Phase 1: Database Controller Enhancement**

#### **Add Category-Specific Query Methods**
```python
# ai_agent/database_controller.py

def get_character_categories(self) -> List[str]:
    """Get all character-related categories (excluding NPC Starships)"""
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

def get_ship_categories(self) -> List[str]:
    """Get all ship-related categories"""
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

def search_characters(self, query: str, limit: int = 10) -> List[Dict]:
    """Search character pages using category filtering"""
    character_categories = self.get_character_categories()
    return self.search_pages(query, categories=character_categories, limit=limit)

def search_ships(self, query: str, limit: int = 10) -> List[Dict]:
    """Search ship pages using category filtering"""
    ship_categories = self.get_ship_categories()
    return self.search_pages(query, categories=ship_categories, limit=limit)

def search_logs(self, query: str, ship_name: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """Search log pages using category filtering"""
    log_categories = self._get_actual_log_categories_from_db()
    
    if ship_name:
        # Filter to specific ship logs
        ship_log_categories = [cat for cat in log_categories 
                              if ship_name.lower() in cat.lower()]
        if ship_log_categories:
            return self.search_pages(query, categories=ship_log_categories, limit=limit)
    
    # Search all logs
    return self.search_pages(query, categories=log_categories, limit=limit)
```

### **Phase 2: Content Retriever Simplification**

#### **Remove Complex Ship Detection Logic**
```python
# ai_agent/handlers/ai_wisdom/content_retriever.py

# REMOVE: is_ship_log_title() function (~50+ lines)
# REMOVE: Complex regex patterns for ship detection
# REMOVE: Hardcoded ship name lists
# REMOVE: Multiple search strategy fallbacks

# REPLACE WITH: Simple category-based searches
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
        # ... existing processing logic
    
    return final_content

def get_ship_information(ship_name: str) -> str:
    """Simplified ship search using categories"""
    controller = get_db_controller()
    
    # Direct category-based ship search
    results = controller.search_ships(ship_name, limit=10)
    
    # ... existing processing logic

def get_character_context(character_name: str) -> str:
    """Simplified character search using categories"""
    controller = get_db_controller()
    
    # Direct category-based character search
    results = controller.search_characters(character_name, limit=10)
    
    # ... existing processing logic
```

#### **Simplify Search Strategy**
```python
# OLD: Multiple complex search strategies
def get_relevant_wiki_context(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    # Complex logic with multiple fallbacks
    # Ship detection heuristics
    # Page type filtering
    # Category mapping
    # Multiple search attempts

# NEW: Simple category-driven approach
def get_relevant_wiki_context(query: str, mission_logs_only: bool = False, is_roleplay: bool = False) -> str:
    controller = get_db_controller()
    
    # Determine search type based on query intent
    if is_log_query(query):
        return controller.search_logs(query, limit=20)
    elif is_character_query(query):
        return controller.search_characters(query, limit=15)
    elif is_ship_query(query):
        return controller.search_ships(query, limit=15)
    else:
        return controller.search_pages(query, limit=20)
```

### **Phase 3: Query Detection Simplification**

#### **Replace Complex Heuristics**
```python
# ai_agent/handlers/ai_wisdom/query_detection.py (if exists)

def is_log_query(query: str) -> bool:
    """Simple log query detection"""
    log_indicators = ['log', 'mission', 'stardate', 'what happened', 'events']
    return any(indicator in query.lower() for indicator in log_indicators)

def is_character_query(query: str) -> bool:
    """Simple character query detection"""
    character_indicators = ['who is', 'tell me about', 'character', 'person', 'crew']
    return any(indicator in query.lower() for indicator in character_indicators)

def is_ship_query(query: str) -> bool:
    """Simple ship query detection"""
    ship_indicators = ['uss', 'ship', 'vessel', 'starship', 'specs', 'class']
    return any(indicator in query.lower() for indicator in ship_indicators)
```

### **Phase 4: Context Builder Updates**

#### **Non-Roleplay Context Builder**
```python
# ai_agent/handlers/ai_wisdom/non_roleplay_context_builder.py

def get_character_context(user_message: str, strategy: Dict[str, Any] = None, is_roleplay: bool = False) -> str:
    """Simplified character context using categories"""
    controller = get_db_controller()
    
    # Extract character name from message
    character_name = extract_character_name(user_message)
    
    # Direct category-based search
    results = controller.search_characters(character_name, limit=10)
    
    # ... existing processing logic

def get_logs_context(user_message: str, strategy: Dict[str, Any], is_roleplay: bool = False) -> str:
    """Simplified logs context using categories"""
    controller = get_db_controller()
    
    # Extract ship name if specified
    ship_name = strategy.get('ship_name')
    
    # Direct category-based log search
    results = controller.search_logs(user_message, ship_name=ship_name, limit=15)
    
    # ... existing processing logic

def get_ship_context(user_message: str, is_roleplay: bool = False) -> str:
    """New simplified ship context using categories"""
    controller = get_db_controller()
    
    # Direct category-based ship search
    results = controller.search_ships(user_message, limit=10)
    
    # ... existing processing logic
```

#### **Roleplay Context Builder**
```python
# ai_agent/handlers/ai_wisdom/roleplay_context_builder.py

def _get_roleplay_database_context(user_message: str) -> str:
    """Simplified roleplay database context using categories"""
    controller = get_db_controller()
    
    # Determine context type needed
    if is_character_query(user_message):
        results = controller.search_characters(user_message, limit=5)
    elif is_ship_query(user_message):
        results = controller.search_ships(user_message, limit=5)
    elif is_log_query(user_message):
        results = controller.search_logs(user_message, limit=5)
    else:
        results = controller.search_pages(user_message, limit=5)
    
    # ... existing processing logic
```

### **Phase 5: Code Cleanup and Removal**

#### **Files to Significantly Simplify**
- `content_retriever.py` - Remove ~200-300 lines of complex logic
- `non_roleplay_context_builder.py` - Simplify search strategies
- `roleplay_context_builder.py` - Simplify database context building

#### **Functions to Remove/Simplify**
```python
# REMOVE from content_retriever.py:
- is_ship_log_title() - ~50+ lines of regex patterns
- Complex ship name extraction logic
- Multiple search strategy fallbacks
- Hardcoded ship name lists
- Page type filtering mixed with categories

# SIMPLIFY in content_retriever.py:
- get_log_content() - Use direct category search
- get_ship_information() - Use direct category search
- get_relevant_wiki_context() - Single unified approach
- search_by_type() - Use category-based search

# SIMPLIFY in context builders:
- All search functions to use direct category queries
- Remove complex heuristics and fallback logic
- Unify search approaches across roleplay/non-roleplay
```

## **Expected Benefits**

### **Code Reduction**
- **~25-30% codebase reduction** in AI Wisdom module
- **Eliminate ~200-300 lines** of complex ship detection logic
- **Remove multiple search strategies** in favor of unified approach
- **Simplify maintenance** significantly

### **Performance Improvements**
- **Direct database queries** instead of complex filtering
- **GIN index utilization** on categories for fast searches
- **Reduced CPU overhead** from pattern matching and heuristics
- **Faster query response times**

### **Improved Reliability**
- **Single source of truth** - database categories
- **No more regex pattern maintenance** for ship detection
- **Consistent search behavior** across all contexts
- **Easier debugging** and troubleshooting

### **Enhanced Maintainability**
- **Clear separation of concerns** - categories define content types
- **Simplified logic flow** - category → search → results
- **Easier to add new content types** - just add categories
- **Reduced complexity** for future developers

## **Implementation Strategy**

### **Phase 1: Database Controller (Week 1)**
1. Add category-specific query methods
2. Test new search functions
3. Validate category detection logic
4. Ensure backward compatibility

### **Phase 2: Content Retriever (Week 2)**
1. Replace complex ship detection with category search
2. Simplify log search logic
3. Update character search functions
4. Remove deprecated functions

### **Phase 3: Context Builders (Week 3)**
1. Update non-roleplay context builder
2. Update roleplay context builder
3. Simplify search strategies
4. Test integration

### **Phase 4: Testing and Validation (Week 4)**
1. Comprehensive testing of all search functions
2. Performance benchmarking
3. User acceptance testing
4. Documentation updates

### **Phase 5: Cleanup and Optimization (Week 5)**
1. Remove deprecated code
2. Optimize database queries
3. Update documentation
4. Final validation

## **Risk Mitigation**

### **Backward Compatibility**
- **Maintain existing function signatures** during transition
- **Add deprecation warnings** for old functions
- **Gradual migration** rather than big-bang replacement
- **Comprehensive testing** at each phase

### **Data Validation**
- **Verify category coverage** - ensure all content is properly categorized
- **Test edge cases** - handle missing or malformed categories
- **Validate search results** - ensure quality doesn't degrade
- **Monitor performance** - ensure queries remain fast

### **Rollback Plan**
- **Keep old functions** as fallbacks during transition
- **Feature flags** to switch between old/new logic
- **Database backups** before major changes
- **Staged deployment** to catch issues early

## **Success Criteria**

### **Functional Requirements**
- ✅ All existing search functionality preserved
- ✅ Character searches use Character/NPC categories (excluding NPC Starships)
- ✅ Log searches use categories containing "Log"
- ✅ Ship searches use categories containing "Ship" or "Starship"
- ✅ Performance equal or better than current system

### **Technical Requirements**
- ✅ 25%+ code reduction in AI Wisdom module
- ✅ Elimination of complex regex ship detection
- ✅ Single unified search strategy
- ✅ Direct database category utilization
- ✅ Comprehensive test coverage

### **Quality Requirements**
- ✅ No regression in search quality
- ✅ Improved response times
- ✅ Simplified maintenance procedures
- ✅ Enhanced debugging capabilities
- ✅ Better error handling

## **Implementation Checklist**

### **Phase 1: Database Controller Enhancement**
- [ ] Add `get_character_categories()` method
- [ ] Add `get_ship_categories()` method  
- [ ] Add `search_characters()` method
- [ ] Add `search_ships()` method
- [ ] Update `search_logs()` method for ship filtering
- [ ] Test all new database methods
- [ ] Validate category detection accuracy

### **Phase 2: Content Retriever Simplification**
- [ ] Remove `is_ship_log_title()` function
- [ ] Simplify `get_log_content()` to use category search
- [ ] Simplify `get_ship_information()` to use category search
- [ ] Add `get_character_context()` using category search
- [ ] Simplify `get_relevant_wiki_context()` unified approach
- [ ] Remove complex ship detection regex patterns
- [ ] Remove hardcoded ship name lists
- [ ] Test all updated functions

### **Phase 3: Context Builder Updates**
- [ ] Update `non_roleplay_context_builder.py` character context
- [ ] Update `non_roleplay_context_builder.py` logs context
- [ ] Add ship context to `non_roleplay_context_builder.py`
- [ ] Update `roleplay_context_builder.py` database context
- [ ] Simplify search strategies across both builders
- [ ] Test roleplay and non-roleplay contexts

### **Phase 4: Query Detection Enhancement**
- [ ] Create/update query detection functions
- [ ] Add `is_log_query()` function
- [ ] Add `is_character_query()` function
- [ ] Add `is_ship_query()` function
- [ ] Test query type detection accuracy
- [ ] Integrate with content retriever

### **Phase 5: Testing and Validation**
- [ ] Create comprehensive test suite
- [ ] Test character search functionality
- [ ] Test ship search functionality
- [ ] Test log search functionality
- [ ] Performance benchmarking
- [ ] User acceptance testing
- [ ] Documentation updates

### **Phase 6: Code Cleanup**
- [ ] Remove deprecated functions
- [ ] Clean up unused imports
- [ ] Update function documentation
- [ ] Optimize database queries
- [ ] Final integration testing

---

**This refactor will transform the AI Wisdom module from a complex, heuristic-based system into a clean, category-driven architecture that's easier to maintain, faster to execute, and more reliable in operation.**

**Status: PLANNED - Ready for implementation** 