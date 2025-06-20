"""
Roleplay Exit Service - Pythonic Exit Condition Detection
=========================================================

This service detects conditions that should end a roleplay session, including
explicit commands, OOC (Out of Character) brackets, and technical queries.
Refactored from a standalone function to a proper service class.
"""

import re
from typing import Tuple, List, Dict


class RoleplayExitService:
    """
    Service for detecting roleplay exit conditions and managing session transitions.
    
    This service provides a clean API for exit condition detection while maintaining
    proper encapsulation and configurable patterns.
    """
    
    # Exit command patterns
    EXIT_COMMANDS: List[str] = [
        'stop roleplay', 'stop roleplaying', 'exit roleplay', 'exit character',
        'end roleplay', 'break character', 'ooc mode', 'out of character'
    ]
    
    # OOC (Out of Character) patterns
    OOC_PATTERNS: List[str] = [
        r'\(\([^)]*\)\)',  # ((text))
        r'//[^/]*',        # // text
        r'\[ooc[^\]]*\]',  # [ooc text]
        r'\booc:',         # ooc: text
    ]

    def __init__(self):
        """Initialize the roleplay exit service."""
        self._compiled_ooc_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.OOC_PATTERNS]

    def detect_roleplay_exit_conditions(self, user_message: str) -> Tuple[bool, str]:
        """
        Detect conditions that should exit roleplay mode.
        
        Args:
            user_message: User message to analyze
            
        Returns:
            Tuple of (should_exit, reason)
        """
        message_lower = user_message.lower().strip()
        
        # 1. Check for explicit exit commands
        for command in self.EXIT_COMMANDS:
            if command in message_lower:
                return True, "explicit_command"
        
        # 2. Check for OOC brackets
        for pattern in self._compiled_ooc_patterns:
            if pattern.search(user_message):
                return True, "ooc_brackets"
        
        return False, ""

    def get_exit_reason_description(self, reason: str) -> str:
        """
        Get a human-readable description of an exit reason.
        
        Args:
            reason: Exit reason code
            
        Returns:
            Human-readable description
        """
        descriptions = {
            "explicit_command": "Explicit roleplay exit command detected",
            "ooc_brackets": "Out-of-character (OOC) content detected",
            "": "No exit condition detected"
        }
        return descriptions.get(reason, f"Unknown exit reason: {reason}")

    def is_ooc_message(self, user_message: str) -> bool:
        """
        Check if a message contains out-of-character content.
        
        Args:
            user_message: Message to check
            
        Returns:
            True if message contains OOC content
        """
        for pattern in self._compiled_ooc_patterns:
            if pattern.search(user_message):
                return True
        return False

    def extract_ooc_content(self, user_message: str) -> List[str]:
        """
        Extract out-of-character content from a message.
        
        Args:
            user_message: Message to analyze
            
        Returns:
            List of OOC content strings found
        """
        ooc_content = []
        
        # Extract content from double parentheses
        double_paren_matches = re.findall(r'\(\(([^)]*)\)\)', user_message)
        ooc_content.extend(double_paren_matches)
        
        # Extract content from OOC brackets
        ooc_bracket_matches = re.findall(r'\[ooc([^\]]*)\]', user_message, re.IGNORECASE)
        ooc_content.extend(ooc_bracket_matches)
        
        # Extract content after ooc:
        ooc_colon_matches = re.findall(r'\booc:\s*(.+?)(?:\n|$)', user_message, re.IGNORECASE)
        ooc_content.extend(ooc_colon_matches)
        
        # Extract content after //
        slash_matches = re.findall(r'//\s*(.+?)(?:\n|$)', user_message)
        ooc_content.extend(slash_matches)
        
        return [content.strip() for content in ooc_content if content.strip()]

    def add_exit_command(self, command: str) -> None:
        """
        Add a new exit command to the detection list.
        
        Args:
            command: Exit command to add
        """
        if command.lower() not in [cmd.lower() for cmd in self.EXIT_COMMANDS]:
            self.EXIT_COMMANDS.append(command.lower())

    def remove_exit_command(self, command: str) -> bool:
        """
        Remove an exit command from the detection list.
        
        Args:
            command: Exit command to remove
            
        Returns:
            True if command was removed, False if not found
        """
        command_lower = command.lower()
        try:
            self.EXIT_COMMANDS.remove(command_lower)
            return True
        except ValueError:
            return False

    def get_exit_statistics(self, user_message: str) -> Dict[str, any]:
        """
        Get comprehensive exit condition statistics for a message.
        
        Args:
            user_message: Message to analyze
            
        Returns:
            Dictionary with exit condition analysis
        """
        should_exit, reason = self.detect_roleplay_exit_conditions(user_message)
        ooc_content = self.extract_ooc_content(user_message)
        
        return {
            'should_exit': should_exit,
            'exit_reason': reason,
            'exit_reason_description': self.get_exit_reason_description(reason),
            'has_ooc_content': bool(ooc_content),
            'ooc_content': ooc_content,
            'ooc_content_count': len(ooc_content),
            'is_pure_ooc': self.is_ooc_message(user_message) and not user_message.strip().replace('((', '').replace('))', '').replace('//', '').replace('[ooc', '').replace(']', '').replace('ooc:', '').strip()
        } 