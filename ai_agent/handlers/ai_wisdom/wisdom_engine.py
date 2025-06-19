"""
Wisdom Engine for Prompt Orchestration
======================================

This module contains the new WisdomEngine, which orchestrates
the prompt generation process. It uses the PromptLibrary to construct
prompts and then executes them via LLM to generate responses.
"""

import time
from typing import Dict, Any
import google.generativeai as genai
from config import GEMMA_API_KEY
from handlers.ai_wisdom.prompt_builder import PromptLibrary

class WisdomEngine:
    """Orchestrates prompt generation using a strategy and the PromptLibrary, then executes via LLM."""

    LLM_MODEL_NAME = 'gemini-2.0-flash-lite'
    MAX_RETRIES = 3

    def __init__(self):
        self.prompt_library = PromptLibrary()
        self.client = self._initialize_gemini_client()

    def _initialize_gemini_client(self):
        """Initializes the Gemini client."""
        try:
            genai.configure(api_key=GEMMA_API_KEY)
            model = genai.GenerativeModel(self.LLM_MODEL_NAME)
            print(f"✅ WisdomEngine initialized with {self.LLM_MODEL_NAME}")
            return model
        except Exception as e:
            print(f"⚠️  Failed to initialize Gemini client for WisdomEngine: {e}")
            return None

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
        """Builds the appropriate prompt based on the strategy."""
        
        # Check for disambiguation case first
        if results and results[0].get('type') == 'disambiguation':
            print(f"         🔀 DISAMBIGUATION DETECTED: Building disambiguation prompt")
            search_term = results[0].get('search_term', subject)
            matches = results[0].get('matches', [])
            return self.prompt_library.build_character_disambiguation_prompt(search_term, matches)
        
        # Determine if this is a character query by inspecting the results.
        # Check the categories array from the database results
        is_character_query = False
        if results:
            categories = results[0].get('categories', [])
            if categories:
                # Convert categories to lowercase for case-insensitive matching
                categories_lower = [cat.lower() for cat in categories]
                # Check if any category contains character-related terms
                character_indicators = ['characters', 'npcs', 'personnel', 'crew']
                is_character_query = any(
                    any(indicator in category for indicator in character_indicators) 
                    for category in categories_lower
                )
                
                if is_character_query:
                    print(f"         👤 CHARACTER QUERY DETECTED: categories={categories}")

        if is_character_query and results:
            # If the top result is a character, use the specialized prompt.
            return self._build_character_prompt(subject, results)
        
        if strategy.get('approach') == 'logs':
            temporal_type = strategy.get('temporal_type', 'latest')
            return self.prompt_library.build_logs_prompt(subject, results, temporal_type)

        # For everything else, use the comprehensive prompt.
        print(f"         📚 COMPREHENSIVE QUERY: Using general prompt")
        return self.prompt_library.build_comprehensive_prompt(subject, results)

    def _execute_prompt_via_llm(self, prompt: str, approach: str) -> str:
        """Executes the built prompt via LLM and returns the response."""
        if not self.client:
            print(f"         ❌ WisdomEngine LLM client not available. Returning raw prompt.")
            return prompt

        print(f"         🤖 Executing {approach} prompt via LLM...")
        print(f"         📊 Prompt length: {len(prompt)} characters")
        
        # DEBUG: Show first 200 chars of prompt being processed
        print(f"         📝 DEBUG - Prompt preview: {prompt[:200]}...")

        for attempt in range(self.MAX_RETRIES):
            try:
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=12000,
                    temperature=0.6,
                    candidate_count=1
                )
                
                response = self.client.generate_content(prompt, generation_config=generation_config)
                response_text = response.text.strip()
                
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