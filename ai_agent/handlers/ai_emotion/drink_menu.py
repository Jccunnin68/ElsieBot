"""
Drink Menu and Bar Service Responses
====================================

This module handles all drink-related mock responses, including the galactic bar menu
and specific drink orders.
"""

from typing import Optional, Dict


# Star Trek drinks database with responses
DRINKS_DATABASE = {
    "romulan ale": "Romulan Ale. *slides the azure glass forward* Intoxicating and forbidden. What happens here stays here.",
    "synthehol": "Synthehol. *sets glass in place* All the pleasure, none of the consequences.",
    "blood wine": "Klingon Blood Wine. *pours with ceremonial precision* A warrior's choice.",
    "kanar": "Cardassian Kanar. *slides golden liquid across bar* Rich and complex. Not for the timid.",
    "andorian ale": "Andorian Ale. *presents chilled glass* Cool as its homeworld, twice as refreshing.",
    "tranya": "Tranya. *offers glass* First Federation hospitality in liquid form.",
    "tea earl grey hot": "Tea, Earl Grey, hot. *presents cup* A classic choice.",
    "raktajino": "Raktajino. *slides mug forward* Bold enough to rouse the dead.",
    "slug-o-cola": "Slug-o-Cola. *raises eyebrow* Ferengi... ingenuity. An experience, certainly.",
    "ambassador": "Ambassador. *slides glass forward* A diplomatic choice. *smirks slightly*"
}


def handle_drink_request(user_message: str) -> Optional[str]:
    """
    Handle specific drink orders and return appropriate response.
    
    Args:
        user_message: The user's message to check for drink requests
        
    Returns:
        Drink response string if a specific drink is detected, None otherwise
    """
    user_lower = user_message.lower().strip()
    
    # Check for specific drinks first
    for drink, response in DRINKS_DATABASE.items():
        if drink in user_lower or any(word in user_lower for word in drink.split()):
            return response
    
    # General drink requests - only when explicitly asking for drinks
    drink_request_indicators = [
        "drink", "beverage", "cocktail", "beer", "wine", "whiskey", "vodka", "rum", 
        "what can you make", "what do you have to drink"
    ]
    
    if any(indicator in user_lower for indicator in drink_request_indicators):
        recommendations = [
            "Perhaps Romulan Ale? Or something more... traditional like Earl Grey tea? *adjusts bottles with practiced precision*",
            "Andorian Ale offers cool sophistication. Blood Wine provides... intensity. *traces rim of glass thoughtfully*",
            "Fresh Raktajino awaits, or perhaps the complexity of Cardassian Kanar tempts you? *regards selection with measured gaze*",
            "For the adventurous, An Ambassador. For the discerning, Tranya. *raises eyebrow with subtle intrigue*",
            "*fingers move across controls with fluid grace* From synthehol to the most potent Klingon vintage. What calls to you tonight?"
        ]
        import random
        return random.choice(recommendations)
    
    return None


def get_menu_response() -> str:
    """
    Get Elsie's full galactic bar menu response.
    
    Returns:
        Formatted bar menu with all available drinks
    """
    return """*display materializes with elegant precision*

🍺 **ELSIE'S GALACTIC BAR MENU** 🍺

**Federation Classics:**
• Tea, Earl Grey, Hot - A timeless choice
• Synthehol - All the pleasure, none of the consequences
• Raktajino - Bold Klingon coffee for the discerning

**Exotic Indulgences:**
• Romulan Ale - Enigmatically blue and intoxicating
• Andorian Ale - As cool and refined as its origins
• Klingon Blood Wine - For those with warrior hearts
• Cardassian Kanar - Rich, complex, and warming
• Tranya - Sweet diplomacy in liquid form

**For the Adventurous:**
• Slug-o-Cola - A Ferengi curiosity (proceed with caution)

What tempts you this evening?"""


def is_menu_request(user_message: str) -> bool:
    """
    Check if the user is requesting the drink menu.
    
    Args:
        user_message: The user's message to analyze
        
    Returns:
        True if this is a menu request
    """
    user_lower = user_message.lower().strip()
    
    menu_indicators = [
        "menu", "what do you have", "what drinks", "what's available",
        "what can you serve", "drink list", "beverage menu"
    ]
    
    return any(indicator in user_lower for indicator in menu_indicators)


def get_drink_info(drink_name: str) -> Optional[str]:
    """
    Get information about a specific drink.
    
    Args:
        drink_name: Name of the drink to look up
        
    Returns:
        Drink information string if found, None otherwise
    """
    drink_lower = drink_name.lower().strip()
    
    # Extended drink information
    drink_info = {
        "romulan ale": "A potent blue alcoholic beverage from Romulus. Highly intoxicating and technically illegal in the Federation.",
        "synthehol": "Synthetic alcohol that provides the taste and social experience without the negative effects.",
        "blood wine": "A traditional Klingon alcoholic beverage, deep red in color and very strong.",
        "kanar": "A Cardassian alcoholic beverage with a golden color and sweet, complex flavor.",
        "andorian ale": "A blue alcoholic beverage from Andoria, served chilled and known for its refreshing qualities.",
        "tranya": "A sweet, orange-colored beverage from the First Federation.",
        "raktajino": "A Klingon coffee beverage, strong and black, popular throughout the quadrant.",
        "slug-o-cola": "A Ferengi soft drink with a questionable taste and unusual ingredients."
    }
    
    if drink_lower in drink_info:
        return f"*adjusts display with practiced grace* {drink_info[drink_lower]}"
    
    return None 