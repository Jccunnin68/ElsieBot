"""
AI Knowledge - Database and Content Processing
==============================================

This package contains the core components for interacting with the database
and processing large volumes of content using LLMs.

Components:
- database_controller.py: Manages all connections and operations with the database.
- knowledge_engine.py: A powerful LLM-based engine for summarizing and
  post-processing large query results before they are used for context.
"""

from .database_controller import get_db_controller
from .knowledge_engine import get_knowledge_engine, should_process_data

__all__ = [
    # Database access
    'get_db_controller',

    # Knowledge processing engine
    'get_knowledge_engine',
    'should_process_data',
] 