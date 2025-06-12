"""
Character Tracking and Name Extraction
======================================

Handles character name extraction from messages, validation, and addressing detection.
Supports both [Character Name] bracket format and emote-based character detection.
"""

import re
from typing import List

# Common words to exclude from character name detection
ROLEPLAY_EXCLUDED_WORDS = {
    'The', 'She', 'He', 'They', 'This', 'That', 'Then', 'Now', 'Here', 'There',
    'When', 'Where', 'What', 'Who', 'Why', 'How', 'Can', 'Could', 'Would', 'Should',
    'Will', 'Shall', 'May', 'Might', 'Must', 'Do', 'Does', 'Did', 'Have', 'Has',
    'Had', 'Is', 'Are', 'Was', 'Were', 'Am', 'Be', 'Been', 'Being',
    'Walks', 'Runs', 'Sits', 'Stands', 'Looks', 'Sees', 'Hears', 'Says', 'Tells',
    'Gets', 'Takes', 'Gives', 'Brings', 'Comes', 'Goes', 'Turns', 'Moves',
    'Smiles', 'Laughs', 'Nods', 'Shrugs', 'Points', 'Waves', 'Reaches',
    'Enters', 'Exits', 'Approaches', 'Leaves', 'Returns', 'Stops'
} 

def is_valid_character_name(name: str) -> bool:
    """Check if a potential name is valid (not a common word)."""
    return (len(name) > 2 and 
            name not in ROLEPLAY_EXCLUDED_WORDS and
            name.lower() not in ['you', 'me', 'us', 'them', 'everyone', 'anyone', 'someone'])


def extract_current_speaker(user_message: str) -> str:
    """Extract the character name from the current message."""
    # Check for [Character Name] format first
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            return ' '.join(word.capitalize() for word in name.split())
    
    # Check for character names in emotes
    character_names = extract_character_names_from_emotes(user_message)
    if character_names:
        return character_names[0]
    
    return ""


def extract_character_names_from_emotes(user_message: str) -> List[str]:
    """
    Extract character names from emotes for speaker permanence.
    Uses Named Entity Recognition patterns and validation.
    Enhanced to detect [Character Name] format for multi-character play.
    """
    character_names = []
    
    # Extract character names from [Character Name] brackets
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            name_normalized = ' '.join(word.capitalize() for word in name.split())
            if name_normalized not in character_names:
                character_names.append(name_normalized)
    
    # Extract text within emotes
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    
    for emote in emotes:
        potential_names = re.findall(r'\b([A-Z][a-z]+)\b', emote)
        
        for name in potential_names:
            if is_valid_character_name(name):
                name_normalized = name.capitalize()
                if name_normalized not in character_names:
                    character_names.append(name_normalized)
    
    return character_names


def extract_addressed_characters(user_message: str) -> List[str]:
    """
    Extract character names that are being directly addressed in the message.
    Looks for patterns like "Hey John," or "What do you think, Sarah?"
    Enhanced to detect [Character Name] format addressing.
    """
    addressed_characters = []
    
    # Check if message is addressing a character in brackets
    bracket_addressing_pattern = r'\[([A-Z][a-zA-Z\s]+)\][^[]*(?:you|your|yourself)'
    bracket_matches = re.findall(bracket_addressing_pattern, user_message, re.IGNORECASE)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            addressed_characters.append(name)
    
    # Pattern 1: "Hey/Hi [Name]," at start of message
    greeting_pattern = r'^(?:hey|hi|hello|yo)\s+([A-Z][a-z]+),?\s'
    match = re.search(greeting_pattern, user_message, re.IGNORECASE)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
    
    # Pattern 2: "[Name], [statement]" - name at beginning with comma
    name_start_pattern = r'^([A-Z][a-z]+),\s+'
    match = re.search(name_start_pattern, user_message)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
    
    # Pattern 3: "[statement], [Name]" - name at end with comma
    name_end_pattern = r',\s+([A-Z][a-z]+)[.!?]?\s*$'
    match = re.search(name_end_pattern, user_message)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
    
    # Pattern 4: "What do you think, [Name]?" - question directed at someone
    question_pattern = r'(?:what do you think|your thoughts|what about you),?\s+([A-Z][a-z]+)[.!?]?'
    match = re.search(question_pattern, user_message, re.IGNORECASE)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
    
    # Pattern 5: Inside emotes - "*turns to [Name]*" or "*looks at [Name]*"
    emote_pattern = r'\*[^*]*(?:turns? to|looks? at|speaks? to|addresses?|faces?)\s+([A-Z][a-z]+)[^*]*\*'
    matches = re.finditer(emote_pattern, user_message, re.IGNORECASE)
    for match in matches:
        name = match.group(1)
        if is_valid_character_name(name):
            addressed_characters.append(name)
    
    return list(set(addressed_characters))  # Remove duplicates


def detect_speaking_character(user_message: str) -> str:
    """
    Detect if a character is speaking in this message (for auto-adding to participants).
    Looks for [Character Name] format or character names followed by dialogue/actions.
    Returns the character name if found, empty string otherwise.
    """
    # Check for bracket format first (most reliable)
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            name_normalized = ' '.join(word.capitalize() for word in name.split())
            return name_normalized
    
    # Check for character names followed by speaking/action indicators
    speaking_patterns = [
        r'\b([A-Z][a-z]+)\s+(?:says?|speaks?|replies?|responds?|asks?|tells?|whispers?|shouts?)',
        r'\b([A-Z][a-z]+)\s+(?:nods?|smiles?|laughs?|sighs?|looks?|turns?|moves?)',
        r'^([A-Z][a-z]+):\s+',  # "Name: dialogue"
        r'"[^"]*"\s*-?\s*([A-Z][a-z]+)',  # "dialogue" - Name
    ]
    
    for pattern in speaking_patterns:
        match = re.search(pattern, user_message)
        if match:
            potential_name = match.group(1)
            if is_valid_character_name(potential_name):
                return potential_name.capitalize()
    
    return ""


def extract_current_speaker(user_message: str) -> str:
    """Extract the character name from the current message."""
    # Check for [Character Name] format first
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            return ' '.join(word.capitalize() for word in name.split())
    
    # Check for character names in emotes
    character_names = extract_character_names_from_emotes(user_message)
    if character_names:
        return character_names[0]
    
    return "" 