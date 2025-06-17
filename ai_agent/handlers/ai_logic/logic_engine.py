"""
Logic Engine for Query Disambiguation
======================================

This module provides a dedicated interface for using a local LLM to perform
specific, narrowly-defined tasks. Its primary role in the agentic architecture
is to determine the correct database category for a general user query,
avoiding the need for complex heuristic logic.
"""

from typing import List, Dict
import os
import google.generativeai as genai

class LogicEngine:
    """
    An engine that uses an LLM for performing specific reasoning tasks.
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
        print(f"✓ Logic Engine initialized for model: {self.model_name}")

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
            "3.  If no category is a good fit, you MUST respond with 'General'.\\n\\n"
            "**EXAMPLES:**\\n"
            "- User Query: 'tell me about the stardancer' -> Your Response: 'Ships'\\n"
            "- User Query: 'who is jackson riens' -> Your Response: 'Characters'\\n"
            "- User Query: 'latest logs for the adagio' -> Your Response: 'Logs'\\n"
            "- User Query: 'what happened on beryxia' -> Your Response: 'Planets'\\n"
            "- User Query: 'what are beryxians' -> Your Response: 'Species'\\n"
            "- User Query: 'what is the federation' -> Your Response: 'General'\\n"
            "- User Query: 'who is talia' -> Your Response: 'Characters'\\n"
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