"""
AI Logic Module
===============

This module contains the core decision-making logic for Elsie's AI system.
It handles response routing, decision extraction, and query processing.

CURRENT MODULES:
- response_router.py: Main message routing and decision coordination
- response_decision_engine.py: Enhanced contextual decision making

- non_roleplay_handler.py: Non-roleplay message handling
- query_detection.py: Query type detection and analysis
- log_patterns.py: Log-specific pattern matching
- log_processor.py: Log content processing
- context_detection.py: Context detection utilities

The system uses an enhanced pathway for roleplay scenarios with sophisticated
contextual intelligence and emotional analysis.
"""

# Core imports
from .response_router import route_message_to_handler
from .response_decision_engine import create_response_decision_engine
from .response_decision import ResponseDecision

from .non_roleplay_handler import handle_non_roleplay_message

# Utility imports
try:
    from .query_detection import *
    from .context_detection import *
except ImportError as e:
    print(f"Warning: Could not import some ai_logic utilities: {e}")

# Context detection utilities
from .context_detection import (
    detect_who_elsie_addressed,
    detect_general_personality_context
)

__all__ = [
    # NEW ARCHITECTURE - Main entry points
    'ResponseDecision',
 
    'route_message_to_handler',
    
    # Legacy (for compatibility)
    'detect_general_personality_context',
    'detect_who_elsie_addressed',
] 