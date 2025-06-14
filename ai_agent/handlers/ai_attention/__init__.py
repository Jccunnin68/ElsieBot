"""
AI Attention - Roleplay State Management Package
===============================================

This package handles all roleplay detection, state management, and conversation tracking.
It manages character interactions, turn-based conversation flow, and roleplay session lifecycle.

Components:
- roleplay_detection.py: Core detection engine with confidence scoring
- dgm_handler.py: Deputy Game Master post handling and scene management
- character_tracking.py: Character name extraction and validation
- channel_restrictions.py: Channel permission and restriction logic
- state_manager.py: RoleplayStateManager class for session tracking
- response_logic.py: Decision logic for when Elsie should respond
- exit_conditions.py: Roleplay exit condition detection

Usage:
    from handlers.ai_attention import detect_roleplay_triggers, RoleplayStateManager
    
    is_rp, confidence, triggers = detect_roleplay_triggers(message, channel_context)
    state_manager = RoleplayStateManager()
"""

from .roleplay_detection import detect_roleplay_triggers
from .dgm_handler import check_dgm_post, extract_characters_from_dgm_post
from .character_tracking import (
    extract_character_names_from_emotes, 
    is_valid_character_name,
    extract_addressed_characters,
    extract_current_speaker
)
from .channel_restrictions import is_roleplay_allowed_channel
from .state_manager import RoleplayStateManager, get_roleplay_state
from .response_logic import (
    check_subtle_bar_interaction,
    check_if_other_character_addressed,
    extract_drink_from_emote
)
from .exit_conditions import detect_roleplay_exit_conditions

__all__ = [
    # Core detection
    'detect_roleplay_triggers',
    
    # DGM handling
    'check_dgm_post',
    'extract_characters_from_dgm_post',
    
    # Character tracking
    'extract_character_names_from_emotes',
    'is_valid_character_name', 
    'extract_addressed_characters',
    'extract_current_speaker',
    
    # Channel restrictions
    'is_roleplay_allowed_channel',
    
    # State management
    'RoleplayStateManager',
    'get_roleplay_state',
    
    # Response logic (enhanced pathway functions only)
    'check_subtle_bar_interaction',
    'check_if_other_character_addressed',
    'extract_drink_from_emote',
    
    # Exit conditions
    'detect_roleplay_exit_conditions'
] 