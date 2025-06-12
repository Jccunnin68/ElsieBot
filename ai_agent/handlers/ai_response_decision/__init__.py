"""
AI Response Decision - Decision Logic Package
============================================

This package handles response decision-making logic, determining when and how
Elsie should respond to different types of messages. It extracts the strategy
and decision logic from ai_handler.py.

Components:
- strategy_engine.py: Core strategy determination logic
- response_decision.py: ResponseDecision dataclass and decision extraction
- context_detection.py: Personality and context detection logic

Usage:
    from handlers.ai_response_decision import extract_response_decision, ResponseDecision
    
    decision = extract_response_decision(message, history, channel_context)
    if decision.needs_ai_generation:
        # Proceed with AI generation
    else:
        # Use pre-generated response
        return decision.pre_generated_response
"""

from .response_decision import ResponseDecision
from .strategy_engine import determine_response_strategy
from .context_detection import detect_general_personality_context, detect_who_elsie_addressed
from .decision_extractor import extract_response_decision

__all__ = [
    # Core decision classes
    'ResponseDecision',
    
    # Strategy determination
    'determine_response_strategy',
    
    # Context detection
    'detect_general_personality_context',
    'detect_who_elsie_addressed',
    
    # Decision extraction
    'extract_response_decision'
] 