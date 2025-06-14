"""
DGM (Daedalus Game Master) Handler
===============================

Handles DGM posts for scene setting, character control, and roleplay session management.
DGM posts use [DGM] tags and can control scenes or even Elsie directly.
"""

import re
from typing import Dict, List, Any

from .character_tracking import is_valid_character_name


def extract_scene_context(user_message: str) -> Dict[str, Any]:
    """
    PHASE 2A: Extract scene context information from DGM posts.
    
    Parses location, time, environment, and other scene details that Elsie should understand.
    Examples:
    - "[DGM] *The Stardancer was currently in orbit of Earth.*" -> location: "orbit of Earth", ship: "Stardancer"
    - "[DGM] The doors to Ten Forward slide open as evening approaches." -> location: "Ten Forward", time: "evening"
    """
    # Remove DGM tag for cleaner parsing
    clean_message = re.sub(r'^\s*\[DGM\]\s*', '', user_message, flags=re.IGNORECASE).strip()
    
    scene_context = {
        'location': None,
        'time_of_day': None,
        'ship_status': None,
        'environment': None,
        'atmosphere': None,
        'raw_description': clean_message
    }
    
    print(f"   🎬 EXTRACTING SCENE CONTEXT from: '{clean_message[:100]}{'...' if len(clean_message) > 100 else ''}'")
    
    # Extract location information
    location_patterns = [
        # Specific locations
        r'(?:in|at|to|aboard|on)\s+(Ten Forward|the bridge|engineering|sickbay|the holodeck|the ready room|the observation lounge)',
        r'(?:in|at|to|aboard|on)\s+(Earth|Vulcan|Risa|Deep Space Nine|the Alpha Quadrant)',
        r'(?:in|at|to|aboard|on)\s+(orbit of [A-Z][a-z]+)',
        r'(?:in|at|to|aboard|on)\s+(the [A-Z][a-zA-Z\s]+)',
        
        # Ship locations
        r'(?:aboard|on)\s+(USS [A-Z][a-z]+|the [A-Z][a-z]+)',
        r'(USS [A-Z][a-z]+|the [A-Z][a-z]+)\s+(?:was|is|remains)',
        
        # General location patterns
        r'(?:doors to|entrance to|inside|within)\s+([A-Z][a-zA-Z\s]+)',
        r'([A-Z][a-zA-Z\s]+)\s+(?:slide open|opens|closes)',
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, clean_message, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            scene_context['location'] = location
            print(f"      📍 LOCATION: {location}")
            break
    
    # Extract time of day
    time_patterns = [
        r'\b(morning|afternoon|evening|night|dawn|dusk|midnight|noon)\b',
        r'\b(early morning|late evening|late night)\b',
        r'as\s+(evening|morning|night|dawn|dusk)\s+(?:approaches|arrives|falls)',
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, clean_message, re.IGNORECASE)
        if match:
            time_of_day = match.group(1).strip().lower()
            scene_context['time_of_day'] = time_of_day
            print(f"      🕐 TIME: {time_of_day}")
            break
    
    # Extract ship status
    ship_status_patterns = [
        r'(?:was|is|remains)\s+(?:currently\s+)?(?:in\s+)?(orbit|docked|traveling|at warp|in space)',
        r'(?:orbiting|approaching|leaving|departing)\s+([A-Z][a-z]+)',
        r'(?:at|in|near)\s+(warp|impulse|full stop)',
    ]
    
    for pattern in ship_status_patterns:
        match = re.search(pattern, clean_message, re.IGNORECASE)
        if match:
            ship_status = match.group(0).strip()
            scene_context['ship_status'] = ship_status
            print(f"      🚀 SHIP STATUS: {ship_status}")
            break
    
    # Extract environmental details
    environment_patterns = [
        r'\*([^*]+(?:lighting|atmosphere|temperature|sound|music|noise)[^*]*)\*',
        r'\*([^*]+(?:warm|cold|bright|dim|quiet|loud|peaceful|busy)[^*]*)\*',
        r'\*([^*]+(?:glow|shimmer|flicker|hum|buzz)[^*]*)\*',
    ]
    
    environment_details = []
    for pattern in environment_patterns:
        matches = re.finditer(pattern, clean_message, re.IGNORECASE)
        for match in matches:
            detail = match.group(1).strip()
            environment_details.append(detail)
            print(f"      🌟 ENVIRONMENT: {detail}")
    
    if environment_details:
        scene_context['environment'] = environment_details
    
    # Extract atmospheric mood
    atmosphere_patterns = [
        r'\b(peaceful|busy|quiet|lively|tense|relaxed|formal|casual|festive|somber)\b',
        r'\b(empty|crowded|bustling|serene|chaotic)\b',
    ]
    
    for pattern in atmosphere_patterns:
        match = re.search(pattern, clean_message, re.IGNORECASE)
        if match:
            atmosphere = match.group(1).strip().lower()
            scene_context['atmosphere'] = atmosphere
            print(f"      🎭 ATMOSPHERE: {atmosphere}")
            break
    
    # Filter out None values for cleaner context
    filtered_context = {k: v for k, v in scene_context.items() if v is not None}
    
    if len(filtered_context) > 1:  # More than just raw_description
        print(f"   ✅ SCENE CONTEXT EXTRACTED: {len(filtered_context)-1} elements")
    else:
        print(f"   ℹ️  No specific scene context detected")
    
    return filtered_context


def check_dgm_post(user_message: str) -> Dict[str, Any]:
    """
    Check if this is a DGM (Daedalus Game Master) post for scene setting.
    DGM posts should trigger roleplay sessions but never get responses.
    Enhanced to parse character names from DGM scene descriptions.
    Enhanced to detect DGM-controlled Elsie posts with [DGM][Elsie] pattern.
    PHASE 2A: Enhanced to extract scene context (location, time, environment).
    Returns dict with is_dgm, action, triggers_roleplay, confidence, triggers, characters, dgm_controlled_elsie, scene_context
    """
    # Check for DGM tag at the start of the message
    dgm_pattern = r'^\s*\[DGM\]'
    if not re.search(dgm_pattern, user_message, re.IGNORECASE):
        return {
            'is_dgm': False,
            'action': 'none',
            'triggers_roleplay': False,
            'confidence': 0.0,
            'triggers': [],
            'characters': [],
            'dgm_controlled_elsie': False,
            'elsie_content': '',
            'scene_context': {}
        }
    
    print(f"   🎬 DGM POST ANALYSIS:")
    
    # PHASE 2A: Extract scene context from all DGM posts
    scene_context = extract_scene_context(user_message)
    
    # Check for DGM-controlled Elsie posts: [DGM][Elsie] pattern
    dgm_elsie_pattern = r'\[DGM\]\s*\[Elsie\]\s*(.*)'
    dgm_elsie_match = re.search(dgm_elsie_pattern, user_message, re.IGNORECASE | re.DOTALL)
    
    if dgm_elsie_match:
        elsie_content = dgm_elsie_match.group(1).strip()
        print(f"   🎭 DGM-CONTROLLED ELSIE DETECTED")
        return {
            'is_dgm': True,
            'action': 'control_elsie',
            'triggers_roleplay': True,
            'confidence': 1.0,
            'triggers': ['dgm_controlled_elsie'],
            'characters': [],
            'dgm_controlled_elsie': True,
            'elsie_content': elsie_content,
            'scene_context': scene_context
        }
    
    # Extract character names from multiple sources
    characters = set()  # Use a set to avoid duplicates
    
    # 1. Extract from [Character Name] format - now handles multi-word names
    bracket_pattern = r'\[([^\]]+)\]'
    bracket_matches = re.finditer(bracket_pattern, user_message)
    for match in bracket_matches:
        char_name = match.group(1).strip()
        # Skip DGM tag itself
        if char_name.lower() == 'dgm':
            continue
            
        # Check if this is a multi-word name
        words = char_name.split()
        if len(words) > 1:
            # For multi-word names, validate the entire name as one entity
            if is_valid_character_name(char_name):
                characters.add(char_name)
                print(f"   👤 Multi-word character detected: {char_name}")
        else:
            # Single word names handled as before
            if is_valid_character_name(char_name):
                characters.add(char_name)
    
    # 2. Extract from *italicized text*
    italic_pattern = r'\*([^*]+)\*'
    italic_matches = re.finditer(italic_pattern, user_message)
    for match in italic_matches:
        italic_text = match.group(1).strip()
        # Split the italicized text into words and check each
        words = italic_text.split()
        for word in words:
            # Clean the word of any punctuation
            clean_word = re.sub(r'[^\w\s]', '', word)
            if is_valid_character_name(clean_word):
                characters.add(clean_word)
    
    # Convert set back to list for the return value
    character_list = list(characters)
    if character_list:
        print(f"   👥 CHARACTERS DETECTED IN DGM POST: {character_list}")
    
    # Check for scene end indicators - multiple patterns
    scene_end_patterns = [
        r'\[DGM\]\s*\[END\]',  # [DGM][END]
        r'\[DGM\]\s+END\b',  # [DGM] END (the missing pattern!)
        r'\[DGM\]\s*\*end\s+scene\*',  # [DGM] *end scene*
        r'\[DGM\]\s*\*scene\s+ends?\*',  # [DGM] *scene ends*
        r'\[DGM\]\s*\*fade\s+to\s+black\*',  # [DGM] *fade to black*
        r'\[DGM\]\s*\*roll\s+credits\*',  # [DGM] *roll credits*
        r'\[DGM\]\s*\*curtain\s+falls?\*',  # [DGM] *curtain falls*
        r'\[DGM\]\s*\*scene\s+fades?\*',  # [DGM] *scene fades*
        r'\[DGM\]\s*end\s+of\s+scene',  # [DGM] end of scene
        r'\[DGM\]\s*scene\s+complete',  # [DGM] scene complete
        r'\[DGM\]\s*\*the\s+end\*',  # [DGM] *the end*
    ]
    
    for pattern in scene_end_patterns:
        if re.search(pattern, user_message, re.IGNORECASE):
            print(f"   🎬 DGM SCENE END DETECTED - Pattern: {pattern}")
            return {
                'is_dgm': True,
                'action': 'end_scene',
                'triggers_roleplay': True,
                'confidence': 1.0,
                'triggers': ['dgm_scene_end'],
                'characters': character_list,
                'dgm_controlled_elsie': False,
                'elsie_content': '',
                'scene_context': scene_context
            }
    
    # Default DGM scene setting
    print(f"   🎬 DGM SCENE SETTING DETECTED")
    return {
        'is_dgm': True,
        'action': 'scene_setting',
        'triggers_roleplay': True,
        'confidence': 1.0,
        'triggers': ['dgm_scene_setting'],
        'characters': character_list,
        'dgm_controlled_elsie': False,
        'elsie_content': '',
        'scene_context': scene_context
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