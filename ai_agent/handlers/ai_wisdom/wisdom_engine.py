"""
Wisdom Engine for Prompt Orchestration
======================================

This module contains the new WisdomEngine, which orchestrates
the prompt generation process. It uses the PromptLibrary to construct
the final context for the LLM based on a strategy from the
structured_query_handler.
"""

from typing import Dict, Any
from handlers.ai_wisdom.prompt_builder import PromptLibrary

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
        subject = strategy.get('subject') or user_message
        results = strategy.get('results', [])

        # Determine if this is a character query
        category = strategy.get('category', '').lower()
        is_character_query = 'character' in category or 'npc' in category

        if is_character_query and results:
            return self._build_character_prompt(subject, results)

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

    def _build_character_prompt(self, subject: str, results: list) -> str:
        """
        Builds a special prompt for character queries. It verifies that the top
        search result matches the query subject before proceeding.
        """
        print(f"         👥 Building character prompt for '{subject}'")
        
        if not results:
            return self.prompt_library.build_comprehensive_prompt(subject, [])

        # The top result is our best candidate for the primary character.
        primary_candidate = results[0]
        
        # Verify the candidate's title matches the subject to ensure relevance.
        if subject.lower() in primary_candidate.get('title', '').lower():
            # Confirmed: the top result is the character we're looking for.
            primary_character_info = primary_candidate
            known_associates = results[1:]
            
            return self.prompt_library.build_character_with_associates_prompt(
                primary_character_info,
                known_associates
            )
        else:
            # The top result doesn't match, so we can't be confident.
            # Return a "not found" response to avoid presenting incorrect information.
            print(f"         ⚠️  Top result '{primary_candidate.get('title')}' did not match subject '{subject}'.")
            return self.prompt_library.build_comprehensive_prompt(subject, []) 