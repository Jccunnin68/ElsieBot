"""
Structured Content Retriever
============================

This module is the data-fetching component of the new agentic architecture.
It takes a structured query object from the StructuredQueryDetector and
retrieves the relevant content from the database, orchestrating with the
LLMInterface when necessary for general queries.
"""

from typing import Dict, Any, List
from database_controller import get_db_controller
from ai_agent.handlers.ai_logic.llm_interface import get_llm_interface

class StructuredContentRetriever:
    """
    Retrieves content from the database based on a structured query object.
    """
    def __init__(self):
        self.db_controller = get_db_controller()
        self.llm_interface = get_llm_interface()

    def get_content(self, structured_query: Dict[str, Any]) -> List[Dict]:
        """
        Main method to fetch content based on the structured query.

        Args:
            structured_query: A dictionary from StructuredQueryDetector.

        Returns:
            A list of matching records from the database.
        """
        query_type = structured_query.get('type')
        print(f"   📚 Structured Content Retriever: Handling type '{query_type}'")

        match query_type:
            case 'explicit':
                return self._handle_explicit_search(structured_query)
            case 'logs':
                return self._handle_log_search(structured_query)
            case 'ship' | 'character' | 'species' | 'planet':
                return self._handle_typed_search(structured_query)
            case 'general':
                return self._handle_general_query(structured_query)
            case _:
                print(f"   ⚠️  Unknown query type in content retriever: {query_type}")
                return []

    def _handle_explicit_search(self, query: Dict[str, str]) -> List[Dict]:
        """Handles: search for "term" in "category" """
        term = query.get('term')
        category = query.get('category')
        return self.db_controller.search(query=term, categories=[category], limit=10)

    def _handle_log_search(self, query: Dict[str, Any]) -> List[Dict]:
        """Handles: logs for <ship/character> [latest|first|recent]"""
        subject = query.get('subject')
        modifier = query.get('modifier')
        
        order_by_map = {
            'latest': 'chronological',
            'first': 'id_asc',
            'recent': 'chronological'
        }
        limit_map = {
            'latest': 1,
            'first': 1,
            'recent': 3
        }

        order_by = order_by_map.get(modifier, 'chronological')
        limit = limit_map.get(modifier, 3)
        
        # We assume 'Logs' is a valid category. This could be made more robust.
        log_categories = self.db_controller.get_log_categories()
        
        return self.db_controller.search(
            query=subject, 
            categories=log_categories, 
            limit=limit, 
            order_by=order_by
        )

    def _handle_typed_search(self, query: Dict[str, str]) -> List[Dict]:
        """Handles: ship <name>, character <name>, etc."""
        term = query.get('term')
        query_type = query.get('type')

        category_map = {
            'ship': self.db_controller.get_ship_categories,
            'character': self.db_controller.get_character_categories,
            'species': lambda: ['Species', 'Race'], # Assuming these categories exist
            'planet': lambda: ['Planet'] # Assuming this category exists
        }

        # Get the categories associated with the query type
        category_func = category_map.get(query_type)
        categories = category_func() if category_func else [query_type.title()]

        return self.db_controller.search(query=term, categories=categories, limit=1)

    def _handle_general_query(self, query: Dict[str, Any]) -> List[Dict]:
        """
        Handles a general query by using the LLM to find the best category.
        """
        user_query = query.get('query')
        all_categories = self.db_controller.get_all_categories()

        if not all_categories:
            print("   ⚠️ No categories found in database. Performing standard search.")
            return self.db_controller.search(query=user_query, limit=5)
            
        # Use the LLM to determine the best category
        chosen_category = self.llm_interface.determine_query_category(user_query, all_categories)
        
        print(f"   🔍 General query routed to category '{chosen_category}' by LLM.")
        
        # Search within that category
        return self.db_controller.search(query=user_query, categories=[chosen_category], limit=5)

# Singleton instance
_content_retriever = None

def get_structured_content_retriever():
    """
    Provides a global singleton instance of the StructuredContentRetriever.
    """
    global _content_retriever
    if _content_retriever is None:
        _content_retriever = StructuredContentRetriever()
    return _content_retriever 