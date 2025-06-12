"""
Roleplay Exit Conditions
========================

Detects conditions that should end a roleplay session, including explicit commands,
OOC (Out of Character) brackets, and technical queries that break immersion.
"""

import re
from typing import Tuple


def detect_roleplay_exit_conditions(user_message: str) -> Tuple[bool, str]:
    """
    Detect conditions that should exit roleplay mode.
    Returns (should_exit, reason)
    """
    message_lower = user_message.lower().strip()
    
    # 1. Explicit exit commands
    exit_commands = [
        'stop roleplay', 'stop roleplaying', 'exit roleplay', 'exit character',
        'end roleplay', 'break character', 'ooc mode', 'out of character'
    ]
    
    for command in exit_commands:
        if command in message_lower:
            return True, "explicit_command"
    
    # 2. OOC brackets
    ooc_patterns = [
        r'\(\([^)]*\)\)',  # ((text))
        r'//[^/]*',        # // text
        r'\[ooc[^\]]*\]',  # [ooc text]
        r'\booc:',         # ooc: text
    ]
    
    for pattern in ooc_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            return True, "ooc_brackets"
 
    
    
    return False, "" 