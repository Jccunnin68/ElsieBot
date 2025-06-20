"""
Character Tracking Service - Pythonic Character Name Processing
==============================================================

This service handles character name extraction, validation, and addressing detection
with proper encapsulation and state management. Refactored from standalone functions
to a proper service class with dependency injection support.
"""

import re
from typing import List, Optional, Set, Dict


class CharacterTrackingService:
    """
    Service for tracking and processing character names in roleplay messages.
    
    This service provides a clean API for character name extraction, validation,
    and addressing detection while maintaining proper encapsulation and configuration.
    """
    
    # Common words to exclude from character name detection
    ROLEPLAY_EXCLUDED_WORDS: Set[str] = {
        # Articles
        'The', 'A', 'An',
        # Pronouns
        'She', 'He', 'They', 'It', 'I', 'We', 'You', 'Me', 'Him', 'Her', 'Them', 'Us',
        'This', 'That', 'These', 'Those', 'My', 'Your', 'His', 'Her', 'Its', 'Our', 'Their',
        'Mine', 'Yours', 'Ours', 'Theirs', 'Myself', 'Yourself', 'Himself', 'Herself', 'Itself',
        'Ourselves', 'Yourselves', 'Themselves',
        # Demonstratives and determiners
        'Then', 'Now', 'Here', 'There', 'Some', 'Any', 'All', 'Each', 'Every', 'Both', 'Either',
        'Neither', 'Much', 'Many', 'Few', 'Little', 'More', 'Most', 'Less', 'Least',
        # Question words
        'When', 'Where', 'What', 'Who', 'Why', 'How', 'Which', 'Whose', 'Whom',
        # Modal verbs
        'Can', 'Could', 'Would', 'Should', 'Will', 'Shall', 'May', 'Might', 'Must', 'Ought',
        # Auxiliary verbs
        'Do', 'Does', 'Did', 'Have', 'Has', 'Had', 'Is', 'Are', 'Was', 'Were', 'Am', 'Be', 'Been', 'Being',
        # Common prepositions
        'To', 'From', 'In', 'On', 'At', 'By', 'For', 'With', 'Without', 'About', 'Above', 'Below',
        'Under', 'Over', 'Through', 'Between', 'Among', 'During', 'Before', 'After', 'Since',
        'Until', 'Toward', 'Against', 'Into', 'Onto', 'Upon', 'Within', 'Beneath', 'Beside',
        'Beyond', 'Across', 'Around', 'Behind', 'Along', 'Near', 'Off', 'Out', 'Up', 'Down',
        # Common conjunctions
        'And', 'Or', 'But', 'So', 'Yet', 'Nor', 'For', 'Because', 'Since', 'Although', 'Though',
        'While', 'Whereas', 'If', 'Unless', 'Whether', 'Than', 'As', 'Like',
        # Common verbs
        'Walks', 'Runs', 'Sits', 'Stands', 'Looks', 'Sees', 'Hears', 'Says', 'Tells', 'Asks',
        'Gets', 'Takes', 'Gives', 'Brings', 'Comes', 'Goes', 'Turns', 'Moves', 'Makes', 'Does',
        'Smiles', 'Laughs', 'Nods', 'Shrugs', 'Points', 'Waves', 'Reaches', 'Touches', 'Holds',
        'Enters', 'Exits', 'Approaches', 'Leaves', 'Returns', 'Stops', 'Starts', 'Begins', 'Ends',
        'Opens', 'Closes', 'Pushes', 'Pulls', 'Throws', 'Catches', 'Drops', 'Picks',
        # Common adverbs
        'Very', 'Really', 'Quite', 'Rather', 'Too', 'So', 'Just', 'Only', 'Even', 'Still',
        'Already', 'Yet', 'Soon', 'Often', 'Sometimes', 'Always', 'Never', 'Usually', 'Rarely',
        'Quickly', 'Slowly', 'Carefully', 'Suddenly', 'Finally', 'First', 'Last', 'Next',
        # Common adjectives that might appear as single words
        'Good', 'Bad', 'Big', 'Small', 'Old', 'New', 'Long', 'Short', 'High', 'Low', 'Hot', 'Cold',
        'Fast', 'Slow', 'Easy', 'Hard', 'Light', 'Dark', 'Heavy', 'Soft', 'Loud', 'Quiet',
        'Clean', 'Dirty', 'Full', 'Empty', 'Open', 'Closed', 'Free', 'Busy', 'Rich', 'Poor',
        # Common nouns that aren't names
        'Thing', 'Things', 'Person', 'People', 'Man', 'Woman', 'Boy', 'Girl', 'Child', 'Children',
        'Place', 'Time', 'Day', 'Night', 'Week', 'Month', 'Year', 'Hour', 'Minute', 'Second',
        'Home', 'House', 'Room', 'Door', 'Window', 'Table', 'Chair', 'Bed', 'Floor', 'Wall',
        'Hand', 'Hands', 'Face', 'Eyes', 'Head', 'Body', 'Foot', 'Feet', 'Arm', 'Arms', 'Leg', 'Legs',
        # Additional common words
        'Yes', 'No', 'Maybe', 'Perhaps', 'Please', 'Thank', 'Thanks', 'Sorry', 'Excuse', 'Welcome',
        'Hello', 'Hi', 'Hey', 'Goodbye', 'Bye', 'See', 'Later', 'Today', 'Tomorrow', 'Yesterday',
        'Morning', 'Afternoon', 'Evening', 'Night', 'Way', 'Ways', 'Side', 'Part', 'End', 'Start',
        # Additional common words (abbreviated for space)
        'Good', 'Bad', 'Big', 'Small', 'Yes', 'No', 'Maybe', 'Please', 'Thank', 'Thanks'
    }

    # Define valid character ranges including Nordic and Icelandic characters
    VALID_CHAR_RANGES: List[str] = [
        r'A-Za-z',  # Basic Latin
        r'À-ÿ',     # Latin-1 Supplement
        r'Þþ',      # Icelandic Thorn
        r'Ðð',      # Icelandic Eth
        r'Ææ',      # Icelandic/Nordic AE
        r'Øø',      # Nordic O with stroke
        r'Åå',      # Nordic A with ring
        r'Öö',      # Nordic O with umlaut
        r'Ää',      # Nordic A with umlaut
        r'Üü',      # Nordic U with umlaut
        r'Éé',      # Nordic E with acute
        r'Íí',      # Nordic I with acute
        r'Óó',      # Nordic O with acute
        r'Úú',      # Nordic U with acute
        r'Ýý',      # Nordic Y with acute
        r'Áá',      # Nordic A with acute
        r'Ññ',      # Spanish N with tilde
        r'Ÿÿ',      # Y with diaeresis
        r'Œœ',      # Latin ligature OE
    ]

    def __init__(self):
        """Initialize the character tracking service."""
        # Combine all valid character ranges into a single pattern
        self._valid_char_pattern = f"[{''.join(self.VALID_CHAR_RANGES)}\\s\\'-]+"
        
        # Cache for performance
        self._excluded_lower = {word.lower() for word in self.ROLEPLAY_EXCLUDED_WORDS}
        self._meta_tags = {
            'dgm', 'gm', 'ooc', 'end', 'scene', 'start', 'begin', 'stop', 'pause', 'resume'
        }

    def normalize_character_name(self, name: str) -> str:
        """
        Normalize a character name to a consistent format.
        
        Args:
            name: Character name to normalize
            
        Returns:
            Normalized character name
        """
        if not name:
            return name
            
        words = name.split()
        normalized_words = []
        
        for word in words:
            if "'" in word or "-" in word:
                parts = re.split(r'([\'-])', word)
                normalized_parts = []
                for part in parts:
                    if part in ["'", "-"]:
                        normalized_parts.append(part)
                    else:
                        normalized_parts.append(part.capitalize())
                normalized_words.append("".join(normalized_parts))
            else:
                if word:
                    first_char = word[0].upper()
                    rest_of_word = word[1:]
                    normalized_words.append(first_char + rest_of_word)
        
        return " ".join(normalized_words)

    def is_valid_character_name(self, name: str) -> bool:
        """
        Check if a potential name is valid.
        
        Args:
            name: Name to validate
            
        Returns:
            True if name is valid for a character
        """
        if not name or len(name) < 2:
            return False
            
        name = name.replace('[', '').replace(']', '').strip()
        if not name or len(name) < 2:
            return False
            
        name_lower = name.lower()

        if name_lower in self._meta_tags:
            return False

        words_in_name = name_lower.split()
        if any(word in self._excluded_lower for word in words_in_name):
            return False
        
        if not re.match(f"^{self._valid_char_pattern}$", name):
            return False
        
        if not name[0].isalpha() or not name[0].isupper():
            return False
        
        return True

    def extract_character_names_from_emotes(self, user_message: str) -> List[str]:
        """
        Extract all character names mentioned in emotes within a message.
        
        Args:
            user_message: Message to analyze
            
        Returns:
            List of character names found in emotes
        """
        character_names = []
        
        # Extract from bracket format first
        bracket_matches = re.findall(r'\[([^\]]+)\]', user_message)
        for match in bracket_matches:
            potential_name = match.strip()
            if self.is_valid_character_name(potential_name):
                normalized_name = self.normalize_character_name(potential_name)
                if normalized_name not in character_names:
                    character_names.append(normalized_name)
        
        return character_names

    def extract_addressed_characters(self, user_message: str) -> List[str]:
        """
        Extract characters that are being directly addressed in the message.
        
        Args:
            user_message: Message to analyze
            
        Returns:
            List of character names being addressed
        """
        addressed_characters = []
        
        addressing_patterns = [
            r'@([A-Z][a-zA-ZÀ-ÿ\s\'-]+?)(?:\s|$|[,.!?])',
            r'(?:^|\s)([A-Z][a-zA-ZÀ-ÿ\s\'-]+?),',
            r'(?:Hey|Hello|Hi)\s+([A-Z][a-zA-ZÀ-ÿ\s\'-]+?)(?:\s|$|[,.!?])',
        ]
        
        for pattern in addressing_patterns:
            matches = re.finditer(pattern, user_message)
            for match in matches:
                potential_name = match.group(1).strip()
                if self.is_valid_character_name(potential_name):
                    normalized_name = self.normalize_character_name(potential_name)
                    if normalized_name not in addressed_characters:
                        addressed_characters.append(normalized_name)
        
        return addressed_characters

    def detect_speaking_character(self, user_message: str) -> str:
        """
        Detect the primary speaking character in a message.
        
        Args:
            user_message: Message to analyze
            
        Returns:
            Character name if detected, 'Unknown' otherwise
        """
        # Try bracket format first
        bracket_match = re.search(r'\[([^\]]+)\]', user_message)
        if bracket_match:
            potential_name = bracket_match.group(1).strip()
            if self.is_valid_character_name(potential_name):
                return self.normalize_character_name(potential_name)
        
        return 'Unknown'

    def get_character_statistics(self, user_message: str) -> Dict[str, any]:
        """
        Get comprehensive character statistics for a message.
        
        Args:
            user_message: Message to analyze
            
        Returns:
            Dictionary with character analysis statistics
        """
        return {
            'speaking_character': self.detect_speaking_character(user_message),
            'characters_in_emotes': self.extract_character_names_from_emotes(user_message),
            'addressed_characters': self.extract_addressed_characters(user_message),
            'total_characters_mentioned': len(set(
                self.extract_character_names_from_emotes(user_message) + 
                self.extract_addressed_characters(user_message)
            )),
            'has_character_interaction': bool(
                self.extract_character_names_from_emotes(user_message) or 
                self.extract_addressed_characters(user_message)
            )
        } 