"""
AI Wisdom - Database Access and Context Generation (Phase 5 Refactor)
======================================================================

This module has been refactored to use the modular ai_database handler package.
The massive 751-line ai_wisdom.py has been broken down into focused modules
while preserving all existing functionality.

Refactored Structure:
- handlers/ai_database/context_coordinator.py - Main coordination
- handlers/ai_database/roleplay_contexts.py - Roleplay context generation  
- handlers/ai_database/database_contexts.py - Standard database contexts
- handlers/ai_database/ooc_handlers.py - Out-of-character queries

Legacy Support:
    All functions delegate to the new modular system for backwards compatibility.
"""

# Import from the new modular handler package
from handlers.ai_database import (
    get_context_for_strategy,
    handle_ooc_url_request
)

# Export the main functions for external use
__all__ = [
    'get_context_for_strategy',
    'handle_ooc_url_request'
]


# REFACTOR SUMMARY - PHASE 5 COMPLETE  
# ===================================
#
# BEFORE: 751 lines of monolithic database/context generation code
# AFTER:  Clean delegation to modular ai_database handler package
#
# NEW PACKAGE STRUCTURE:
# 📁 handlers/ai_database/
#   🐍 context_coordinator.py     - Main coordination (get_context_for_strategy)
#   🐍 roleplay_contexts.py       - Roleplay context generation (238 lines)
#   🐍 database_contexts.py       - Standard database contexts (341 lines) 
#   🐍 ooc_handlers.py           - Out-of-character queries (63 lines)
#   🐍 __init__.py               - Clean package exports (47 lines)
#
# BENEFITS:
# - Clear separation of concerns across focused modules
# - Each module has single responsibility for specific context types
# - Easy to test individual context generators
# - Better maintainability and code organization
# - Clean imports and exports via __init__.py files
# - Comprehensive documentation and type hints
#
# BACKWARDS COMPATIBILITY:
# - All existing functionality preserved
# - All function signatures maintained
# - No breaking changes to external interfaces
# - Legacy imports continue to work
#
# TOTAL CODE ORGANIZATION:
# - Original: 751 lines in single file
# - Refactored: 4 focused modules averaging ~150 lines each
# - Much easier to navigate and maintain specific functionality
