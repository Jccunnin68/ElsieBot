"""
DGM (Daedalus Game Master) Handler
===============================

Handles DGM posts for scene setting, character control, and roleplay session management.
DGM posts use [DGM] tags and can control scenes or even Elsie directly.
"""

import re
from typing import Dict, List, Any, Optional

from ..ai_logic.response_decision import ResponseDecision





def extract_scene_context(user_message: str) -> Dict[str, Any]:
    """
    Extract basic scene context information from DGM posts using pattern matching.
    
    The attention engine will handle AI-powered analysis of the scene context.
    This function provides basic structure extraction for immediate use.
    
    Parses location, time, environment, and other scene details that Elsie should understand.
    Examples:
    - "[DGM] *The Stardancer was currently in orbit of Earth.*" -> location: "orbit of Earth", ship: "Stardancer"
    - "[DGM] The doors to Ten Forward slide open as evening approaches." -> location: "Ten Forward", time: "evening"
    """
    # Remove DGM tag for cleaner parsing
    clean_message = re.sub(r'^\s*\[DGM\]\s*', '', user_message, flags=re.IGNORECASE).strip()
    
    print(f"   🎬 EXTRACTING BASIC SCENE CONTEXT from: '{clean_message[:100]}{'...' if len(clean_message) > 100 else ''}'")
    
    scene_context = {
        'location': None,
        'time_of_day': None,
        'atmosphere': None,
        'raw_description': clean_message
    }
    
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
        
        # Bar/venue names
        r'(?:the\s+)?([A-Z][a-zA-Z\s]*(?:lizzy|lounge|bar|pub|cantina))',
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
    
    # Extract atmospheric mood
    atmosphere_patterns = [
        r'\b(peaceful|busy|quiet|lively|tense|relaxed|formal|casual|festive|somber)\b',
        r'\b(empty|crowded|bustling|serene|chaotic)\b',
        r'(?:pulsing|thrumming|vibrating)\s+with\s+(\w+)',
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
        print(f"   ✅ BASIC SCENE CONTEXT EXTRACTED: {len(filtered_context)-1} elements")
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
    # Get character tracking service for validation
    from ..service_container import get_character_tracking_service
    char_service = get_character_tracking_service()
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
    
    # Basic character extraction from explicit [Character Name] format only
    # NOTE: Advanced AI-powered character detection is handled by the attention engine
    characters = []
    
    # Only extract from explicit [Character Name] format for immediate structure
    bracket_pattern = r'\[([^\]]+)\]'
    bracket_matches = re.finditer(bracket_pattern, user_message)
    for match in bracket_matches:
        char_name = match.group(1).strip()
        # Skip DGM tag itself and other system tags
        if char_name.lower() not in ['dgm', 'end', 'scene']:
            # Basic validation using character service
            if char_service.is_valid_character_name(char_name):
                characters.append(char_name)
                print(f"   👤 Explicit character: [{char_name}]")
    
    if characters:
        print(f"   👥 EXPLICIT CHARACTERS: {characters}")
    else:
        print(f"   ℹ️  No explicit character brackets found (AI analysis will handle scene text)")
    
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
                'triggers_roleplay': False,
                'confidence': 1.0,
                'triggers': ['dgm_scene_end'],
                'characters': characters,
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
        'characters': characters,
        'dgm_controlled_elsie': False,
        'elsie_content': '',
        'scene_context': scene_context
    }





def handle_dgm_command(user_message: str, channel_context: Dict = None) -> Optional[ResponseDecision]:
    """
    Checks for and handles DGM commands, returning a ResponseDecision if found.
    This encapsulates the logic for scene setting, ending, and character control.
    """
    dgm_result = check_dgm_post(user_message)
    if not dgm_result or not dgm_result['is_dgm']:
        return None

    dgm_action = dgm_result['action']
    from ..service_container import get_roleplay_state
    rp_state = get_roleplay_state()

    if dgm_action == 'scene_setting':
        print(f"   🎬 DGM Scene Setting - Starting roleplay session")
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(
                turn_number=0, # Turn number is not available here, but session starts at 0
                initial_triggers=['dgm_scene_setting'],
                channel_context=channel_context,  # Pass channel context for proper isolation
                dgm_characters=dgm_result.get('characters', [])
            )
        rp_state.store_dgm_scene_context(dgm_result.get('scene_context', {}))
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={'approach': 'dgm_scene_setting', 'reasoning': 'DGM scene setting.'}
        )

    elif dgm_action == 'end_scene':
        print(f"   🎬 DGM Scene End - Ending roleplay session")
        if rp_state.is_roleplaying:
            rp_state.end_roleplay_session('dgm_scene_end')
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={'approach': 'dgm_scene_end', 'reasoning': 'DGM scene ended.'}
        )

    elif dgm_action == 'control_elsie':
        print(f"   🎭 DGM Controlled Elsie")
        if not rp_state.is_roleplaying:
             rp_state.start_roleplay_session(
                 turn_number=0, 
                 initial_triggers=['dgm_controlled_elsie'],
                 channel_context=channel_context
             )
        rp_state.store_dgm_scene_context(dgm_result.get('scene_context', {}))
        elsie_content = dgm_result.get('elsie_content', '')
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=elsie_content,
            strategy={'approach': 'roleplay_dgm_controlled', 'reasoning': 'DGM controlled Elsie.'}
        )

    return None 