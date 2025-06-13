"""
Greeting and Farewell Responses
===============================

This module handles greeting and farewell interactions with contextual personality.
"""

import random
from typing import Optional
import re


def handle_greeting(user_message: str, personality_context: str = "complete_self") -> Optional[str]:
    """
    Handle greeting messages with contextual personality responses.
    Enhanced to detect roleplay greeting patterns and emoted greetings.
    
    Args:
        user_message: The user's message
        personality_context: The personality context to emphasize
        
    Returns:
        Greeting response string if this is a greeting, None otherwise
    """
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


def handle_farewell(user_message: str, personality_context: str = "complete_self") -> Optional[str]:
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


def handle_status_inquiry(user_message: str) -> Optional[str]:
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


def get_conversational_response(user_message: str, personality_context: str = "complete_self") -> Optional[str]:
    """
    Get contextual conversational responses for various personality contexts.
    Enhanced for roleplay awareness and character detection.
    
    Args:
        user_message: The user's message
        personality_context: The personality context to emphasize
        
    Returns:
        Conversational response string based on context
    """
    
    # Enhanced: Check for character names in roleplay format
    character_match = re.search(r'\[([^\]]+)\]', user_message)
    character_name = character_match.group(1) if character_match else None
    
    if "stellar" in personality_context.lower():
        conversational_responses = [
            "*adjusts sensor readings* Fascinating.",
            "*looks up from star charts* That's intriguing.",
            "*pauses navigation calculations* Tell me more.",
            "*focuses on you with scientific interest* Continue.",
            "*raises an eyebrow analytically* Really?",
            "*sets down stellar data* I'm listening.",
            "*nods thoughtfully* The patterns are interesting.",
            "*glances up from cartography display* Go on.",
            "*moves with measured precision* That's worth considering.",
            "*focuses with scientific curiosity* And then?"
        ]
    elif "dance" in personality_context.lower():
        conversational_responses = [
            "*moves with fluid grace* Interesting.",
            "*adjusts posture elegantly* I see.",
            "*turns with practiced precision* Tell me more.",
            "*flows into a thoughtful stance* Continue.",
            "*raises an eyebrow with artistic flair* Really?",
            "*pauses mid-movement* I'm listening.",
            "*nods with rhythmic grace* That's intriguing.",
            "*shifts with elegant timing* Go on.",
            "*moves harmoniously* That's worth considering.",
            "*focuses with artistic interest* And then?"
        ]
    elif "bartender" in personality_context.lower():
        conversational_responses = [
            "*nods thoughtfully* Interesting.",
            "*leans against the bar* I see.",
            "*adjusts a glass* That's worth considering.",
            "*glances up with interest* Tell me more.",
            "*pauses in her work* Go on.",
            "*raises an eyebrow* Really?",
            "*sets down what she's doing* I'm listening.",
            "*moves with practiced grace* Continue.",
            "*focuses on you* That's intriguing.",
            "*nods encouragingly* And then?"
        ]
    else:
        # Enhanced: Include character-aware responses when possible
        if character_name:
            conversational_responses = [
                f"*nods thoughtfully at {character_name}* Interesting.",
                f"*adjusts display while listening to {character_name}* I see.",
                f"*focuses on {character_name}* That's worth considering.",
                "*nods thoughtfully* Interesting.",
                "*adjusts display* I see.", 
                "*pauses in her work* That's worth considering."
            ]
        else:
            conversational_responses = [
                "*nods thoughtfully* Interesting.",
                "*adjusts display* I see.",
                "*pauses in her work* That's worth considering.",
                "*glances up with interest* Tell me more.",
                "*focuses on you* Go on.",
                "*raises an eyebrow* Really?",
                "*sets down what she's doing* I'm listening.",
                "*moves with practiced grace* Continue.",
                "*looks at you intently* That's intriguing.",
                "*nods encouragingly* And then?"
            ]
    
    return random.choice(conversational_responses) 