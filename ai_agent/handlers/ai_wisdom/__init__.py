"""
AI Wisdom - Context Generation and Content Retrieval
======================================================

This package is responsible for generating the context that the AI uses
to form its responses and for retrieving content from the database using
the new agentic architecture.

Components:
- context_coordination_service.py: Service for context generation routing.
- roleplay_context_builder.py: Manages context for immersive roleplay scenarios.
- structured_content_retriever.py: The unified data retrieval and processing module.
- prompt_builder.py: Prompt building service and library.
- wisdom_engine.py: Core wisdom processing engine.
"""

from .structured_content_retriever import StructuredContentRetriever
from .roleplay_context_builder import RoleplayContextBuilder
from .prompt_builder import PromptLibrary
from .wisdom_engine import WisdomEngine

__all__ = [
    # Agentic content retrieval
    'StructuredContentRetriever',

    # Context Builders / Engines
    'RoleplayContextBuilder',
    'PromptLibrary',
    'WisdomEngine',
]

# Use service container for context coordination:
# from handlers.service_container import get_context_coordination_service
# Use: from handlers.service_container import get_knowledge_engine 