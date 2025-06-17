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

# Note: In a real implementation, this would use the Google Generative AI SDK
# from google.generativeai as genai

class LogicEngine:
    """
    An engine that uses an LLM for performing specific reasoning tasks.
    """
    def __init__(self, model_name="gemini-1.5-flash-latest"):
        """
        Initializes the Logic Engine.

        Args:
            model_name: The name of the Gemini model to use.
        """
        # In a real implementation, you would configure the API key here
        # self.api_key = os.getenv("GEMINI_API_KEY")
        # genai.configure(api_key=self.api_key)
        # self.model = genai.GenerativeModel(model_name)
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
        # --- LLM Call (Mocked for now) ---
        # In a real implementation, the following lines would be replaced
        # with an actual call to the Gemini API.
        # response = self.model.generate_content(prompt)
        # category = response.text.strip()
        
        # Mocked response: For now, we'll return the first category that appears in the query
        # This is a placeholder to allow the architecture to be built.
        query_lower = query.lower()
        for cat in available_categories:
            if cat.lower() in query_lower:
                print(f"   🤖 [MOCK] LLM selected category: {cat}")
                return cat
        
        # If no direct match, return a default or the first category for testing
        mock_category = available_categories[0] if available_categories else "General"
        print(f"   🤖 [MOCK] LLM defaulted to category: {mock_category}")
        return mock_category
        # --- End Mock ---
        
        # return category

    def _build_category_selection_prompt(self, query: str, available_categories: List[str]) -> str:
        """
        Constructs the prompt for the LLM to select a category.
        """
        category_list = "\n".join(f"- {category}" for category in available_categories)

        prompt = f"""
You are an intelligent data routing agent. Your task is to analyze a user's query and select the single most appropriate data category from a provided list.

**Instructions:**
1.  Read the user's query carefully to understand their intent.
2.  Review the list of available data categories.
3.  Choose the one category that best matches the user's query.
4.  Your response MUST BE ONLY the name of the chosen category and nothing else.

**User Query:**
"{query}"

**Available Categories:**
{category_list}

**Your Response (Category Name Only):**
"""
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