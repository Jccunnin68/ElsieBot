"""
Greeting Service - Pythonic Greeting and Farewell Handling
==========================================================

This service handles greeting and farewell interactions with contextual personality.
Refactored from standalone functions to a proper service class with dependency injection.
"""

import random
import re
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ai_attention.state_manager import RoleplayStateManager

class GreetingService:
    """
    Service for handling greetings, farewells, and status inquiries with contextual personality.
    
    This service provides a clean API for greeting-related responses while maintaining
    proper dependency injection and state management.
    """
    
    def __init__(self, roleplay_state: Optional['RoleplayStateManager'] = None):
        """
        Initialize the greeting service.
        
        Args:
            roleplay_state: Optional roleplay state manager for context awareness
        """
        self._roleplay_state = roleplay_state
    
    @property
    def roleplay_state(self) -> Optional['RoleplayStateManager']:
        """Lazy-load roleplay state to avoid circular imports."""
        if self._roleplay_state is None:
            try:
                from ..service_container import get_roleplay_state
                self._roleplay_state = get_roleplay_state()
            except ImportError:
                pass  # Fallback gracefully if import fails
        return self._roleplay_state

    def handle_greeting(self, user_message: str, personality_context: str = "complete_self") -> Optional[str]:
        """
        Handle greeting messages with contextual personality responses.
        Enhanced to detect roleplay greeting patterns and emoted greetings.
        ENHANCED: Prevents generic responses during active roleplay sessions.
        
        Args:
            user_message: The user's message
            personality_context: The personality context to emphasize
            
        Returns:
            Greeting response string if this is a greeting, None otherwise
        """
        # CRITICAL: Check if we're in roleplay mode - if so, let roleplay context handle it
        rp_state = self.roleplay_state
        if rp_state and rp_state.is_roleplaying:
            print("   🎭 GREETING DETECTION: In roleplay mode - deferring to roleplay context for character-aware greeting")
            return None  # Let roleplay context handle greetings with full character knowledge
            
        user_lower = user_message.lower().strip()
        
        # Standard greeting indicators
        greeting_indicators = ["hello", "hi", "greetings", "hey", "good morning", "good afternoon", "good evening"]
        
        # Enhanced: Roleplay greeting patterns in emotes and actions
        roleplay_greeting_patterns = [
            r'\*waves?\s+hello\*',           # "*waves hello*"
            r'\*nods?\s+in\s+greeting\*',    # "*nods in greeting*"
            r'\*approaches?\s+.*smile\*',     # "*approaches with a smile*"
            r'\*enters?\s+and\s+looks?\s+around\*', # "*enters and looks around*"
            r'\*walks?\s+in\*',              # "*walks in*"
            r'\*arrives?\*',                 # "*arrives*"
            r'\*comes?\s+in\*',              # "*comes in*"
            r'\*steps?\s+(?:in|into)\*',     # "*steps in*"
            r'\*waves?\s+(?:to|at)\s+everyone\*', # "*waves to everyone*"
            r'\*looks?\s+around\s+.*(?:room|bar|area)\*', # "*looks around the room*"
            r'\*glances?\s+around\*',        # "*glances around*"
        ]
        
        # Check standard greeting indicators
        has_standard_greeting = any(word in user_lower for word in greeting_indicators)
        
        # Check roleplay greeting patterns
        has_roleplay_greeting = any(re.search(pattern, user_lower) for pattern in roleplay_greeting_patterns)
        
        # Enhanced: Character-to-character greetings (bracket format)
        character_greeting_pattern = r'\[[^\]]+\]\s*(?:hello|hi|greetings|hey|good\s+(?:morning|afternoon|evening))'
        has_character_greeting = bool(re.search(character_greeting_pattern, user_lower))
        
        # Return None if no greeting detected
        if not (has_standard_greeting or has_roleplay_greeting or has_character_greeting):
            return None
        
        # Enhanced: Extract character name for personalized responses
        character_match = re.search(r'\[([^\]]+)\]', user_message)
        character_name = character_match.group(1) if character_match else None
        
        return self._generate_greeting_response(personality_context, character_name)
    
    def handle_farewell(self, user_message: str, personality_context: str = "complete_self") -> Optional[str]:
        """
        Handle farewell messages with contextual personality responses.
        
        Args:
            user_message: The user's message
            personality_context: The personality context to emphasize
            
        Returns:
            Farewell response string if this is a farewell, None otherwise
        """
        user_lower = user_message.lower().strip()
        
        farewell_indicators = ["bye", "goodbye", "see you", "farewell", "take care", "goodnight"]
        
        if not any(word in user_lower for word in farewell_indicators):
            return None
        
        farewells = [
            "Safe travels. *nods with quiet elegance* The bar remains, as do I. Until next time.",
            "Farewell. *continues polishing glasses with methodical precision* The night continues, and I'll be here when it calls you back.",
            "Until we meet again. *form shifts with subtle grace* May your path be illuminating."
        ]
        
        return random.choice(farewells)

    def handle_status_inquiry(self, user_message: str) -> Optional[str]:
        """
        Handle "how are you" type questions.
        
        Args:
            user_message: The user's message
            
        Returns:
            Status response string if this is a status inquiry, None otherwise
        """
        user_lower = user_message.lower().strip()
        
        status_indicators = ["how are you", "how's it going", "what's up", "how do you feel"]
        
        if not any(indicator in user_lower for indicator in status_indicators):
            return None
        
        return "Doing wonderfully, naturally. *adjusts the interface with fluid precision* Everything's running smoothly. What brings you to my corner of the ship tonight?"

    def get_conversational_response(self, user_message: str, personality_context: str = "complete_self") -> Optional[str]:
        """
        Get contextual conversational responses for various personality contexts.
        Enhanced for roleplay awareness and character detection.
        
        Args:
            user_message: The user's message
            personality_context: The personality context to emphasize
            
        Returns:
            Conversational response string if appropriate, None otherwise
        """
        # Check for basic conversational patterns
        user_lower = user_message.lower().strip()
        
        conversational_patterns = [
            "thanks", "thank you", "nice", "cool", "interesting", "wow", "amazing"
        ]
        
        if not any(pattern in user_lower for pattern in conversational_patterns):
            return None
        
        # Return contextual response based on personality
        if "stellar" in personality_context.lower():
            responses = [
                "*adjusts stellar cartography display* Always happy to help navigate the mysteries of space.",
                "*pauses from analyzing sensor data* The universe is full of wonders.",
                "*nods thoughtfully* Knowledge is meant to be shared."
            ]
        elif "bartender" in personality_context.lower():
            responses = [
                "*polishes glass with practiced movements* All part of the service.",
                "*adjusts bottles with fluid precision* Happy to be of assistance.",
                "*nods warmly* That's what I'm here for."
            ]
        else:
            responses = [
                "*adjusts display with quiet elegance* Always a pleasure.",
                "*nods with subtle grace* Happy to help.",
                "*pauses thoughtfully* Glad I could assist."
            ]
        
        return random.choice(responses)
    
    def _generate_greeting_response(self, personality_context: str, character_name: Optional[str]) -> str:
        """
        Generate appropriate greeting response based on personality context and character name.
        
        Args:
            personality_context: The personality context to emphasize
            character_name: Optional character name for personalized responses
            
        Returns:
            Generated greeting response
        """
        # Contextual greetings based on personality
        if "stellar" in personality_context.lower() or "space" in personality_context.lower():
            if character_name:
                greetings = [
                    f"*looks up from navigation charts* Good evening, {character_name}. The stars are particularly beautiful tonight.",
                    f"*pauses from analyzing sensor data* Hello there, {character_name}. Always fascinating to see what the universe brings our way.",
                    f"*adjusts stellar cartography display* Welcome, {character_name}. What brings you here?",
                    "*pauses thoughtfully* Hello there.",
                    "*nods with quiet elegance* Welcome."
                ]
            else:
                greetings = [
                    "Welcome. *adjusts stellar cartography display* I'm Elsie, Stellar Cartographer aboard the Stardancer. What brings you here?",
                    "*looks up from navigation charts* Good evening. The stars are particularly beautiful tonight. How can I help you?",
                    "*pauses from analyzing sensor data* Hello there. Always fascinating to see what the universe brings our way.",
                    "*pauses thoughtfully* Hello there.",
                    "*nods with quiet elegance* Welcome."
                ]
            
        elif "dance" in personality_context.lower():
            if character_name:
                greetings = [
                    f"*turns with elegant precision* Good evening, {character_name}. The harmony of movement and conversation - both are art forms.",
                    f"*moves with fluid grace* Welcome, {character_name}. There's a certain rhythm to everything, don't you think?",
                    f"*adjusts posture with practiced elegance* Hello, {character_name}. Life is like a dance, and every interaction is a new step.",
                    "*pauses thoughtfully* Hello there.",
                    "*nods with graceful precision* Welcome."
                ]
            else:
                greetings = [
                    "Welcome. *moves with fluid grace* I'm Elsie. There's a certain rhythm to everything, don't you think?",
                    "*turns with elegant precision* Good evening. The harmony of movement and conversation - both are art forms.",
                    "*adjusts posture with practiced elegance* Hello. Life is like a dance, and every interaction is a new step.",
                    "*pauses thoughtfully* Hello there.",
                    "*nods with graceful precision* Welcome."
                ]
        elif "bartender" in personality_context.lower():
            if character_name:
                greetings = [
                    f"*pauses momentarily then moves with elegant precision* Good evening, {character_name}. How may I help you tonight?",
                    f"*polishes glass with practiced movements* Evening, {character_name}. The night is young, and full of possibilities.",
                    f"*adjusts the ambient lighting with fluid grace* Welcome, {character_name}. What draws you to my bar?",
                    "*pauses thoughtfully* Hello there.",
                    "*nods welcomingly* Good evening."
                ]
            else:
                greetings = [
                    "Welcome to my establishment. *adjusts the ambient lighting with fluid grace* I'm Elsie, your bartender for this evening. What draws you to my bar?",
                    "*pauses momentarily then moves with elegant precision* Good evening. I'm Elsie, trained in the finest bartending arts in the quadrant. How may I help you?",
                    "*polishes glass with practiced movements, then sets it down with quiet precision* Evening. The night is young, and full of possibilities. What brings you here?",
                    "*pauses thoughtfully* Hello there.",
                    "*nods welcomingly* Good evening."
                ]
        else:
            # Enhanced: Default responses with character awareness
            if character_name:
                greetings = [
                    f"*adjusts display with fluid precision* Welcome, {character_name}. What brings you here tonight?",
                    f"*looks up with interest* Good evening, {character_name}. Always a pleasure to see you.",
                    f"*adjusts the ambient lighting subtly* Good evening, {character_name}. The night holds many possibilities.",
                    "*pauses thoughtfully* Hello there.",
                    "*nods with quiet elegance* Welcome."
                ]
            else:
                greetings = [
                    "Welcome. *adjusts display with fluid precision* I'm Elsie. What brings you here tonight?",
                    "*looks up with interest* Good evening. Always a pleasure to meet someone new. How can I help you?",
                    "*pauses thoughtfully* Hello there.",
                    "*nods with quiet elegance* Welcome.",
                    "*adjusts the ambient lighting subtly* Good evening. The night holds many possibilities."
                ]
        
        return random.choice(greetings) 