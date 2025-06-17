"""
Post-Response Analysis Functions
===============================

Functions for analyzing Elsie's responses after generation to track
conversation state and addressing patterns.

Note: Pre-response context detection is now handled by LLM routing
in conversation_memory.py and context_gatherer.py
"""

import re


def detect_who_elsie_addressed(response_text: str, user_message: str) -> str:
    """
    Detect who Elsie addressed in her response.
    Returns the character name Elsie is speaking to, or None if unclear.
    
    This is used POST-RESPONSE to track conversation state.
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


def detect_who_elsie_addressed_alt(response_text: str, user_message: str) -> str:
    """
    Alternative method to detect who Elsie addressed in her response.
    This helps track implicit response chains.
    
    This is used POST-RESPONSE for conversation state tracking.
    """
    # First, try to detect who spoke in the user message (likely who Elsie is responding to)
    from handlers.ai_attention.character_tracking import extract_character_names_from_emotes
    
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


def create_personality_context_prompt(user_message: str) -> str:
    """
    Create a prompt fragment for LLM to determine personality context.
    This replaces the hardcoded detect_general_personality_context logic.
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


def create_context_analysis_prompt(user_message: str, conversation_context: str) -> str:
    """
    Create a comprehensive prompt for LLM context analysis.
    This replaces multiple hardcoded detection functions.
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