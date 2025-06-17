"""
Context Coordinator - Wisdom Layer Orchestrator
==============================================

This module coordinates between different context builders and provides
the appropriate context based on the response strategy approach.

REFACTORED: Simplified routing logic:
- All roleplay_ approaches -> RoleplayContextBuilder
- All other approaches -> StandardContextBuilder
"""

from typing import Any, Dict
import traceback


def get_context_for_strategy(strategy: Dict, user_message: str) -> str:
    """
    Simplified context coordinator with clean approach-based routing.
    
    Routes to appropriate context builders based on approach prefix:
    - roleplay_* approaches -> RoleplayContextBuilder  
    - All other approaches -> StandardContextBuilder
    
    Args:
        strategy: Strategy dictionary with approach
        user_message: Original user message
        
    Returns:
        Formatted context string from the appropriate context builder
    """
    try:
        approach = strategy.get('approach', 'general')
        print(f"   🧠 CONTEXT COORDINATOR: Processing approach '{approach}'")
        
        # Import context builders
        from .roleplay_context_builder import RoleplayContextBuilder
        from .standard_context_builder import StandardContextBuilder
        
        # SIMPLIFIED ROUTING: Single check based on approach prefix
        if approach.startswith('roleplay_'):
            print(f"      🎭 Using RoleplayContextBuilder (roleplay_ approach)")
            context_builder = RoleplayContextBuilder()
            result = context_builder.build_context_for_strategy(strategy, user_message)
        else:
            print(f"      📋 Using StandardContextBuilder (standard approach)")
            context_builder = StandardContextBuilder()
            result = context_builder.build_context_for_strategy(strategy, user_message)
        
        print(f"      ✅ Context generated: {len(result)} characters")
        return result
            
    except Exception as e:
        print(f"   ❌ ERROR in context coordinator: {e}")
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return f"I encountered an issue processing your request: {e}" 