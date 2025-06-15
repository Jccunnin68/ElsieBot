"""
Log Pattern Recognition
======================

This module contains shared log-related patterns and functions used by both
query_detection.py and log_processor.py to avoid circular imports.
"""
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
CHARACTER_CORRECTIONS = {
    'serafino': 'Commander Serafino',
    'doctor serafino': 'Commander Serafino',
    'ankos': 'Doctor Ankos',
    'sif': 'Commander Sif',
    'zhal': 'Commander Zhal',
    'blaine': 'Captain Blaine',
    'marcus blaine': 'Captain Marcus Blaine',
    'eren': 'Captain Sereya Eren',
    'sereya eren': 'Captain Sereya Eren',
    'tolena': 'Ensign Blaine',
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
def is_log_query(query: str) -> bool:
    """Determine if the query is asking about logs"""
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in LOG_INDICATORS)

def has_log_specific_terms(query: str) -> bool:
    """Check if the query contains log-specific terms"""
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in LOG_INDICATORS) 