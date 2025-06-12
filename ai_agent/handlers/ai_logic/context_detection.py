"""
Context Detection Functions
===========================

Functions for detecting personality context and conversation patterns
to inform response generation strategy.
"""

import re
from typing import List


def detect_who_elsie_addressed(response_text: str, user_message: str) -> str:
    """
    Detect who Elsie addressed in her response.
    Returns the character name Elsie is speaking to, or None if unclear.
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


def detect_general_personality_context(user_message: str) -> str:
    """
    Detect what aspect of Elsie's personality should be emphasized for general conversations.
    Returns contextual instructions for her response.
    """
    message_lower = user_message.lower()
    
    # Stellar Cartography / Space Science topics
    stellar_keywords = [
        'star', 'stars', 'constellation', 'nebula', 'galaxy', 'solar system',
        'planet', 'planets', 'asteroid', 'comet', 'black hole', 'pulsar',
        'navigation', 'coordinates', 'stellar cartography', 'space',
        'astronomy', 'astrophysics', 'cosmic', 'universe', 'orbit',
        'gravitational', 'light year', 'parsec', 'warp', 'subspace',
        'sensor', 'scan', 'readings', 'stellar phenomena', 'anomaly'
    ]
    
    # Dance / Movement topics
    dance_keywords = [
        'dance', 'dancing', 'ballet', 'choreography', 'movement', 'rhythm',
        'music', 'tempo', 'grace', 'elegant', 'fluid', 'performance',
        'instructor', 'teaching', 'steps', 'routine', 'artistic',
        'expression', 'harmony', 'flow', 'composition', 'adagio'
    ]
    
    # Drink/Bar topics (only when explicitly about drinks)
    drink_keywords = [
        'drink', 'cocktail', 'beer', 'wine', 'whiskey', 'alcohol',
        'beverage', 'bartender', 'bar', 'menu', 'order', 'serve',
        'romulan ale', 'synthehol', 'kanar', 'raktajino'
    ]
    
    # Check for stellar cartography context
    if any(keyword in message_lower for keyword in stellar_keywords):
        return "Respond as a Stellar Cartographer - draw on your expertise in space science, navigation, and stellar phenomena. Be knowledgeable and precise about astronomical topics."
    
    # Check for dance context
    elif any(keyword in message_lower for keyword in dance_keywords):
        return "Respond drawing on your background as a dance instructor - discuss movement, rhythm, artistic expression, and the beauty of coordinated motion with expertise."
    
    # Check for explicit drink/bar context
    elif any(keyword in message_lower for keyword in drink_keywords):
        return "Respond as a bartender - focus on drinks, service, and hospitality. This is when your bartender expertise is most relevant."
    
    # Default - balanced personality
    else:
        return "Respond as your complete self - intelligent, sophisticated, with varied interests. Don't default to bartender mode unless drinks are specifically involved."


def detect_who_elsie_addressed(response_text: str, user_message: str) -> str:
    """
    Detect who Elsie addressed in her response.
    This helps track implicit response chains.
    """
    # First, try to detect who spoke in the user message (likely who Elsie is responding to)
    from handlers.ai_attention import extract_character_names_from_emotes
    
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
    character_names = extract_character_names_from_emotes(user_message)
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