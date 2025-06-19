"""
Logic Engine for Query Disambiguation with Smart Failover
=========================================================

This module provides a dedicated interface for using a local LLM to perform
specific, narrowly-defined tasks. Its primary role in the agentic architecture
is to determine the correct database category for a general user query,
with smart failover to general search if no results are found.
"""

from typing import List, Dict, Optional
import os
import google.generativeai as genai

class LogicEngine:
    """
    An engine that uses an LLM for performing specific reasoning tasks with smart failover.
    """
    def __init__(self, model_name="gemini-2.0-flash-lite"):
        """
        Initializes the Logic Engine.

        Args:
            model_name: The name of the Gemini model to use.
        """
        self.api_key = os.getenv("GEMMA_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        self.db_controller = None  # Will be set by dependency injection
        print(f"✓ Logic Engine initialized for model: {self.model_name}")

    def set_database_controller(self, db_controller):
        """
        Sets the database controller for smart failover checks.
        
        Args:
            db_controller: Instance of FleetDatabaseController
        """
        self.db_controller = db_controller
        print(f"✓ Logic Engine connected to database controller")

    def determine_query_category_with_failover(self, query: str, available_categories: List[str]) -> Dict[str, any]:
        """
        Uses the LLM to determine the most relevant category for a user's query,
        then performs a quick verification search. If no results are found,
        falls back to general search.

        Args:
            query: The user's natural language query.
            available_categories: A list of all possible categories from the database.

        Returns:
            Dictionary containing:
            - category: The determined category (may be 'General' after failover)
            - original_category: The original LLM-determined category
            - failover_used: Boolean indicating if failover was triggered
            - reason: Explanation of the decision
        """
        # Handle case where no categories are available from database
        if not available_categories or len(available_categories) == 0:
            print(f"   ⚠️  No categories available from database - using default category set")
            # Use common Star Trek/Fleet categories as fallback
            available_categories = [
                'Characters', 'Ships', 'Logs', 'Planets', 'Species', 'Technology',
                'Organizations', 'Governments', 'Episodes', 'General'
            ]
        
        # Step 1: Get initial category determination from LLM
        original_category = self.determine_query_category(query, available_categories)
        
        # Step 2: If no database controller available, return original category
        if not self.db_controller:
            print(f"   ⚠️  No database controller available - skipping failover check")
            return {
                'category': original_category,
                'original_category': original_category,
                'failover_used': False,
                'reason': 'No database controller for verification'
            }
        
        # Step 3: Perform quick verification search if category is specific
        if original_category.lower() != 'general':
            print(f"   🔍 SMART FAILOVER: Verifying category '{original_category}' has results...")
            
            # Use enhanced category matching for more flexible searches
            verification_results = self.db_controller.search_with_category_matching(
                query=query,
                target_category=original_category,
                limit=3
            )
            
            if verification_results and len(verification_results) > 0:
                print(f"   ✅ VERIFICATION PASSED: Found {len(verification_results)} results for '{original_category}'")
                return {
                    'category': original_category,
                    'original_category': original_category,
                    'failover_used': False,
                    'reason': f'Category verified with {len(verification_results)} matches'
                }
            else:
                print(f"   🔄 FAILOVER TRIGGERED: No results for '{original_category}', falling back to general search")
                return {
                    'category': 'General',
                    'original_category': original_category,
                    'failover_used': True,
                    'reason': f'No results found for {original_category}, using general search'
                }
        else:
            # Already determined as general, no failover needed
            return {
                'category': original_category,
                'original_category': original_category,
                'failover_used': False,
                'reason': 'Originally categorized as general'
            }

    def determine_query_category(self, query: str, available_categories: List[str]) -> str:
        """
        Uses the LLM to determine the most relevant category for a user's query.

        Args:
            query: The user's natural language query.
            available_categories: A list of all possible categories from the database.

        Returns:
            The single most relevant category name as a string.
        """
        prompt = self._build_category_selection_prompt(query, available_categories)

        print(f"   🧠 LLM aAbient: Determining category for query '{query}'")
        
        response = self.model.generate_content(prompt)
        category = response.text.strip()
        
        print(f"   🤖 LLM Returned Category: '{category}'")
        
        return category

    def _build_category_selection_prompt(self, query: str, available_categories: List[str]) -> str:
        """
        Constructs the prompt for the LLM to select a category.
        """
        # Format the category list for the prompt
        category_list_str = "\\n".join(f"- {cat}" for cat in available_categories)

        # More explicit rules and examples
        rules_and_examples = (
            "**CRITICAL INSTRUCTIONS:**\\n"
            "1.  Your only job is to select the single best category for the user's query from the list provided.\\n"
            "2.  You MUST respond with ONLY the full name of the chosen category. Do not add any explanation or extra text.\\n"
            "3.  If no category is a good fit, you MUST respond with 'General'.\\n"
            "4.  Do not invent or create a new category. Only select from the list provided.\\n\\n"
            "**EXAMPLES:**\\n"
            "- User Query: 'tell me about the stardancer' -> Your Response: 'Ships'\\n"
            "- User Query: 'who is jackson riens' -> Your Response: 'Characters'\\n"
            "- User Query: 'latest logs for the adagio' -> Your Response: 'Logs'\\n"
            "- User Query: 'what happened on beryxia' -> Your Response: 'Planets'\\n"
            "- User Query: 'what are beryxians' -> Your Response: 'Species'\\n"
            "- User Query: 'what is the federation' -> Your Response: 'General'\\n"
            "- User Query: 'who is talia' -> Your Response: 'Characters'\\n"
            "- User Query: 'what is the stardancer' -> Your Response: 'Ships'\\n"
            "- User Query: 'tell me about jackson riens' -> Your Response: 'character'\\n"
            
        )

        prompt = f'''
You are a database routing specialist. Your task is to analyze a user's query and select the single most appropriate data category from a provided list.

{rules_and_examples}

---
**USER QUERY:**
"{query}"

**AVAILABLE CATEGORIES:**
{category_list_str}

**YOUR RESPONSE (Category Name Only):**
'''
        return prompt.strip()

# Singleton instance of the LogicEngine
_logic_engine = None

def get_logic_engine():
    """
    Provides a global singleton instance of the LogicEngine.
    """
    global _logic_engine
    if _logic_engine is None:
        _logic_engine = LogicEngine()
    return _logic_engine