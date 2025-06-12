"""
Character Tracking and Name Extraction
======================================

Handles character name extraction from messages, validation, and addressing detection.
Supports both [Character Name] bracket format and emote-based character detection.
Includes support for Nordic and Icelandic characters.
"""

import re
from typing import List, Optional

# Common words to exclude from character name detection
ROLEPLAY_EXCLUDED_WORDS = {
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
    'Morning', 'Afternoon', 'Evening', 'Night', 'Way', 'Ways', 'Side', 'Part', 'End', 'Start'
}

# Define valid character ranges including Nordic and Icelandic characters
VALID_CHAR_RANGES = [
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
    r'Íí',      # Nordic I with acute
    r'Óó',      # Nordic O with acute
    r'Úú',      # Nordic U with acute
    r'Ýý',      # Nordic Y with acute
    r'Ññ',      # Spanish N with tilde
    r'Ÿÿ',      # Y with diaeresis
    r'Œœ',      # Latin ligature OE
]

# Combine all valid character ranges into a single pattern
VALID_CHAR_PATTERN = f"[{''.join(VALID_CHAR_RANGES)}\\s\\'-]+"

def normalize_character_name(name: str) -> str:
    """
    Normalize a character name to a consistent format.
    Handles Nordic, Icelandic, and special characters with proper capitalization.
    """
    if not name:
        return name
        
    # Split into words and capitalize each word
    words = name.split()
    normalized_words = []
    
    for word in words:
        # Handle special cases like O'Brien, Mary-Jane, Björk, Þór
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
            # Handle Nordic/Icelandic characters properly
            if word:
                # Capitalize first letter while preserving special characters
                first_char = word[0].upper()
                rest_of_word = word[1:]
                normalized_words.append(first_char + rest_of_word)
    
    return " ".join(normalized_words)

def is_valid_character_name(name: str) -> bool:
    """
    Check if a potential name is valid.
    Enhanced to handle Nordic, Icelandic, and special characters.
    Now with stricter filtering to avoid common words.
    """
    if not name or len(name) < 2:
        return False
    
    # Remove brackets before validation as a safeguard
    name = name.replace('[', '').replace(']', '').strip()
    if not name or len(name) < 2:
        return False
        
    # Convert to lowercase for comparison
    name_lower = name.lower()
    
    # Check against excluded words (case-insensitive)
    excluded_lower = {word.lower() for word in ROLEPLAY_EXCLUDED_WORDS}
    if name_lower in excluded_lower or name_lower in ['you', 'me', 'us', 'them', 'everyone', 'anyone', 'someone']:
        return False
    
    # Check if name contains any valid characters
    if not re.match(f"^{VALID_CHAR_PATTERN}$", name):
        return False
    
    # Ensure name starts with a letter
    if not name[0].isalpha():
        return False
    
    # Must be properly capitalized (first letter uppercase for proper names)
    if not name[0].isupper():
        return False
    
    # Check if name is too short after removing special characters
    clean_name = re.sub(r'[^A-Za-zÀ-ÿÞþÐðÆæØøÅåÖöÄäÜüÉéÍíÓóÚúÝýÁáÑñŸÿŒœ]', '', name)
    if len(clean_name) < 2:
        return False
    
    # Additional checks: avoid single letters followed by apostrophe or common patterns
    if len(name) == 2 and name[1] in ["'", "."]:
        return False
    
    # Avoid obvious non-names like "To", "At", etc. that might be capitalized
    if name_lower in ['to', 'at', 'in', 'on', 'by', 'for', 'with', 'from', 'of', 'as', 'is', 'it']:
        return False
    
    return True

def extract_current_speaker(user_message: str) -> Optional[str]:
    """
    Extract the current speaker from a message.
    Returns the speaker's name if found, None otherwise.
    """
    # Check for bracket format first (most reliable)
    bracket_pattern = f'\\[({VALID_CHAR_PATTERN})\\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            return normalize_character_name(name)
    
    # Check for character names followed by speaking/action indicators
    speaking_patterns = [
        f'\\b({VALID_CHAR_PATTERN})\\s+(?:says?|speaks?|replies?|responds?|asks?|tells?|whispers?|shouts?)',
        f'\\b({VALID_CHAR_PATTERN})\\s+(?:nods?|smiles?|laughs?|sighs?|looks?|turns?|moves?)',
        f'^({VALID_CHAR_PATTERN}):\\s+',  # "Name: dialogue"
        f'"[^"]*"\\s*-?\\s*({VALID_CHAR_PATTERN})',  # "dialogue" - Name
    ]
    
    for pattern in speaking_patterns:
        match = re.search(pattern, user_message)
        if match:
            potential_name = match.group(1)
            if is_valid_character_name(potential_name):
                return normalize_character_name(potential_name)
    
    return None

