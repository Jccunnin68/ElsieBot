"""
Character Mappings and Resolution for DB Populator
==================================================

This module contains a local copy of log-related patterns and functions
required by the db_populator. This avoids cross-container dependencies
by making the populator self-sufficient.
"""

import re
from typing import Optional, Dict, List

# Ship-specific character mappings for disambiguation
SHIP_SPECIFIC_CHARACTER_CORRECTIONS = {
    'stardancer': {
        'tolena': 'Ensign Maeve Blaine',
        'maeve tolena': 'Ensign Maeve Blaine',
        'maeve tolena blaine': 'Ensign Maeve Blaine',
        'maeve': 'Ensign Maeve Blaine',
        'marcus': 'Captain Marcus Blaine',
        'captain blaine': 'Captain Marcus Blaine',
    },
    'protector': {
        'tolena': 'Doctor t\'Lena',
        't\'lena': 'Doctor t\'Lena',
        'tlena': 'Doctor t\'Lena',
        'doctor tolena': 'Doctor t\'Lena',
        'dr tolena': 'Doctor t\'Lena',
    },
    'manta': {
        'tolena': 'Doctor t\'Lena',
        't\'lena': 'Doctor t\'Lena',
        'tlena': 'Doctor t\'Lena',
        'doctor tolena': 'Doctor t\'Lena',
        'dr tolena': 'Doctor t\'Lena',
    },
    'pilgrim': {
        'tolena': 'Doctor t\'Lena',
        't\'lena': 'Doctor t\'Lena',
        'tlena': 'Doctor t\'Lena',
        'doctor tolena': 'Doctor t\'Lena',
        'dr tolena': 'Doctor t\'Lena',
       
    },
    'adagio': {
        'Eren': 'Sereya Eren',
        'Sereya': 'Sereya Eren',
        'Talia':'Captain Talia',
        'Campbell':'Conor Campbell',

        
    }
}
FLEET_SHIP_NAMES = [
    'stardancer', 'USS Stardancer', 'protector', 'USS Protector', 'manta', 'USS Manta',
    'pilgrim', 'USS Pilgrim', 'gigantes', 'mjolnir', 'adagio', 'USS Adagio',
    'caelian', 'USS Caelian', 'mjolnir', 'USS Mjolnir', 'gigantes', 'USS Gigantes',
]

# Fallback character corrections when ship context is unknown
FALLBACK_CHARACTER_CORRECTIONS = {
    'marcus blaine': 'Captain Marcus Blaine',
    'captain marcus blaine': 'Captain Marcus Blaine',
    'maeve blaine': 'Ensign Maeve Blaine',
    'maeve tolena blaine': 'Ensign Maeve Blaine',
    'ensign maeve blaine': 'Ensign Maeve Blaine',
    'doctor t\'lena': 'Doctor t\'Lena',
    'serafino': 'Commander Serafino',
    'doctor serafino': 'Commander Serafino',
    'ankos': 'Doctor Ankos',
    'sif': 'Commander Sif',
    'zhal': 'Commander Zhal',
    'eren': 'Captain Sereya Eren',
    'sereya eren': 'Captain Sereya Eren',
    'dryellia': 'Cadet Dryellia',
    'zarina dryellia': 'Cadet Zarina Dryellia',
    'zarina': 'Cadet Zarina Dryellia',
    'alemyn': 'Surithrae Alemyn',
    'snow': 'Cadet Snow',
    'rigby': 'Cadet Rigby',
    'scarlett': 'Cadet Scarlett',
    'bethany scarlett': 'Cadet Bethany Scarlett',
    'antony': 'Cadet Antony',
    'finney': 'Cadet Finney',
    'schwarzweld': 'Cadet Hedwik Schwarzweld',
    'kodor': 'Cadet Kodor',
    'vrajen kodor': 'Cadet Vrajen Kodor',
    'vrajen': 'Cadet Vrajen Kodor',
    'tavi': 'Cadet Antony'
}

def resolve_character_name_with_context(name: str, ship_context: Optional[str] = None, surrounding_text: str = "") -> str:
    if not name:
        return name
    name_lower = name.lower().strip()
    surrounding_lower = surrounding_text.lower()
    if ship_context and ship_context.lower() in SHIP_SPECIFIC_CHARACTER_CORRECTIONS:
        ship_corrections = SHIP_SPECIFIC_CHARACTER_CORRECTIONS[ship_context.lower()]
        if name_lower in ship_corrections:
            return ship_corrections[name_lower]
    if name_lower in ['tolena', 'blaine']:
        resolved_name = _resolve_ambiguous_name(name_lower, ship_context, surrounding_lower)
        if resolved_name:
            return resolved_name
    if name_lower in FALLBACK_CHARACTER_CORRECTIONS:
        return FALLBACK_CHARACTER_CORRECTIONS[name_lower]
    return ' '.join(word.capitalize() for word in name.split())

def _resolve_ambiguous_name(name_lower: str, ship_context: Optional[str], surrounding_lower: str) -> Optional[str]:
    if name_lower == 'tolena':
        stardancer_indicators = ['ensign', 'cadet', 'maeve', 'daughter', 'blaine']
        doctor_indicators = ['doctor', 'dr.', 'medical', 'sickbay', 'patient', 'treatment']
        stardancer_score = sum(1 for indicator in stardancer_indicators if indicator in surrounding_lower)
        doctor_score = sum(1 for indicator in doctor_indicators if indicator in surrounding_lower)
        if stardancer_score > doctor_score:
            return 'Ensign Maeve Blaine'
        elif doctor_score > stardancer_score:
            return 'Doctor t\'Lena'
        elif ship_context:
            if ship_context.lower() == 'stardancer':
                return 'Ensign Maeve Blaine'
            elif ship_context.lower() in ['protector', 'manta', 'pilgrim']:
                return 'Doctor t\'Lena'
        return None
    elif name_lower == 'blaine':
        captain_indicators = ['captain', 'commanding officer', 'co', 'bridge', 'command']
        ensign_indicators = ['ensign', 'cadet', 'maeve', 'tolena', 'daughter']
        captain_score = sum(1 for indicator in captain_indicators if indicator in surrounding_lower)
        ensign_score = sum(1 for indicator in ensign_indicators if indicator in surrounding_lower)
        if captain_score > ensign_score:
            return 'Captain Marcus Blaine'
        elif ensign_score > captain_score:
            return 'Ensign Maeve Blaine'
        elif ship_context and ship_context.lower() == 'stardancer':
            return 'Captain Marcus Blaine'
        return None
    return None 