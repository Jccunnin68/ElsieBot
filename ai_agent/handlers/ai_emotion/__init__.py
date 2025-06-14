"""
AI Emotion - Enhanced Emotional Intelligence for Elsie
=====================================================

This package provides enhanced emotional intelligence capabilities for Elsie,
including emotional support detection, context sensitivity analysis, and
priority resolution for emotional vs. group addressing conflicts.

Key modules:
- emotional_analysis: Core emotional analysis and support detection
- context_sensitivity: Context-aware pattern recognition
- priority_resolution: Confidence-based priority resolution
- conversation_emotions: Conversation-level emotional intelligence
"""

# Import key functions for easier access
try:
    from .emotional_analysis import (
        detect_emotional_support_opportunity,
        analyze_emotional_tone_enhanced,
        EmotionalTone,
        EmotionalContext
    )
    
    from .context_sensitivity import (
        distinguish_group_vs_contextual,
        resolve_addressing_conflict,
        AddressingType
    )
    
    from .priority_resolution import (
        resolve_emotional_vs_group_conflict,
        create_emotional_support_candidate,
        create_group_addressing_candidate,
        ResponseType,
        ResponsePriority
    )
    
    from .conversation_emotions import (
        ConversationEmotionalIntelligence,
        ConversationMood,
        EmotionalRelationship
    )
    
except ImportError as e:
    # Graceful fallback if modules aren't all available
    print(f"Warning: Some ai_emotion modules not available: {e}")

__version__ = "1.0.0"
__author__ = "Elsie AI Enhancement Team"

from .mock_responses import get_mock_response, should_use_mock_response
from .personality_contexts import detect_mock_personality_context, is_simple_chat
from .drink_menu import handle_drink_request, get_menu_response
from .greetings import handle_greeting, handle_farewell
from .poetic_responses import get_poetic_response, should_trigger_poetic_circuit, get_reset_response, get_simple_continuation_response

__all__ = [
    'get_mock_response',
    'should_use_mock_response',
    'detect_mock_personality_context',
    'is_simple_chat',
    'handle_drink_request',
    'get_menu_response',
    'handle_greeting',
    'handle_farewell',
    'get_poetic_response',
    'should_trigger_poetic_circuit',
    'get_reset_response',
    'get_simple_continuation_response'
] 