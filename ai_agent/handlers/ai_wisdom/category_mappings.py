"""
Category Mappings for New Database Schema
=========================================

This module defines category mappings for the transition from page_type to categories array.
Based on database investigation findings:

Current page_type distribution:
- mission_log: 646 entries
- personnel: 351 entries  
- general: 297 entries
- technology: 72 entries
- ship_info: 52 entries
- location: 49 entries

Ships found: adagio, banshee, caelian, defiant, enterprise, faraday, and others
"""

from typing import List, Optional, Set

# Ship log categories - using title case format as expected in new schema
SHIP_LOG_CATEGORIES = [
    'Adagio Log',
    'Banshee Log', 
    'Caelian Log',
    'Defiant Log',
    'Enterprise Log',
    'Faraday Log',
    'Gigantes Log',
    'Manta Log',
    'Pilgrim Log',
    'Protector Log',
    'Sentinel Log',
    'Stardancer Log',
    # Add more as discovered during migration
]

# Character categories (replacing personnel page_type)
CHARACTER_CATEGORIES = [
    'Characters',
    'NPCs',
    'Personnel Files',
    'Crew Records'
]

# Ship information categories
SHIP_INFO_CATEGORIES = [
    'Ship Information',
    'Vessel Specifications',
    'Ship Registry',
    'Technical Data'
]

# Technology categories
TECHNOLOGY_CATEGORIES = [
    'Technology',
    'Equipment',
    'Systems',
    'Specifications'
]

# Location categories
LOCATION_CATEGORIES = [
    'Locations',
    'Starbases',
    'Planets',
    'Sectors'
]

# General content categories
GENERAL_CATEGORIES = [
    'General Information',
    'Federation Archives',
    'Historical Records',
    'Reference Material'
]

# Complete category list for validation
ALL_CATEGORIES = (
    SHIP_LOG_CATEGORIES + 
    CHARACTER_CATEGORIES + 
    SHIP_INFO_CATEGORIES + 
    TECHNOLOGY_CATEGORIES + 
    LOCATION_CATEGORIES + 
    GENERAL_CATEGORIES
)

# Mapping from old page_type to new categories
PAGE_TYPE_TO_CATEGORIES = {
    'mission_log': SHIP_LOG_CATEGORIES,  # Will be refined based on ship_name
    'personnel': CHARACTER_CATEGORIES,
    'ship_info': SHIP_INFO_CATEGORIES,
    'technology': TECHNOLOGY_CATEGORIES,
    'location': LOCATION_CATEGORIES,
    'general': GENERAL_CATEGORIES
}

def get_ship_from_log_category(category: str) -> Optional[str]:
    """
    Extract ship name from log category.
    
    Args:
        category: Category like 'Stardancer Log'
        
    Returns:
        Ship name in lowercase, or None if not a ship log category
    """
    if category.endswith(' Log') and category in SHIP_LOG_CATEGORIES:
        return category[:-4].lower()  # Remove ' Log' and lowercase
    return None

def get_log_category_from_ship(ship_name: str) -> str:
    """
    Convert ship name to log category format.
    
    Args:
        ship_name: Ship name in any case
        
    Returns:
        Formatted category like 'Stardancer Log'
    """
    return f"{ship_name.title()} Log"

def get_ship_log_category(ship_name: str) -> List[str]:
    """
    Get ship log category for a specific ship.
    
    Args:
        ship_name: Ship name in any case
        
    Returns:
        List containing the ship's log category
    """
    log_category = get_log_category_from_ship(ship_name)
    # Only return if it's a recognized ship log category
    if log_category in SHIP_LOG_CATEGORIES:
        return [log_category]
    else:
        # Fallback to generic mission log
        return ['Mission Log']

def is_ship_log_category(category: str) -> bool:
    """Check if category represents a ship log"""
    return category in SHIP_LOG_CATEGORIES

def is_character_category(category: str) -> bool:
    """Check if category represents character/personnel information"""
    return category in CHARACTER_CATEGORIES

def is_ship_info_category(category: str) -> bool:
    """Check if category represents ship information"""
    return category in SHIP_INFO_CATEGORIES

def is_technology_category(category: str) -> bool:
    """Check if category represents technology information"""
    return category in TECHNOLOGY_CATEGORIES

def is_location_category(category: str) -> bool:
    """Check if category represents location information"""
    return category in LOCATION_CATEGORIES

def is_general_category(category: str) -> bool:
    """Check if category represents general information"""
    return category in GENERAL_CATEGORIES

