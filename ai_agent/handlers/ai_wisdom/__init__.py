"""
AI Wisdom - Context Generation Package
========================================

This package is responsible for generating the context that the AI uses
to form its responses. It separates logic for roleplay and non-roleplay
scenarios, providing the necessary information and instructions for each.

The primary entry point is `get_context_for_strategy`, which routes
requests to the appropriate context builder based on the determined
response strategy.

Components:
- context_coordinator.py: The main router for context generation.
- non_roleplay_context_builder.py: Handles all standard, OOC, and database queries.
- roleplay_context_builder.py: Manages context for immersive roleplay scenarios.
- content_retriever.py: The unified data retrieval and processing module.
- log_patterns.py: Supporting patterns for log processing.
"""

from .context_coordinator import get_context_for_strategy

__all__ = [
    'get_context_for_strategy'
] 