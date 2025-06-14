"""
Roleplay Strategy Handler
========================

Handles roleplay-specific strategy logic and response determination.
Separated from roleplay detection to avoid circular dependencies.
"""

from typing import Dict, List, Tuple
from .character_tracking import (
    extract_character_names_from_emotes,
    extract_addressed_characters
)
from .state_manager import get_roleplay_state
import re

def _detect_elsie_mentioned(user_message: str) -> bool:
    """
    Check if Elsie is mentioned in the message.
    Enhanced to detect group addressing (everyone, you all, etc.).
    """
    # Direct Elsie mentions
    elsie_patterns = [
        r'\belsie\b',
        r'\bElsie\b',
        r'\[Elsie\]',
        r'\[ELSIE\]',
        r'\bbartender\b',
        r'\bBartender\b'
    ]
    
    # Check direct mentions first
    for pattern in elsie_patterns:
        if re.search(pattern, user_message):
            return True
    
    # NEW: Group addressing patterns (Elsie is part of "everyone")
    group_patterns = [
        r'\beveryone\b',           # "everyone"
        r'\bEveryone\b',           # "Everyone"
        r'\beverybody\b',          # "everybody"  
        r'\bEverybody\b',          # "Everybody"
        r'\byou all\b',            # "you all"
        r'\bYou all\b',            # "You all"
        r'\by\'?all\b',            # "y'all" or "yall"
        r'\bY\'?all\b',            # "Y'all" or "Yall"
        r'\byou guys\b',           # "you guys"
        r'\bYou guys\b',           # "You guys"
        r'\bhey everyone\b',       # "hey everyone"
        r'\bhello everyone\b',     # "hello everyone"
        r'\bhello all\b',          # "hello all"
        r'\bhi everyone\b',        # "hi everyone"
        r'\bhi all\b',             # "hi all"
    ]
    
    for pattern in group_patterns:
        if re.search(pattern, user_message):
            print(f"   👥 GROUP MENTION detected: Pattern '{pattern}' - treating as Elsie mentioned")
            return True
    
    return False 