def convert_page_type_to_categories(page_type: str, ship_name: Optional[str] = None) -> List[str]:
    """
    Convert old page_type to new categories array.
    
    Args:
        page_type: Old page type value
        ship_name: Ship name for mission logs
        
    Returns:
        List of appropriate categories
    """
    if page_type == 'mission_log' and ship_name:
        # Convert ship name to specific log category
        return [get_log_category_from_ship(ship_name)]
    elif page_type in PAGE_TYPE_TO_CATEGORIES:
        # For non-ship logs, return first category from the group
        categories = PAGE_TYPE_TO_CATEGORIES[page_type]
        if page_type == 'mission_log':
            # Generic mission log if no ship specified
            return ['Mission Log']
        return [categories[0]]  # Return primary category
    else:
        # Unknown page type, default to general
        return ['General Information']

def get_categories_for_ship(ship_name: str) -> List[str]:
    """
    Get all possible categories for a specific ship.
    
    Args:
        ship_name: Ship name
        
    Returns:
        List of categories that might apply to this ship
    """
    ship_log_category = get_log_category_from_ship(ship_name)
    return [
        ship_log_category,
        'Ship Information',  # Ship might also have info pages
        'Technical Data'     # Ship might have technical specs
    ]

def validate_categories(categories: List[str]) -> bool:
    """
    Validate that all categories are recognized.
    
    Args:
        categories: List of categories to validate
        
    Returns:
        True if all categories are valid
    """
    category_set = set(categories)
    valid_categories = set(ALL_CATEGORIES)
    return category_set.issubset(valid_categories)

def get_category_type(category: str) -> str:
    """
    Get the type/group of a category.
    
    Args:
        category: Category name
        
    Returns:
        Category type: 'ship_log', 'character', 'ship_info', 'technology', 'location', 'general', or 'unknown'
    """
    if is_ship_log_category(category):
        return 'ship_log'
    elif is_character_category(category):
        return 'character'
    elif is_ship_info_category(category):
        return 'ship_info'
    elif is_technology_category(category):
        return 'technology'
    elif is_location_category(category):
        return 'location'
    elif is_general_category(category):
        return 'general'
    else:
        return 'unknown'

# Reverse mapping for migration validation
CATEGORY_TO_PAGE_TYPE = {}
for page_type, categories in PAGE_TYPE_TO_CATEGORIES.items():
    for category in categories:
        CATEGORY_TO_PAGE_TYPE[category] = page_type 

def is_log_category(category: str) -> bool:
    """
    Check if a category represents a log (contains 'log' in the name).
    This filters out episode summaries and other non-log content.
    
    Args:
        category: Category name to check
        
    Returns:
        True if category contains 'log', False otherwise
    """
    return 'log' in category.lower()

def get_all_log_categories() -> List[str]:
    """
    Get all categories that contain 'log' from the defined categories.
    This dynamically filters to only include actual log categories,
    excluding episode summaries and other content types.
    
    Returns:
        List of categories containing 'log'
    """
    # Filter from ship log categories (primary source)
    log_categories = [cat for cat in SHIP_LOG_CATEGORIES if is_log_category(cat)]
    
    # Add any other log-related categories that might exist
    other_log_categories = [
        'Mission Log',
        'Personal Log', 
        'Captain\'s Log',
        'Engineering Log',
        'Medical Log',
        'Security Log',
        'Science Log'
    ]
    
    # Only include if they contain 'log'
    for cat in other_log_categories:
        if is_log_category(cat) and cat not in log_categories:
            log_categories.append(cat)
    
    print(f"   📊 Dynamic log categories: {len(log_categories)} categories containing 'log'")
    return log_categories

def get_ship_specific_log_categories(ship_name: Optional[str] = None) -> List[str]:
    """
    Get log categories for a specific ship, filtering to only categories containing 'log'.
    
    Args:
        ship_name: Ship name to get categories for
        
    Returns:
        List of log categories for the ship
    """
    if ship_name:
        ship_log_category = get_log_category_from_ship(ship_name)
        if is_log_category(ship_log_category):
            return [ship_log_category]
    
    # Return all log categories if no specific ship
    return get_all_log_categories()

def filter_categories_for_logs(categories: List[str]) -> List[str]:
    """
    Filter a list of categories to only include those containing 'log'.
    
    Args:
        categories: List of categories to filter
        
    Returns:
        Filtered list containing only log categories
    """
    log_categories = [cat for cat in categories if is_log_category(cat)]
    print(f"   🔍 Filtered {len(categories)} categories -> {len(log_categories)} log categories")
    return log_categories 