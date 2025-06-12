# Phase 6 Refactor Plan: ai_logic.py Analysis
## AI Logic Deduplication and Module Migration

### Overview
Phase 6 focuses on auditing `ai_logic.py` (2224 lines) to identify:
1. **Duplicated functions** - Already implemented in handler packages (REMOVE from ai_logic)
2. **Functions to migrate** - Need proper placement in handler packages  
3. **Core utilities** - Keep in ai_logic as shared utilities

---

## 📋 Function-by-Function Analysis

### 🔍 **DUPLICATED FUNCTIONS** (Already in handlers - REMOVE from ai_logic)

#### ✅ In handlers/ai_attention/
| ai_logic.py Function | Handler Location | Status |
|---------------------|------------------|--------|
| `detect_roleplay_triggers()` | roleplay_detection.py | ✅ REMOVE |
| `_check_dgm_post()` | dgm_handler.py (`check_dgm_post`) | ✅ REMOVE |
| `_extract_characters_from_dgm_post()` | dgm_handler.py (`extract_characters_from_dgm_post`) | ✅ REMOVE |
| `is_roleplay_allowed_channel()` | channel_restrictions.py | ✅ REMOVE |
| `should_elsie_respond_in_roleplay()` | response_logic.py | ✅ REMOVE |
| `_check_subtle_bar_interaction()` | response_logic.py (`check_subtle_bar_interaction`) | ✅ REMOVE |
| `_extract_drink_from_emote()` | response_logic.py (`extract_drink_from_emote`) | ✅ REMOVE |
| `_detect_speaking_character()` | character_tracking.py (`detect_speaking_character`) | ✅ REMOVE |
| `_check_if_other_character_addressed()` | response_logic.py (`check_if_other_character_addressed`) | ✅ REMOVE |
| `extract_addressed_characters()` | character_tracking.py | ✅ REMOVE |
| `is_valid_character_name()` | character_tracking.py | ✅ REMOVE |
| `extract_character_names_from_emotes()` | character_tracking.py | ✅ REMOVE |
| `detect_roleplay_exit_conditions()` | exit_conditions.py | ✅ REMOVE |
| `RoleplayStateManager` class | state_manager.py | ✅ REMOVE |
| `get_roleplay_state()` | state_manager.py | ✅ REMOVE |

**Total Duplicated: 15 functions + 1 class**

---

### 🚀 **FUNCTIONS TO MIGRATE** (Need proper handler placement)

#### 📝 **Query Detection Functions** → handlers/ai_response_decision/query_detection.py (NEW)
| Function | Purpose | Lines |
|----------|---------|-------|
| `is_continuation_request()` | Detect continuation phrases | ~19 |
| `is_federation_archives_request()` | Detect archive requests | ~28 |
| `extract_continuation_focus()` | Extract focus subject from continuation | ~67 |
| `is_specific_log_request()` | Detect log-specific requests | ~27 |
| `is_stardancer_query()` | Detect Stardancer queries | ~15 |
| `is_stardancer_command_query()` | Detect command staff queries | ~16 |
| `extract_tell_me_about_subject()` | Extract subject from "tell me about" | ~32 |
| `is_ooc_query()` | Detect OOC queries | ~28 |
| `extract_ooc_log_url_request()` | Extract URL request details | ~56 |
| `extract_ship_log_query()` | Extract ship log queries | ~29 |
| `is_character_query()` | Detect character queries | ~80 |
| `get_query_type()` | Classify query type | ~20 |

**Subtotal: 12 functions (~417 lines)**

#### 💬 **Conversation Management** → handlers/ai_coordinator/conversation_utils.py (NEW)
| Function | Purpose | Lines |
|----------|---------|-------|
| `detect_topic_change()` | Detect conversation topic changes | ~114 |
| `format_conversation_history()` | Format chat history | ~19 |
| `format_conversation_history_with_dgm_elsie()` | Format history with DGM posts | ~33 |

**Subtotal: 3 functions (~166 lines)**

#### 🛠️ **Utility Functions** → KEEP in ai_logic.py (Core utilities)
| Function | Purpose | Lines |
|----------|---------|-------|
| `convert_earth_date_to_star_trek()` | Date conversion utility | ~76 |
| `chunk_prompt_for_tokens()` | Token management utility | ~58 |
| `filter_meeting_info()` | Text filtering utility | ~12 |

**Subtotal: 3 functions (~146 lines)**

---

## 📦 **NEW MODULES TO CREATE**

### 1. **handlers/ai_response_decision/query_detection.py**
**Purpose**: Centralize all query detection and parsing logic
- 12 query detection functions
- Clean, focused interface for identifying user intent
- Used by strategy engine for decision making

### 2. **handlers/ai_coordinator/conversation_utils.py** 
**Purpose**: Conversation state and history management
- Topic change detection
- History formatting utilities
- Conversation flow management

---

## 🎯 **MIGRATION STRATEGY**

### Phase 6A: Remove Duplicated Functions (SAFE)
1. ✅ Verify all 15 duplicated functions are working in handlers
2. ✅ Update imports in files that use these functions  
3. ✅ Remove duplicated functions from ai_logic.py
4. ✅ Test that everything still works

### Phase 6B: Create New Modules and Migrate
1. 🔄 Create `handlers/ai_response_decision/query_detection.py`
2. 🔄 Migrate 12 query detection functions
3. 🔄 Create `handlers/ai_coordinator/conversation_utils.py`
4. 🔄 Migrate 3 conversation management functions
5. 🔄 Update imports across codebase
6. 🔄 Test functionality

### Phase 6C: Update ai_logic.py Structure
1. 🔄 Keep only 3 core utility functions
2. 🔄 Add clean imports from handler packages
3. 🔄 Update documentation to reflect new structure
4. 🔄 Final testing and validation

---

## 📊 **EXPECTED RESULTS**

### Before Phase 6:
- `ai_logic.py`: 2224 lines (monolithic)
- Mixed responsibilities: roleplay, queries, utilities, conversation management

### After Phase 6:
- `ai_logic.py`: ~200 lines (95% reduction!)
- Clean core utilities + imports from handler packages
- **+2 new focused modules** in handler packages
- All functionality preserved, better organized

### File Structure Impact:
```
📁 handlers/ai_response_decision/
  + query_detection.py        (NEW - 12 functions, ~417 lines)
  
📁 handlers/ai_coordinator/
  + conversation_utils.py     (NEW - 3 functions, ~166 lines)
  
🗂️ ai_logic.py               (3 core functions, ~200 total lines)
```

---

## ⚠️ **DEPENDENCIES TO VERIFY**

### Critical Import Updates Needed:
1. **ai_wisdom.py** - Uses many query detection functions
2. **ai_handler.py** - Uses conversation management functions  
3. **ai_emotion.py** - May use some utility functions
4. **content_retrieval_db.py** - May use query detection
5. **Any test files** - Need import updates

### Testing Priority:
1. 🧪 Query detection accuracy (all 12 functions)
2. 🧪 Conversation flow management
3. 🧪 Roleplay functionality (ensure no regression)
4. 🧪 Full end-to-end response generation

---

## 🎉 **SUCCESS CRITERIA**

✅ **100% backwards compatibility** - All existing functionality works  
✅ **Clean module separation** - Each module has focused responsibility  
✅ **No code duplication** - Single source of truth for each function  
✅ **Improved maintainability** - Easy to find and modify specific functionality  
✅ **Performance preservation** - No performance regression  

---

**Ready to proceed with Phase 6A (Remove Duplicated Functions)?** 