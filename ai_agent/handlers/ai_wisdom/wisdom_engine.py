"""
Wisdom Engine for Prompt Orchestration
======================================

This module contains the new WisdomEngine, which orchestrates
the prompt generation process. It uses the PromptLibrary to construct
prompts and then executes them via LLM to generate responses.
"""

import time
from typing import Dict, Any
from config import OLLAMA_WISDOM_MODEL, OLLAMA_WISDOM_URL
from handlers.ai_wisdom.prompt_builder import PromptLibrary
from handlers.local_gemma import LocalGemma

class WisdomEngine:
    """Orchestrates prompt generation using a strategy and the PromptLibrary, then executes via LLM."""

    MAX_RETRIES = 1

    def __init__(self):
        self.prompt_library = PromptLibrary()
        self.client = LocalGemma(OLLAMA_WISDOM_URL, OLLAMA_WISDOM_MODEL)
        if self.client.configured:
            print(f"✅ WisdomEngine initialized with {OLLAMA_WISDOM_MODEL} at {OLLAMA_WISDOM_URL}")
        else:
            print("⚠️  WisdomEngine local model is not configured")

    def build_context_for_strategy(self, strategy: Dict[str, Any], user_message: str) -> str:
        """
        Builds a prompt using the PromptLibrary, then executes it via LLM to generate a response.

        This method acts as a router, calling the appropriate method from the
        PromptLibrary based on the 'approach' defined in the strategy, then processes
        the prompt through an LLM to get the actual response content.
        """
        approach = strategy.get('approach', 'comprehensive')
        print(f"         🎯 WISDOM ENGINE: Processing approach '{approach}'")
        
        # Extract common data from the strategy
        subject = strategy.get('subject') or user_message
        results = strategy.get('results', [])

        # Step 1: Build the prompt using PromptLibrary
        prompt = self._build_prompt_for_strategy(strategy, user_message, subject, results)
        
        # Step 2: Execute the prompt via LLM and return the response
        return self._execute_prompt_via_llm(prompt, approach)

    def _build_prompt_for_strategy(self, strategy: Dict[str, Any], user_message: str, subject: str, results: list) -> str:
        """
        Builds the appropriate prompt based on the strategy.
        """
        print(f"         🎯 WISDOM ENGINE: Building prompt for approach '{strategy.get('approach')}'")
        print(f"         📊 Working with {len(results)} results")
        
        if strategy.get('approach') == 'logs':
            temporal_type = strategy.get('temporal_type', 'latest')
            
            # Check if this is a list query
            if results and results[0].get('is_list_item'):
                print(f"         📜 LIST QUERY DETECTED: Building log list prompt")
                return self.prompt_library.build_log_list_prompt(subject, results)
            
            # NEW: Check for multi-log queries by looking at BOTH results AND strategy
            # This is crucial when database connection fails and we have no results
            force_historical_from_results = results and any(result.get('use_historical_summary') for result in results)
            force_historical_from_strategy = any(strategy.get(key, False) for key in ['force_historical_summary', 'is_multi_log'])
            
            print(f"         🔍 MULTI-LOG DETECTION:")
            print(f"         - force_historical_from_results: {force_historical_from_results}")
            print(f"         - force_historical_from_strategy: {force_historical_from_strategy}")
            
            if force_historical_from_results or force_historical_from_strategy:
                if force_historical_from_strategy:
                    print(f"         🔢 MULTI-LOG HISTORICAL SUMMARY: Detected from strategy (works even without DB results)")
                else:
                    print(f"         📚 HISTORICAL SUMMARY DETECTED: Detected from results")
                return self.prompt_library.build_historical_summary_prompt(subject, results, temporal_type)
            
            # Default to narrative format for single logs
            else:
                print(f"         📖 NARRATIVE LOG DETECTED: Building standard log prompt")
                return self.prompt_library.build_logs_prompt(subject, results, temporal_type)

        # For everything else, use the comprehensive prompt.
        print(f"         📚 COMPREHENSIVE QUERY: Using general prompt")
        return self.prompt_library.build_comprehensive_prompt(subject, results)

    def _execute_prompt_via_llm(self, prompt: str, approach: str) -> str:
        """Executes the built prompt via LLM and returns the response."""
        if not self.client.configured:
            print(f"         ❌ WisdomEngine LLM client not available. Returning raw prompt.")
            return prompt

        print(f"         🤖 Executing {approach} prompt via LLM...")
        print(f"         📊 Prompt length: {len(prompt)} characters")
        
        # DEBUG: Show first 200 chars of prompt being processed
        print(f"         📝 DEBUG - Prompt preview: {prompt[:200]}...")

        for attempt in range(self.MAX_RETRIES):
            try:
                response_text = self.client.generate(prompt, temperature=0.3, max_tokens=8192)
                
                if response_text:
                    print(f"         ✅ WisdomEngine successfully generated {len(response_text)} character response")
                    # DEBUG: Show first 300 chars and last 300 chars of response
                    print(f"         🔍 DEBUG - Response start: {response_text[:300]}...")
                    if len(response_text) > 600:
                        print(f"         🔍 DEBUG - Response end: ...{response_text[-300:]}")
                    return response_text
                else:
                    print(f"         ⚠️  WisdomEngine returned empty response on attempt {attempt + 1}")
            
            except Exception as e:
                print(f"         ❌ WisdomEngine LLM call failed on attempt {attempt + 1}: {e}")

            if attempt < self.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

        print(f"         ❌ All WisdomEngine LLM attempts failed. Returning raw prompt as fallback.")
        return prompt

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
        candidate_title = primary_candidate.get('title', '').lower()
        subject_lower = subject.lower()
        
        # More flexible matching - check if subject words are in the title
        subject_words = subject_lower.split()
        title_contains_subject = any(word in candidate_title for word in subject_words if len(word) > 2)
        
        # Also check reverse - if title words are in subject (for cases like "Captain Marcus Blaine")
        title_words = candidate_title.split()
        subject_contains_title = any(word in subject_lower for word in title_words if len(word) > 2)
        
        is_match = title_contains_subject or subject_contains_title
        
        print(f"         🔍 Character matching: '{subject}' vs '{primary_candidate.get('title', '')}'")
        print(f"         📊 Match result: {is_match} (title_contains_subject: {title_contains_subject}, subject_contains_title: {subject_contains_title})")
        
        if is_match:
            # Confirmed: the top result is the character we're looking for.
            primary_character_info = primary_candidate
            known_associates = results[1:]
            
            print(f"         ✅ CHARACTER MATCH CONFIRMED: Using character prompt with {len(known_associates)} associates")
            return self.prompt_library.build_character_with_associates_prompt(
                primary_character_info,
                known_associates
            )
        else:
            # The top result doesn't match, so we can't be confident.
            # Return a "not found" response to avoid presenting incorrect information.
            print(f"         ❌ CHARACTER MATCH FAILED: Top result '{primary_candidate.get('title')}' did not match subject '{subject}'.")
            return self.prompt_library.build_comprehensive_prompt(subject, []) 