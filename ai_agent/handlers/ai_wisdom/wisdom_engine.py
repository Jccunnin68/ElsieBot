"""
Wisdom Engine for Prompt Orchestration
======================================

This module contains the new WisdomEngine, which orchestrates
the prompt generation process. It uses the PromptLibrary to construct
the final context for the LLM based on a strategy from the
structured_query_handler.
"""

from typing import Dict, Any
from .prompt_builder import PromptLibrary

class WisdomEngine:
    """Orchestrates prompt generation using a strategy and the PromptLibrary."""

    def __init__(self):
        self.prompt_library = PromptLibrary()

    def build_context_for_strategy(self, strategy: Dict[str, Any], user_message: str) -> str:
        """
        Builds a context string for the LLM based on the provided strategy.

        This method acts as a router, calling the appropriate method from the
        PromptLibrary based on the 'approach' defined in the strategy.
        """
        approach = strategy.get('approach', 'comprehensive')
        print(f"         🎯 WISDOM ENGINE: Processing approach '{approach}'")
        
        # Extract common data from the strategy
        subject = strategy.get('subject', user_message)
        results = strategy.get('results', [])

        if approach in ['logs', 'temporal_logs']:
            temporal_type = strategy.get('temporal_type', 'latest')
            return self.prompt_library.build_logs_prompt(subject, results, temporal_type)
        
        elif approach == 'comprehensive':
            return self.prompt_library.build_comprehensive_prompt(subject, results)
        
        elif approach == 'simple_chat':
            return "Simple conversational response - no additional context needed."
            
        else:
            # Fallback for any unknown or unspecified strategies.
            print(f"         ❌ Unknown approach: '{approach}'. Defaulting to comprehensive.")
            return self.prompt_library.build_comprehensive_prompt(subject, results) 