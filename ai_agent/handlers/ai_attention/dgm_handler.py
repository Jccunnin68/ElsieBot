"""
DGM (Deputy Game Master) Handler
===============================

Handles DGM posts for scene setting, character control, and roleplay session management.
DGM posts use [DGM] tags and can control scenes or even Elsie directly.
"""

import re
from typing import Dict, List, Any

from .character_tracking import is_valid_character_name


def check_dgm_post(user_message: str) -> Dict[str, Any]:
    """
    Check if this is a DGM (Daedalus Game Master) post for scene setting.
    DGM posts should trigger roleplay sessions but never get responses.
    Enhanced to parse character names from DGM scene descriptions.
    Enhanced to detect DGM-controlled Elsie posts with [DGM][Elsie] pattern.
    Returns dict with is_dgm, action, triggers_roleplay, confidence, triggers, characters, dgm_controlled_elsie
    """
    dgm_pattern = r'\[DGM\]'
    if not re.search(dgm_pattern, user_message, re.IGNORECASE):
        return {
            'is_dgm': False,
            'action': 'none',
            'triggers_roleplay': False,
            'confidence': 0.0,
            'triggers': [],
            'characters': [],
            'dgm_controlled_elsie': False,
            'elsie_content': ''
        }
    
    print(f"   🎬 DGM POST ANALYSIS:")
    
    # Check for DGM-controlled Elsie posts: [DGM][Elsie] pattern
    dgm_elsie_pattern = r'\[DGM\]\s*\[Elsie\]\s*(.*)'
    dgm_elsie_match = re.search(dgm_elsie_pattern, user_message, re.IGNORECASE | re.DOTALL)
    
    if dgm_elsie_match:
        elsie_content = dgm_elsie_match.group(1).strip()
        print(f"      🎭 DGM-CONTROLLED ELSIE DETECTED!")
        print(f"      📝 Elsie Content: '{elsie_content[:100]}{'...' if len(elsie_content) > 100 else ''}'")
        
        return {
            'is_dgm': True,
            'action': 'dgm_controlled_elsie',
            'triggers_roleplay': True,
            'confidence': 1.0,
            'triggers': ['dgm_controlled_elsie'],
            'characters': ['Elsie'],
            'dgm_controlled_elsie': True,
            'elsie_content': elsie_content
        }
    
    # Parse character names from DGM post
    characters_mentioned = extract_characters_from_dgm_post(user_message)
    
    # Check for scene ending patterns
    ending_patterns = [
        r'\*end scene\*', r'\*roll credits\*', r'\*scene ends\*',
        r'\*fade to black\*', r'\*curtain falls\*', r'\*scene fades\*',
        r'end of scene', r'scene complete'
    ]
    
    message_lower = user_message.lower()
    for pattern in ending_patterns:
        if re.search(pattern, message_lower):
            print(f"      🎬 SCENE ENDING DETECTED: '{pattern}'")
            return {
                'is_dgm': True,
                'action': 'end_scene',
                'triggers_roleplay': False,
                'confidence': 0.0,
                'triggers': ['dgm_scene_end'],
                'characters': characters_mentioned,
                'dgm_controlled_elsie': False,
                'elsie_content': ''
            }
    
    # Scene setting (default for DGM posts)
    print(f"      🎬 GENERAL DGM POST - Treating as scene setting")
    if characters_mentioned:
        print(f"      👥 CHARACTERS MENTIONED IN DGM POST: {characters_mentioned}")
    
    return {
        'is_dgm': True,
        'action': 'set_scene',
        'triggers_roleplay': True,
        'confidence': 1.0,
        'triggers': ['dgm_scene_setting'],
        'characters': characters_mentioned,
        'dgm_controlled_elsie': False,
        'elsie_content': ''
    }


def extract_characters_from_dgm_post(dgm_message: str) -> List[str]:
    """
    Extract character names from DGM scene descriptions.
    Looks for proper nouns that could be character names.
    Enhanced to detect character lists like "Fallo and Maeve".
    """
    characters = []
    clean_message = re.sub(r'\[DGM\]', '', dgm_message, flags=re.IGNORECASE).strip()
    
    print(f"      🔍 PARSING DGM MESSAGE FOR CHARACTERS: '{clean_message[:100]}{'...' if len(clean_message) > 100 else ''}'")
    
    # Titles to exclude from character names
    titles = {'Captain', 'Commander', 'Lieutenant', 'Doctor', 'Dr', 'Ensign', 'Chief', 'Admiral', 'Colonel', 'Major', 'Sergeant'}
    
    # STEP 1: Handle character lists with "and" - "Name and Name"
    print(f"      📋 STEP 1: Checking for character lists...")
    list_patterns = [
        r'\b([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\b',
        r'\b([A-Z][a-z]+)\s*,\s*([A-Z][a-z]+)\b',
    ]
    
    for pattern in list_patterns:
        matches = re.finditer(pattern, clean_message)
        for match in matches:
            for group_num in range(1, len(match.groups()) + 1):
                potential_name = match.group(group_num)
                if potential_name and potential_name not in titles and is_valid_character_name(potential_name):
                    name_normalized = potential_name.capitalize()
                    if name_normalized not in characters:
                        characters.append(name_normalized)
                        print(f"         👤 CHARACTER FOUND: '{name_normalized}' via list pattern")
    
    # STEP 2: Handle titles with names - "Captain Smith and Lieutenant Jones"
    print(f"      📋 STEP 2: Checking for titled characters...")
    titled_patterns = [
        r'(?:Captain|Commander|Lieutenant|Doctor|Dr\.|Ensign|Chief|Admiral|Colonel|Major|Sergeant)\s+([A-Z][a-z]+)',
    ]
    
    for pattern in titled_patterns:
        matches = re.finditer(pattern, clean_message)
        for match in matches:
            potential_name = match.group(1)
            if potential_name and potential_name not in titles and is_valid_character_name(potential_name):
                name_normalized = potential_name.capitalize()
                if name_normalized not in characters:
                    characters.append(name_normalized)
                    print(f"         👤 CHARACTER FOUND: '{name_normalized}' via titled pattern")
    
    # STEP 3: Look for individual character names in various contexts
    print(f"      📋 STEP 3: Checking for individual characters...")
    individual_patterns = [
        r'\b([A-Z][a-z]+)\s+(?:enters|arrives|walks|sits|stands|looks|turns|speaks|says|approaches|moves)',
        r'\b([A-Z][a-z]+)\'s\s+',
        r'(?:^|\.\s+)([A-Z][a-z]+)\s+',
    ]
    
    for pattern in individual_patterns:
        matches = re.finditer(pattern, clean_message)
        for match in matches:
            potential_name = match.group(1)
            if potential_name and potential_name not in titles and is_valid_character_name(potential_name):
                name_normalized = potential_name.capitalize()
                if name_normalized not in characters:
                    characters.append(name_normalized)
                    print(f"         👤 CHARACTER FOUND: '{name_normalized}' via individual pattern")
    
    # STEP 4: Check for bracket format characters that might be in DGM posts
    print(f"      📋 STEP 4: Checking for bracket format...")
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, clean_message)
    for name in bracket_matches:
        name = name.strip()
        if is_valid_character_name(name) and name not in titles:
            name_normalized = ' '.join(word.capitalize() for word in name.split())
            if name_normalized not in characters:
                characters.append(name_normalized)
                print(f"         👤 CHARACTER FOUND: '[{name_normalized}]' via bracket format")
    
    print(f"      📋 TOTAL CHARACTERS EXTRACTED: {len(characters)} - {characters}")
    return characters 