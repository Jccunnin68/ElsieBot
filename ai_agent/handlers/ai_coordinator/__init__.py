"""
AI Coordinator - Response Coordination Package
=============================================

This package handles the main coordination logic for AI responses,
including the main entry point (coordinate_response) and response
tracking logic.

Components:
- response_coordinator.py: Main coordination entry point
- tracking_manager.py: Response tracking and state management
- ai_engine.py: AI generation engine (Gemma API calls)

Usage:
    from handlers.ai_coordinator import coordinate_response
    
    response = coordinate_response(message, history, channel_context)
"""

from .response_coordinator import coordinate_response
from .ai_engine import generate_ai_response_with_decision

__all__ = [
    # Main coordination
    'coordinate_response',
    
    # AI generation
    'generate_ai_response_with_decision'
] 