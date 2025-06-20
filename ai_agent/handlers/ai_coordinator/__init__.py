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

__all__ = [
    # Main coordination
    'coordinate_response'
]

# REMOVED: generate_ai_response_with_decision is now obsolete
# Use service_container.get_ai_engine().generate_response_with_decision() instead 