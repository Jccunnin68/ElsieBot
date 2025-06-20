"""
AI Emotion - Emotional Analysis and Response Generation
=======================================================

This package handles the emotional analysis of user messages and can
generate emotionally-aware responses, including poetic or mock responses.

New Architecture:
- emotion_engine.py: A dedicated LLM-powered engine for all nuanced
  emotional analysis. Replaces the old heuristic-based modules.

Core Components:
- poetic_responses.py: Generates esoteric, poetic responses.
- greetings.py: Handles simple greetings.
- drink_menu.py: Provides mock responses for bar service.
- personality_contexts.py: Provides personality information (mostly deprecated).
"""

from .poetic_responses import should_trigger_poetic_circuit, get_poetic_response
from .mock_responses import get_mock_response

__all__ = [
    # Existing Response Generators
    'should_trigger_poetic_circuit',
    'get_poetic_response',
    'get_mock_response',
]

# REMOVED: Global accessor functions moved to service_container
# Use: from handlers.service_container import get_emotion_engine 