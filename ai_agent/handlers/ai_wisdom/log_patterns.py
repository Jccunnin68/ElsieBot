"""
Log Pattern Recognition
======================

This module contains shared log-related patterns and functions used by both
query_detection.py and log_processor.py to avoid circular imports.
"""

import re
from typing import Optional, Dict, List

# Ship names from the fleet
SHIP_NAMES = [
    'stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 
    'caelian', 'enterprise', 'montagnier', 'faraday', 'cook', 'mjolnir',
    'rendino', 'gigantes', 'banshee'
]
# Log indicators for query detection
LOG_INDICATORS = [
    'log', 'logs', 'mission log', 'ship log', 'stardancer log', 
    'captain log', 'personal log', 'stardate', 'entry',
    'what happened', 'events', 'mission report', 'incident report',
    'summarize', 'summary', 'recap', 'tell me what',
    'last mission', 'recent mission', 'latest log',
    'captain\'s log', 'first officer\'s log',
    'expedition', 'away mission', 'away team',
    'event log', 'event logs', 'incident', 'incident log',
    'event report', 'occurrence', 'happening',
    # Ship-specific log patterns
    'adagio log', 'pilgrim', 'stardancer log', 'protector log',
    'manta ', 'sentinel', 'caelian','gigantes', 'banshee','adagio'
    # Date-based patterns
    'retrieve', 'show me', 'get the log', 'find the log',
    # Named incidents
    'incident log', 'crisis log', 'affair log', 'operation log'
]

# Ship-specific character mappings for disambiguation
SHIP_SPECIFIC_CHARACTER_CORRECTIONS = {
    'stardancer': {
        'tolena': 'Ensign Maeve Blaine',
        'maeve tolena': 'Ensign Maeve Blaine',
        'maeve tolena blaine': 'Ensign Maeve Blaine',
        'maeve': 'Ensign Maeve Blaine',
        'blaine': 'Captain Marcus Blaine',  # Default for Stardancer
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
    }
}

# Fallback character corrections when ship context is unknown or not ship-specific
FALLBACK_CHARACTER_CORRECTIONS = {
    # Specific full names (no ambiguity)
    'marcus blaine': 'Captain Marcus Blaine',
    'captain marcus blaine': 'Captain Marcus Blaine',
    'maeve blaine': 'Ensign Maeve Blaine',
    'maeve tolena blaine': 'Ensign Maeve Blaine',
    'ensign maeve blaine': 'Ensign Maeve Blaine',
    'doctor t\'lena': 'Doctor t\'Lena',
    
    # Other non-ambiguous characters
    'serafino': 'Commander Serafino',
    'doctor serafino': 'Commander Serafino',
    'ankos': 'Doctor Ankos',
    'sif': 'Commander Sif',
    'zhal': 'Commander Zhal',
    'eren': 'Captain Sereya Eren',
    'sereya eren': 'Captain Sereya Eren',
    'dryellia': 'Cadet Dryellia',
    'zarina dryellia': 'Cadet Zarina Dryellia',
    'snow': 'Cadet Snow',
    'rigby': 'Cadet Rigby',
    'scarlett': 'Cadet Scarlett',
    'bethany scarlett': 'Cadet Bethany Scarlett',
    'antony': 'Cadet Antony',
    'finney': 'Cadet Finney',
    'schwarzweld': 'Cadet Hedwik Schwarzweld',
    'kodor': 'Cadet Kodor',
    'vrajen kodor': 'Cadet Vrajen Kodor',
    'tavi': 'Cadet Antony'
}

# Legacy CHARACTER_CORRECTIONS for backward compatibility (deprecated)
CHARACTER_CORRECTIONS = FALLBACK_CHARACTER_CORRECTIONS.copy()

