"""
Content Filter Service - Pythonic Content Filtering
===================================================

This service handles content filtering operations with proper
encapsulation and state management. Refactored from standalone functions
to a proper service class.
"""

import re
from typing import List


class ContentFilterService:
    """
    Service for filtering content and removing unwanted information.
    
    This service provides a clean API for content filtering functionality while maintaining
    proper encapsulation and configuration management.
    """
    
    # Meeting information patterns for filtering
    MEETING_INFO_PATTERNS: List[str] = [
        r'Meeting times?.*?\n',
        r'Game master.*?\n',
        r'GM:.*?\n',
        r'Session.*?\n',
        r'Next meeting.*?\n',
        r'Schedule.*?\n'
    ]
    
    # Fallback response patterns
    FALLBACK_RESPONSE_PREFIX = "LLM_PROCESSOR_FALLBACK_"

    def filter_meeting_info(self, text: str) -> str:
        """
        Remove meeting schedule information from responses.
        
        Args:
            text: Text to filter
            
        Returns:
            Filtered text with meeting information removed
        """
        if not text:
            return text
        
        filtered_text = text
        for pattern in self.MEETING_INFO_PATTERNS:
            filtered_text = re.sub(pattern, "", filtered_text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up any double newlines or spaces created by the filtering
        filtered_text = re.sub(r'\n\s*\n', '\n\n', filtered_text)
        filtered_text = re.sub(r' +', ' ', filtered_text)
        return filtered_text.strip()

    def is_fallback_response(self, content: str) -> bool:
        """
        Check if content is a fallback response from LLM processing.
        
        Fallback responses are returned when LLM processing fails due to:
        - Rate limiting
        - API errors  
        - Processing failures
        
        Args:
            content: The content string to check
            
        Returns:
            True if content is a fallback response, False otherwise
        """
        if not content:
            return False
        return content.startswith(self.FALLBACK_RESPONSE_PREFIX)
    
    def clean_discord_formatting(self, text: str) -> str:
        """
        Clean Discord-specific formatting from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Text with Discord formatting removed
        """
        if not text:
            return text
        
        # Remove Discord mentions
        text = re.sub(r'<@!?\d+>', '', text)
        
        # Remove Discord channel mentions
        text = re.sub(r'<#\d+>', '', text)
        
        # Remove Discord role mentions
        text = re.sub(r'<@&\d+>', '', text)
        
        # Remove Discord custom emojis
        text = re.sub(r'<:\w+:\d+>', '', text)
        
        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def remove_conversation_continuations(self, text: str) -> str:
        """
        Remove AI-generated conversation continuations from responses.
        
        Args:
            text: Text to filter
            
        Returns:
            Text with conversation continuations removed
        """
        if not text:
            return text
        
        # Common conversation continuation patterns
        continuation_patterns = [
            r'\\nCustomer:.*',
            r'\\nElsie:.*',
            r'\\nUser:.*',
            r'\\nAssistant:.*',
            r'\nCustomer:.*',
            r'\nElsie:.*',
            r'\nUser:.*',
            r'\nAssistant:.*'
        ]
        
        filtered_text = text
        for pattern in continuation_patterns:
            filtered_text = re.sub(pattern, '', filtered_text, flags=re.DOTALL)
        
        return filtered_text.strip()
    
    def sanitize_user_input(self, text: str) -> str:
        """
        Sanitize user input by removing potentially harmful content.
        
        Args:
            text: User input to sanitize
            
        Returns:
            Sanitized text
        """
        if not text:
            return text
        
        # Remove potentially harmful patterns
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def extract_clean_emotes(self, text: str) -> List[str]:
        """
        Extract emotes from text and return them cleaned.
        
        Args:
            text: Text containing emotes
            
        Returns:
            List of cleaned emote strings
        """
        if not text:
            return []
        
        # Find emotes in *action* format
        emote_pattern = r'\*([^*]+)\*'
        emotes = re.findall(emote_pattern, text)
        
        # Clean and filter emotes
        cleaned_emotes = []
        for emote in emotes:
            cleaned = emote.strip()
            if len(cleaned) > 2:  # Ignore very short emotes
                cleaned_emotes.append(cleaned)
        
        return cleaned_emotes
    
    def add_meeting_filter_pattern(self, pattern: str) -> None:
        """
        Add a new meeting information filter pattern.
        
        Args:
            pattern: Regex pattern to add to meeting filters
        """
        if pattern not in self.MEETING_INFO_PATTERNS:
            self.MEETING_INFO_PATTERNS.append(pattern)
    
    def remove_meeting_filter_pattern(self, pattern: str) -> bool:
        """
        Remove a meeting information filter pattern.
        
        Args:
            pattern: Pattern to remove
            
        Returns:
            True if pattern was removed, False if not found
        """
        try:
            self.MEETING_INFO_PATTERNS.remove(pattern)
            return True
        except ValueError:
            return False 