def extract_character_names_from_emotes(user_message: str) -> List[str]:
    """
    Extract character names from emotes for speaker permanence.
    Uses Named Entity Recognition patterns and validation.
    Enhanced to detect [Character Name] format for multi-character play.
    Supports Nordic and Icelandic characters.
    """
    character_names = []
    
    # Extract character names from [Character Name] brackets
    bracket_pattern = f'\\[({VALID_CHAR_PATTERN})\\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            name_normalized = normalize_character_name(name)
            if name_normalized not in character_names:
                character_names.append(name_normalized)
    
    # Extract text within emotes
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    
    for emote in emotes:
        # Enhanced pattern to catch names with Nordic/Icelandic characters
        potential_names = re.findall(f'\\b({VALID_CHAR_PATTERN})\\b', emote)
        
        for name in potential_names:
            if is_valid_character_name(name):
                name_normalized = normalize_character_name(name)
                if name_normalized not in character_names:
                    character_names.append(name_normalized)
    
    return character_names

def extract_addressed_characters(user_message: str) -> List[str]:
    """
    Extract character names that are being directly addressed in the message.
    Enhanced to handle Nordic and Icelandic characters.
    """
    addressed_characters = []
    
    # Check if message is addressing a character in brackets
    bracket_addressing_pattern = f'\\[({VALID_CHAR_PATTERN})\\][^[]*(?:you|your|yourself)'
    bracket_matches = re.findall(bracket_addressing_pattern, user_message, re.IGNORECASE)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            name_normalized = normalize_character_name(name)
            addressed_characters.append(name_normalized)
    
    # Pattern 1: "Hey/Hi [Name]," at start of message
    greeting_pattern = f'^(?:hey|hi|hello|yo)\\s+({VALID_CHAR_PATTERN}),?\\s'
    match = re.search(greeting_pattern, user_message, re.IGNORECASE)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            name_normalized = normalize_character_name(name)
            addressed_characters.append(name_normalized)
    
    # Pattern 2: "[Name], [statement]" - name at beginning with comma
    name_start_pattern = f'^({VALID_CHAR_PATTERN}),\\s+'
    match = re.search(name_start_pattern, user_message)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            name_normalized = normalize_character_name(name)
            addressed_characters.append(name_normalized)
    
    # Pattern 3: "[statement], [Name]" - name at end with comma
    name_end_pattern = f',\\s+({VALID_CHAR_PATTERN})[.!?]?\\s*$'
    match = re.search(name_end_pattern, user_message)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            name_normalized = normalize_character_name(name)
            addressed_characters.append(name_normalized)
    
    # Pattern 4: "What do you think, [Name]?" - question directed at someone
    question_pattern = f'(?:what do you think|your thoughts|what about you),?\\s+({VALID_CHAR_PATTERN})[.!?]?'
    match = re.search(question_pattern, user_message, re.IGNORECASE)
    if match:
        name = match.group(1)
        if is_valid_character_name(name):
            name_normalized = normalize_character_name(name)
            addressed_characters.append(name_normalized)
    
    # Pattern 5: Inside emotes - "*turns to [Name]*" or "*looks at [Name]*"
    emote_pattern = f'\\*[^*]*(?:turns? to|looks? at|speaks? to|addresses?|faces?)\\s+({VALID_CHAR_PATTERN})[^*]*\\*'
    matches = re.finditer(emote_pattern, user_message, re.IGNORECASE)
    for match in matches:
        name = match.group(1)
        if is_valid_character_name(name):
            name_normalized = normalize_character_name(name)
            addressed_characters.append(name_normalized)
    
    return list(set(addressed_characters))  # Remove duplicates

def detect_speaking_character(user_message: str) -> str:
    """
    Detect if a character is speaking in this message.
    Enhanced to handle Nordic and Icelandic characters.
    """
    # Check for bracket format first (most reliable)
    bracket_pattern = f'\\[({VALID_CHAR_PATTERN})\\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name):
            return normalize_character_name(name)
    
    # Check for character names followed by speaking/action indicators
    speaking_patterns = [
        f'\\b({VALID_CHAR_PATTERN})\\s+(?:says?|speaks?|replies?|responds?|asks?|tells?|whispers?|shouts?)',
        f'\\b({VALID_CHAR_PATTERN})\\s+(?:nods?|smiles?|laughs?|sighs?|looks?|turns?|moves?)',
        f'^({VALID_CHAR_PATTERN}):\\s+',  # "Name: dialogue"
        f'"[^"]*"\\s*-?\\s*({VALID_CHAR_PATTERN})',  # "dialogue" - Name
    ]
    
    for pattern in speaking_patterns:
        match = re.search(pattern, user_message)
        if match:
            potential_name = match.group(1)
            if is_valid_character_name(potential_name):
                return normalize_character_name(potential_name)
    
    return "" 