def resolve_character_name_with_context(name: str, ship_context: Optional[str] = None, 
                                       surrounding_text: str = "") -> str:
    """
    Resolve character name using ship context and surrounding text clues.
    
    Args:
        name: Character name to resolve
        ship_context: Ship name from log context
        surrounding_text: Surrounding text for additional context clues
    
    Returns:
        Resolved character name with rank/title
    """
    if not name:
        return name
        
    name_lower = name.lower().strip()
    surrounding_lower = surrounding_text.lower()
    
    # 1. Try ship-specific resolution first
    if ship_context and ship_context.lower() in SHIP_SPECIFIC_CHARACTER_CORRECTIONS:
        ship_corrections = SHIP_SPECIFIC_CHARACTER_CORRECTIONS[ship_context.lower()]
        if name_lower in ship_corrections:
            resolved = ship_corrections[name_lower]
            return resolved
    
    # 2. Handle special ambiguous cases with surrounding text analysis
    if name_lower in ['tolena', 'blaine']:
        resolved_name = _resolve_ambiguous_name(name_lower, ship_context, surrounding_lower)
        if resolved_name:
            return resolved_name
    
    # 3. Fallback to general corrections
    if name_lower in FALLBACK_CHARACTER_CORRECTIONS:
        resolved = FALLBACK_CHARACTER_CORRECTIONS[name_lower]
        return resolved
    
    # 4. Return with proper capitalization if no correction found
    proper_name = ' '.join(word.capitalize() for word in name.split())
    return proper_name

def _resolve_ambiguous_name(name_lower: str, ship_context: Optional[str], surrounding_lower: str) -> Optional[str]:
    """
    Resolve ambiguous names using context clues.
    
    Args:
        name_lower: Lowercase name to resolve
        ship_context: Ship context if available
        surrounding_lower: Lowercase surrounding text
        
    Returns:
        Resolved name or None if still ambiguous
    """
    
    if name_lower == 'tolena':
        # Check for rank indicators in surrounding text
        stardancer_indicators = ['ensign', 'cadet', 'maeve', 'daughter', 'blaine']
        doctor_indicators = ['doctor', 'dr.', 'medical', 'sickbay', 'patient', 'treatment']
        
        stardancer_score = sum(1 for indicator in stardancer_indicators if indicator in surrounding_lower)
        doctor_score = sum(1 for indicator in doctor_indicators if indicator in surrounding_lower)
        
        if stardancer_score > doctor_score:
            return 'Ensign Maeve Blaine'
        elif doctor_score > stardancer_score:
            return 'Doctor t\'Lena'
        elif ship_context:
            # Use ship context as tiebreaker
            if ship_context.lower() == 'stardancer':
                return 'Ensign Maeve Blaine'
            elif ship_context.lower() in ['protector', 'manta', 'pilgrim']:
                return 'Doctor t\'Lena'
        
        # Only print warning for truly ambiguous cases
        print(f"      ⚠️  Could not resolve ambiguous 'Tolena' - insufficient context")
        return None
    
    elif name_lower == 'blaine':
        # Check for rank/context indicators
        captain_indicators = ['captain', 'commanding officer', 'co', 'bridge', 'command']
        ensign_indicators = ['ensign', 'cadet', 'maeve', 'tolena', 'daughter']
        
        captain_score = sum(1 for indicator in captain_indicators if indicator in surrounding_lower)
        ensign_score = sum(1 for indicator in ensign_indicators if indicator in surrounding_lower)
        
        if captain_score > ensign_score:
            return 'Captain Marcus Blaine'
        elif ensign_score > captain_score:
            return 'Ensign Maeve Blaine'
        elif ship_context and ship_context.lower() == 'stardancer':
            # Default to Captain for Stardancer (more senior officer)
            return 'Captain Marcus Blaine'
        
        # Only print warning for truly ambiguous cases
        print(f"      ⚠️  Could not resolve ambiguous 'Blaine' - insufficient context")
        return None
    
    return None

def extract_ship_name_from_log_content(content: str, title: str = "") -> Optional[str]:
    """
    Extract ship name from log content or title for context resolution.
    
    Args:
        content: Log content to analyze
        title: Log title to analyze
        
    Returns:
        Ship name if detected, None otherwise
    """
    text_to_check = f"{title} {content}".lower()
    
    # Check for explicit ship mentions
    for ship in SHIP_NAMES:
        if ship in text_to_check:
            return ship
    
    # Check for USS prefix patterns
    uss_pattern = r'uss\s+(\w+)'
    uss_match = re.search(uss_pattern, text_to_check)
    if uss_match:
        ship_candidate = uss_match.group(1)
        if ship_candidate in SHIP_NAMES:
            return ship_candidate
    
    return None

def is_log_query(query: str) -> bool:
    """Determine if the query is asking about logs"""
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in LOG_INDICATORS)

def has_log_specific_terms(query: str) -> bool:
    """Check if the query contains log-specific terms"""
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in LOG_INDICATORS) 