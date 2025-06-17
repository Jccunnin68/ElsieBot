"""
AI Wisdom - Context Generation and Content Retrieval
======================================================

This package is responsible for generating the context that the AI uses
to form its responses and for retrieving content from the database using
the new agentic architecture.

Components:
- context_coordinator.py: The main router for context generation.
- standard_context_builder.py: Handles all standard, OOC, and database queries.
- roleplay_context_builder.py: Manages context for immersive roleplay scenarios.
- structured_content_retriever.py: The unified data retrieval and processing module.
- llm_query_processor.py: Post-processes large query results using an LLM.
- log_patterns.py: Supporting patterns for log processing.
"""

from .context_coordinator import get_context_for_strategy
from .structured_content_retriever import StructuredContentRetriever
from .llm_query_processor import get_llm_processor, should_process_data
from .roleplay_context_builder import RoleplayContextBuilder
from .prompt_builder import PromptLibrary
from .structured_context_builder import StructuredContextBuilder

__all__ = [
    # Main entry point for context generation
    'get_context_for_strategy',

    # Agentic content retrieval
    'StructuredContentRetriever',

    # Context Builders
    'RoleplayContextBuilder',
    'PromptLibrary',
    'StructuredContextBuilder',

    # LLM Processing
    'get_llm_processor',
    'should_process_data',
] 