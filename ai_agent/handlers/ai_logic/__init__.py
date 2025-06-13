"""
AI Logic - Decision Logic Package (REFACTORED)
==============================================

This package handles response decision-making with clean mode separation:

NEW ARCHITECTURE:
- response_router.py: Main entry point - routes by roleplay mode
- roleplay_handler.py: ALL roleplay mode responses (character-aware, bar service)
- non_roleplay_handler.py: ALL non-roleplay mode responses (simple, factual)
- response_decision.py: ResponseDecision dataclass
- decision_extractor.py: Simplified entry point (just calls router)

LEGACY (kept for compatibility):
- strategy_engine.py: Legacy strategy logic (being phased out)
- context_detection.py: Legacy context detection

Usage:
    from handlers.ai_logic import extract_response_decision, ResponseDecision
    
    decision = extract_response_decision(message, history, channel_context)
    # Router automatically handles roleplay vs non-roleplay mode
"""

from .response_decision import ResponseDecision
from .decision_extractor import extract_response_decision
from .response_router import route_message_to_handler

# Legacy imports (for compatibility)
try:
    from .strategy_engine import determine_response_strategy
    from .context_detection import detect_general_personality_context, detect_who_elsie_addressed
except ImportError:
    # Handle missing legacy modules gracefully
    pass

__all__ = [
    # NEW ARCHITECTURE - Main entry points
    'ResponseDecision',
    'extract_response_decision', 
    'route_message_to_handler',
    
    # Legacy (for compatibility)
    'determine_response_strategy',
    'detect_general_personality_context',
    'detect_who_elsie_addressed',
] 