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
from .state_manager import get_roleplay_state, RoleplayStateManager
from .character_tracking import extract_character_names_from_emotes
from .dgm_handler import check_dgm_post, handle_dgm_command
from .attention_engine import get_attention_engine

__all__ = [
    # New Attention Engine
    'get_attention_engine',

    # State Management
    'get_roleplay_state',
    'RoleplayStateManager',

    # Utilities
    'extract_character_names_from_emotes',

    # DGM Handling (Non-LLM)
    'check_dgm_post',
    'handle_dgm_command'
] 