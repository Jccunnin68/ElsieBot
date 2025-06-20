"""
AI Knowledge - Database and Content Processing
==============================================

This package contains the core components for interacting with the database
and processing large volumes of content using LLMs.

Components:
- database_controller.py: Manages all connections and operations with the database.
- knowledge_engine.py: An LLM-based engine for cleaning raw Discord logs.
"""

__all__ = [
    # REMOVED: Global accessor functions moved to service_container
    # Use: from handlers.service_container import get_db_controller, get_knowledge_engine
] 