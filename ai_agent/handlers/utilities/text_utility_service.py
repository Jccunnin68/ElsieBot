"""
Text Utility Service - Pythonic Text Analysis and Utilities
===========================================================

This service handles text analysis and utility operations with proper
encapsulation and state management. Refactored from standalone functions
to a proper service class.
"""

import re
from typing import Optional, List, Dict, Any


class TextUtilityService:
    """
    Service for text analysis, token estimation, and general text utilities.
    
    This service provides a clean API for text utility functionality while maintaining
    proper encapsulation and state management.
    """
    
    # Constants for token estimation
    CHARACTERS_PER_TOKEN = 4  # Conservative estimate: 1 token ≈ 4 characters

    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text input to Gemma API.
        Uses conservative estimate: 1 token ≈ 4 characters (more conservative)
        
        Args:
            text: Text to analyze
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return int(len(text) / self.CHARACTERS_PER_TOKEN)
    
    def get_word_count(self, text: str) -> int:
        """
        Get word count of text.
        
        Args:
            text: Text to count words in
            
        Returns:
            Number of words
        """
        if not text:
            return 0
        return len(text.split())
    
    def get_character_count(self, text: str) -> int:
        """
        Get character count of text.
        
        Args:
            text: Text to count characters in
            
        Returns:
            Number of characters
        """
        if not text:
            return 0
        return len(text)
    
    def truncate_text(self, text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to a maximum length with optional suffix.
        
        Args:
            text: Text to truncate
            max_length: Maximum length (including suffix)
            suffix: Suffix to add when truncating (default: "...")
            
        Returns:
            Truncated text
        """
        if not text or len(text) <= max_length:
            return text
        
        if len(suffix) >= max_length:
            return text[:max_length]
        
        return text[:max_length - len(suffix)] + suffix
    
    def extract_urls(self, text: str) -> List[str]:
        """
        Extract URLs from text.
        
        Args:
            text: Text to extract URLs from
            
        Returns:
            List of URLs found in text
        """
        if not text:
            return []
        
        url_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+'
        return re.findall(url_pattern, text)
    
    def remove_urls(self, text: str) -> str:
        """
        Remove URLs from text.
        
        Args:
            text: Text to remove URLs from
            
        Returns:
            Text with URLs removed
        """
        if not text:
            return text
        
        url_pattern = r'https?://[^\s<>"\'{}|\\^`\[\]]+'
        return re.sub(url_pattern, '', text).strip()
    
    def clean_whitespace(self, text: str) -> str:
        """
        Clean excessive whitespace from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Text with cleaned whitespace
        """
        if not text:
            return text
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove trailing/leading whitespace
        return text.strip()
    
    def extract_quoted_text(self, text: str) -> List[str]:
        """
        Extract quoted text from a string.
        
        Args:
            text: Text to extract quotes from
            
        Returns:
            List of quoted strings
        """
        if not text:
            return []
        
        # Match both single and double quotes
        quote_patterns = [
            r'"([^"]*)"',  # Double quotes
            r"'([^']*)'",  # Single quotes
        ]
        
        quoted_text = []
        for pattern in quote_patterns:
            quoted_text.extend(re.findall(pattern, text))
        
        return [quote.strip() for quote in quoted_text if quote.strip()]
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Simple sentence splitting (can be enhanced with more sophisticated rules)
        sentence_pattern = r'[.!?]+\s+'
        sentences = re.split(sentence_pattern, text)
        
        return [sentence.strip() for sentence in sentences if sentence.strip()]
    
    def calculate_readability_score(self, text: str) -> float:
        """
        Calculate a simple readability score based on average sentence and word length.
        
        Args:
            text: Text to analyze
            
        Returns:
            Readability score (lower is more readable)
        """
        if not text:
            return 0.0
        
        sentences = self.split_into_sentences(text)
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Simple readability formula (higher = less readable)
        return (avg_sentence_length * 0.1) + (avg_word_length * 0.5)
    
    def extract_character_names(self, text: str) -> List[str]:
        """
        Extract character names from text using common patterns.
        
        Args:
            text: Text to extract names from
            
        Returns:
            List of character names found
        """
        if not text:
            return []
        
        # Common character name patterns
        patterns = [
            r'\[([A-Z][a-zA-Z\s]+)\]',  # [Character Name]
            r'\*([A-Z][a-z]+)\s+',      # *Name does something*
            r'([A-Z][a-z]+):\s',        # Name: says something
        ]
        
        names = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                name = match.strip()
                if len(name) > 2 and name not in names:
                    names.append(name)
        
        return names
    
    def get_text_statistics(self, text: str) -> Dict[str, Any]:
        """
        Get comprehensive text statistics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with text statistics
        """
        if not text:
            return {
                'character_count': 0,
                'word_count': 0,
                'sentence_count': 0,
                'estimated_tokens': 0,
                'readability_score': 0.0,
                'has_urls': False,
                'character_names': [],
                'quoted_text': []
            }
        
        return {
            'character_count': self.get_character_count(text),
            'word_count': self.get_word_count(text),
            'sentence_count': len(self.split_into_sentences(text)),
            'estimated_tokens': self.estimate_token_count(text),
            'readability_score': self.calculate_readability_score(text),
            'has_urls': bool(self.extract_urls(text)),
            'character_names': self.extract_character_names(text),
            'quoted_text': self.extract_quoted_text(text)
        } 