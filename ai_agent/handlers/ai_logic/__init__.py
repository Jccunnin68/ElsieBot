"""
AI Logic - Response Decision and Context Analysis
=================================================

This package handles the core logic for determining appropriate responses
and analyzing conversation context for the AI agent.

Components:
- response_decision_engine.py: Main response decision logic
- context_detection.py: Post-response analysis and prompt builders
- query_detection.py: Query pattern detection
- response_router.py: Response routing logic
- roleplay_handler.py: Roleplay-specific logic
- standard_handler.py: Standard conversation logic
"""

from .response_decision_engine import ResponseDecision
from .context_detection import (
    detect_who_elsie_addressed,
    detect_who_elsie_addressed_alt,
    create_personality_context_prompt,
    create_context_analysis_prompt
)
from .query_detection import detect_query_type_with_conflicts
from .response_router import route_message_to_handler
from .roleplay_handler import handle_roleplay_message
from .standard_handler import handle_standard_message

__all__ = [
    # Response decision making
    'ResponseDecision',
    
    # Post-response analysis and prompt building
    'detect_who_elsie_addressed',
    'detect_who_elsie_addressed_alt',
    'create_personality_context_prompt',
    'create_context_analysis_prompt',
    
    # Query detection
    'detect_query_type_with_conflicts',
    
    # Response routing
    'route_message_to_handler',
    'handle_roleplay_message',
    'handle_standard_message',
] 