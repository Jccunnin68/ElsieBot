"""
Structured Query Detector
=========================

This module contains the logic for detecting specific, structured query patterns
that can be handled directly without LLM intervention. It is a key component
of the new agentic architecture, allowing for fast-pathing of explicit user commands.
"""

import re
from typing import Dict, Optional, Any

class StructuredQueryDetector:
    """
    Detects specific, structured query patterns in a user's message.
    """
    def detect_query(self, user_message: str) -> Dict[str, Any]:
        """
        Analyzes the user message to find a matching structured query pattern.

        Args:
            user_message: The raw message from the user.

        Returns:
            A dictionary containing the detected query details, or a 'general'
            type if no specific pattern is matched.
        """
        # The order of these checks is important, from most specific to most general.
        
        # 1. Explicit search: "search for 'term' in 'category'"
        explicit_search = self._detect_explicit_search(user_message)
        if explicit_search:
            return explicit_search

        # 2. Log search: "logs for <ship/character> [latest|first|recent]"
        log_search = self._detect_log_search(user_message)
        if log_search:
            return log_search

        # 3. Typed search: "ship <name>", "character <name>", etc.
        typed_search = self._detect_typed_search(user_message)
        if typed_search:
            return typed_search

        # If no specific pattern is found, it's a general query for the LLM.
        return {'type': 'general', 'query': user_message}

    def _detect_explicit_search(self, user_message: str) -> Optional[Dict[str, str]]:
        """
        Detects the pattern: search for "term" in "category"
        """
        pattern = re.compile(r'search for\s+"([^"]+)"\s+in\s+"([^"]+)"', re.IGNORECASE)
        match = pattern.search(user_message)
        if match:
            term, category = match.groups()
            return {'type': 'explicit', 'term': term.strip(), 'category': category.strip()}
        return None

    def _detect_log_search(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Detects log-related queries for ships or characters.
        Pattern: logs for <ship/character> [latest|first|recent]
        """
        # Pattern to capture the subject (ship/character) and an optional modifier
        pattern = re.compile(r'logs for\s+([^"]+?)(?:\s+(latest|first|recent))?$', re.IGNORECASE)
        match = pattern.search(user_message)
        if match:
            subject, modifier = match.groups()
            subject = subject.strip()
            # Default modifier to 'recent' if not specified, as per requirements
            modifier = modifier.lower() if modifier else 'recent'
            
            return {
                'type': 'logs',
                'subject': subject,
                'modifier': modifier
            }
        return None

    def _detect_typed_search(self, user_message: str) -> Optional[Dict[str, str]]:
        """
        Detects simple typed searches like "ship <name>".
        """
        typed_patterns = {
            'ship': re.compile(r'^ship\s+([A-Za-z0-9\s-]+)$', re.IGNORECASE),
            'character': re.compile(r'^character\s+([A-Za-z0-9\s\'-]+)$', re.IGNORECASE),
            'species': re.compile(r'^species\s+([A-Za-z\s-]+)$', re.IGNORECASE),
            'planet': re.compile(r'^planet\s+([A-Za-z0-9\s-]+)$', re.IGNORECASE),
        }

        for query_type, pattern in typed_patterns.items():
            match = pattern.match(user_message)
            if match:
                term = match.group(1).strip()
                return {'type': query_type, 'term': term}
        return None 