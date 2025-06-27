"""
Context Analysis Service - Pythonic Context Detection and Analysis
==================================================================

This service handles context analysis for post-response processing and context
detection. Refactored from standalone functions to a proper service class.
"""

import re
from typing import Optional, List


class ContextAnalysisService:
    """
    Service for analyzing message context and detecting addressing patterns.
    
    This service provides a clean API for context analysis functionality while maintaining
    proper encapsulation and state management.
    """
    
    # Patterns for detecting Elsie mentions
    ELSIE_MENTION_PATTERNS: List[str] = [
        r'\belsie\b',
        r'\bbartender\b',
        r'\bbarkeep\b',
        r'\bserver\b',
        r'\bwaitress\b'
    ]

    def detect_elsie_mention(self, user_message: str) -> bool:
        """
        Detects if Elsie is mentioned in the message by name or role.
        This is used to "wake up" Elsie in a channel she isn't actively monitoring.
        
        Args:
            user_message: The user's message to analyze
            
        Returns:
            True if Elsie is mentioned, False otherwise
        """
        message_lower = user_message.lower()
        for pattern in self.ELSIE_MENTION_PATTERNS:
            if re.search(pattern, message_lower):
                return True
        return False

    def detect_who_elsie_addressed(self, response_text: str, user_message: str) -> Optional[str]:
        """
        Detect who Elsie addressed in her response.
        Returns the character name Elsie is speaking to, or None if unclear.
        
        This is used POST-RESPONSE to track conversation state.
        
        Args:
            response_text: Elsie's response text
            user_message: The original user message
            
        Returns:
            Character name Elsie is addressing, or None if unclear
        """
        # Check for direct address patterns like "[Character Name],"
        address_match = re.search(r'\[([A-Z][a-z]+[A-Za-z\s]*)\],?\s*', response_text)
        if address_match:
            return address_match.group(1)
        
        # Look for mentions of character names from the user message
        user_characters = re.findall(r'\[([A-Z][a-z]+[A-Za-z\s]*)\]', user_message)
        for character in user_characters:
            # Check if Elsie mentions this character in her response
            if character.lower() in response_text.lower():
                return character
        
        # Look for common addressing patterns
        addressing_patterns = [
            r'to\s+([A-Z][a-z]+)',
            r'for\s+([A-Z][a-z]+)',
            r'gives?\s+([A-Z][a-z]+)',
            r'hands?\s+([A-Z][a-z]+)',
            r'serves?\s+([A-Z][a-z]+)'
        ]
        
        for pattern in addressing_patterns:
            match = re.search(pattern, response_text)
            if match:
                return match.group(1)
        
        return None

    def detect_who_elsie_addressed_alt(self, response_text: str, user_message: str) -> str:
        """
        Alternative method to detect who Elsie addressed in her response.
        This helps track implicit response chains.
        
        This is used POST-RESPONSE for conversation state tracking.
        
        Args:
            response_text: Elsie's response text
            user_message: The original user message
            
        Returns:
            Character name or empty string if unclear
        """
        # First, try to detect who spoke in the user message (likely who Elsie is responding to)
        from ..service_container import get_character_tracking_service
        char_service = get_character_tracking_service()
        
        # Check for [Character Name] format in user message
        bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
        bracket_matches = re.findall(bracket_pattern, user_message)
        for name in bracket_matches:
            name = name.strip()
            if len(name) > 2:
                name_normalized = ' '.join(word.capitalize() for word in name.split())
                print(f"   👋 ELSIE ADDRESSING: {name_normalized} (detected from user message bracket)")
                return name_normalized
        
        # Check for character names in user message emotes
        character_names = char_service.extract_character_names_from_emotes(user_message)
        if character_names:
            print(f"   👋 ELSIE ADDRESSING: {character_names[0]} (detected from user message emotes)")
            return character_names[0]
        
        # Check if Elsie's response contains addressing terms like "dear", "love", etc.
        response_lower = response_text.lower()
        addressing_terms = ['dear', 'love', 'darling', 'sweetie', 'honey']
        
        # If Elsie used an addressing term, she's likely responding to the speaker
        if any(term in response_lower for term in addressing_terms):
            # Try to extract character from user message again with more patterns
            words = user_message.split()
            for word in words:
                if len(word) > 2 and word[0].isupper() and word.isalpha():
                    # Could be a character name
                    print(f"   👋 ELSIE ADDRESSING: {word} (inferred from addressing term in response)")
                    return word.capitalize()
        
        return ""

    def create_personality_context_prompt(self, user_message: str) -> str:
        """
        Create a prompt fragment for LLM to determine personality context.
        This replaces the hardcoded detect_general_personality_context logic.
        
        Args:
            user_message: The user's message
            
        Returns:
            Formatted prompt for personality context determination
        """
        return f"""
Based on this message: "{user_message}"

Determine which aspect of Elsie's personality should be emphasized:
- STELLAR_CARTOGRAPHER: For space science, navigation, stellar phenomena topics
- BARTENDER: For drinks, service, hospitality topics  
- COUNSELOR: For emotional support, personal problems
- BALANCED: For general conversation (default)

Consider the specific topic and context to choose the most appropriate personality mode.
"""

    def create_context_analysis_prompt(self, user_message: str, conversation_context: str) -> str:
        """
        Create a comprehensive prompt for LLM context analysis.
        This replaces multiple hardcoded detection functions.
        
        Args:
            user_message: The user's message
            conversation_context: Current conversation context
            
        Returns:
            Formatted prompt for comprehensive context analysis
        """
        return f"""
Analyze this roleplay situation for optimal response context:

CURRENT MESSAGE: "{user_message}"

CONVERSATION CONTEXT:
{conversation_context}

Provide analysis for:
1. WHO is speaking (character name if any)
2. WHO is being addressed (Elsie, another character, or group)
3. PERSONALITY MODE needed (Stellar Cartographer, Bartender, Counselor, Balanced)
4. CONVERSATION TONE (casual, formal, emotional, technical)
5. RESPONSE TYPE needed (active dialogue, supportive listening, service, etc.)

Focus on understanding the conversational dynamics and what kind of response would best serve the scene.
"""
    
    def extract_character_name_from_message(self, user_message: str) -> Optional[str]:
        """
        Extract character name from user message using various patterns.
        
        Args:
            user_message: The user's message
            
        Returns:
            Extracted character name or None if not found
        """
        # Look for [Character Name] format
        bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
        bracket_match = re.search(bracket_pattern, user_message)
        if bracket_match:
            name = bracket_match.group(1).strip()
            if len(name) > 2:
                return ' '.join(word.capitalize() for word in name.split())
        
        # Look for common name patterns in emotes
        emote_patterns = [
            r'\*([A-Z][a-z]+)\s+',  # *Name does something*
            r'([A-Z][a-z]+):\s',    # Name: says something
        ]
        
        for pattern in emote_patterns:
            match = re.search(pattern, user_message)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:
                    return name.capitalize()
        
        return None
    
    def detect_conversation_tone(self, user_message: str) -> str:
        """
        Detect the overall tone of the conversation.
        
        Args:
            user_message: The user's message
            
        Returns:
            Detected tone (casual, formal, emotional, technical)
        """
        user_lower = user_message.lower()
        
        # Technical indicators
        technical_terms = ['database', 'search', 'query', 'system', 'computer', 'data', 'analysis']
        if any(term in user_lower for term in technical_terms):
            return 'technical'
        
        # Emotional indicators
        emotional_terms = ['feel', 'sad', 'happy', 'angry', 'worried', 'concerned', 'excited', 'love', 'hate']
        if any(term in user_lower for term in emotional_terms):
            return 'emotional'
        
        # Formal indicators
        formal_terms = ['please', 'thank you', 'sir', 'madam', 'commander', 'captain']
        if any(term in user_lower for term in formal_terms):
            return 'formal'
        
        # Default to casual
        return 'casual' 