"""
AI Attention - Conversational State and Strategy
=================================================

This package is responsible for tracking the state of the conversation
and determining the AI's response strategy, especially during roleplay.

New Architecture:
- attention_engine.py: A powerful LLM-based "Roleplay Director" that
  analyzes the full conversational context to decide on the optimal
  response strategy for Elsie. Replaces response_logic.py.

Core Components:
- state_manager.py: Manages the RoleplayStateManager.
- character_tracking.py: Utility for extracting character names.
- dgm_handler.py: Handles commands from the DGM (Dungeon Game Master).
"""
from .state_manager import RoleplayStateManager
from .character_tracking import extract_character_names_from_emotes
from .dgm_handler import check_dgm_post, handle_dgm_command

__all__ = [
    # State Management
    'RoleplayStateManager',

    # Utilities
    'extract_character_names_from_emotes',

    # DGM Handling (Non-LLM)
    'check_dgm_post',
    'handle_dgm_command'
]

# REMOVED: Global accessor functions moved to service_container
# Use: from handlers.service_container import get_roleplay_state, get_attention_engine 