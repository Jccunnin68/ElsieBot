"""
Context Coordination Service - Pythonic Context Routing
=======================================================

This service coordinates between different context builders and provides
the appropriate context based on the response strategy approach.
Refactored from a standalone function to a proper service class.
"""

from typing import Any, Dict
import traceback

from .wisdom_engine import WisdomEngine
from .roleplay_context_builder import RoleplayContextBuilder


class ContextCoordinationService:
    """
    Service for coordinating context generation based on strategy approach.
    
    This service provides a clean API for routing context generation requests
    to the appropriate context builders while maintaining proper encapsulation.
    """
    
    def __init__(self):
        """Initialize the context coordination service."""
        self._wisdom_engine = None
        self._roleplay_builder = None
    
    @property
    def wisdom_engine(self) -> WisdomEngine:
        """Lazy-load wisdom engine to avoid circular imports."""
        if self._wisdom_engine is None:
            self._wisdom_engine = WisdomEngine()
        return self._wisdom_engine
    
    @property
    def roleplay_builder(self) -> RoleplayContextBuilder:
        """Lazy-load roleplay context builder to avoid circular imports."""
        if self._roleplay_builder is None:
            self._roleplay_builder = RoleplayContextBuilder()
        return self._roleplay_builder

    def get_context_for_strategy(self, strategy: Dict, user_message: str) -> str:
        """
        Get appropriate context based on the response strategy approach.
        
        Routes to appropriate context builders based on approach prefix:
        - roleplay_* approaches -> RoleplayContextBuilder  
        - All other approaches -> WisdomEngine
        
        Args:
            strategy: Strategy dictionary with approach
            user_message: Original user message
            
        Returns:
            Formatted context string from the appropriate context builder
        """
        try:
            approach = strategy.get('approach', 'general')
            print(f"   🧠 CONTEXT COORDINATOR: Processing approach '{approach}'")
            
            # Route based on approach prefix
            if approach.startswith('roleplay_'):
                print(f"      🎭 Using RoleplayContextBuilder (roleplay_ approach)")
                result = self.roleplay_builder.build_context_for_strategy(strategy, user_message)
            else:
                print(f"      🧠 Using WisdomEngine (standard approach)")
                result = self.wisdom_engine.build_context_for_strategy(strategy, user_message)
            
            print(f"      ✅ Context generated: {len(result)} characters")
            return result
                
        except Exception as e:
            print(f"   ❌ ERROR in context coordinator: {e}")
            print(f"   📋 Traceback: {traceback.format_exc()}")
            return f"I encountered an issue processing your request: {e}"

    def get_available_strategies(self) -> Dict[str, str]:
        """
        Get information about available context strategies.
        
        Returns:
            Dictionary mapping strategy types to descriptions
        """
        return {
            'roleplay_active': 'Active roleplay context with character awareness',
            'roleplay_listening': 'Passive roleplay context for scene observation',
            'comprehensive': 'Comprehensive database context for complex queries',
            'ship_info': 'Ship-specific information context',
            'character_info': 'Character-specific information context',
            'logs': 'Log-based historical context',
            'federation_archives': 'Federation archives search context',
            'general': 'General purpose context'
        }

    def validate_strategy(self, strategy: Dict) -> bool:
        """
        Validate that a strategy dictionary contains required fields.
        
        Args:
            strategy: Strategy dictionary to validate
            
        Returns:
            True if strategy is valid, False otherwise
        """
        if not isinstance(strategy, dict):
            return False
        
        required_fields = ['approach']
        return all(field in strategy for field in required_fields)

    def get_context_builder_for_approach(self, approach: str) -> str:
        """
        Get the name of the context builder that handles a specific approach.
        
        Args:
            approach: Strategy approach string
            
        Returns:
            Name of the context builder class
        """
        if approach.startswith('roleplay_'):
            return 'RoleplayContextBuilder'
        else:
            return 'WisdomEngine' 