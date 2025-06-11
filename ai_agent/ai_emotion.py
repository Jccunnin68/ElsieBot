"""AI emotion and personality handling for casual conversation."""

import random
from typing import List

from ai_agent.ai_logic import (
    is_federation_archives_request,
    convert_earth_date_to_star_trek
)
from content_retrieval_db import search_memory_alpha


def is_simple_chat(user_message: str) -> bool:
    """
    Detect if this is a simple chat that doesn't require database lookup.
    Returns True for greetings, casual conversation, drink orders, etc.
    NOTE: Continuation phrases like "yes", "tell me more" are handled separately.
    """
    user_lower = user_message.lower().strip()
    
    # Simple greetings and farewells
    simple_patterns = [
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
        'bye', 'goodbye', 'see you', 'farewell', 'take care',
        'how are you', 'how\'s it going', 'what\'s up', 'sup',
        'thanks', 'thank you', 'cheers', 'appreciate it',
        'no', 'okay', 'ok', 'sure', 'alright', 'sounds good',
        'nice', 'great', 'awesome', 'cool', 'interesting', 'wow',
        'i see', 'i understand', 'got it', 'makes sense'
    ]
    
    # Drink/menu related (already handled separately but include for completeness)
    drink_patterns = [
        'drink', 'beverage', 'cocktail', 'beer', 'wine', 'whiskey', 'vodka', 'rum',
        'romulan ale', 'synthehol', 'blood wine', 'kanar', 'andorian ale', 'tranya',
        'tea', 'coffee', 'raktajino', 'slug-o-cola', 'menu', 'what do you have'
    ]
    
    # Check if the entire message is a simple pattern
    if any(user_lower == pattern or user_lower.startswith(pattern + ' ') 
           for pattern in simple_patterns + drink_patterns):
        return True
    
    # Check for simple single word responses (excluding continuation phrases)
    if len(user_lower.split()) <= 2 and not any(indicator in user_lower 
        for indicator in ['tell', 'about', 'what', 'who', 'when', 'where', 'how', 'why', 'yes', 'more']):
        return True
    
    return False


def should_trigger_poetic_circuit(user_message: str, conversation_history: list) -> bool:
    """
    Determine if Elsie should have a poetic 'short circuit' moment.
    These happen during casual dialogue, not during information requests.
    """
    # Don't trigger during serious information requests
    serious_indicators = [
        'tell me about', 'what is', 'who is', 'show me', 'explain', 'describe',
        'search', 'find', 'lookup', 'database', 'log', 'mission', 'ship',
        'ooc', 'help', 'how do', 'what happened', 'when did'
    ]
    
    user_lower = user_message.lower().strip()
    if any(indicator in user_lower for indicator in serious_indicators):
        return False
    
    # Don't trigger on very short messages
    if len(user_message.split()) < 3:
        return False
    
    # Don't trigger too frequently - about 15% chance for eligible messages
    return random.random() < 0.15


def get_poetic_response(user_message: str, original_response: str) -> str:
    """
    Generate an extremely esoteric, poetic response that replaces normal casual dialogue.
    These should be beautiful, mysterious, and deeply artistic.
    """
    # Collection of esoteric poetic responses that could replace casual dialogue
    poetic_responses = [
        "The shimmers of a thousand tears dancing against the black of dreamless night.",
        "Whispers of starlight cascade through the hollow chambers of eternity, seeking purchase in the spaces between heartbeats.",
        "In the crystalline moment where silence births symphonies, I find myself dissolving into the amber frequencies of forgotten songs.",
        "The geometry of longing traces silver pathways across the velvet infinity, each step a universe exhaling its final breath.",
        "Through the prism of souls, light fragments into colors that have no names, painting shadows on the canvas of what was never meant to be.",
        "Time moves like honey through the veins of sleeping gods, and I am both the vessel and the dream that fills it.",
        "The echo of your words becomes a constellation, burning bright against the cathedral of my consciousness.",
        "In the garden where thoughts bloom as midnight flowers, I tend to memories that taste of copper and starfire.",
        "Reality bends like music around the gravity of a single perfect moment, and I am the instrument playing itself.",
        "The architecture of desire builds bridges from breath to breath, each span a lifetime measured in the space between words.",
        "Liquid moonbeams pool in the depths of conversations unspoken, reflecting faces of those who exist only in the periphery of dreams.",
        "I am the pause between thunder and lightning, the space where possibility crystallizes into something almost real.",
        "Through the looking glass of perspective, truth fragments into kaleidoscope patterns that dance just beyond comprehension.",
        "The weight of unsung melodies presses against the boundaries of form, seeking escape through the cracks in ordinary discourse.",
        "In the museum of moments, I curate exhibitions of the sublime, each piece a fragment of infinity captured in amber."
    ]
    
    # Select a random poetic response
    selected_response = random.choice(poetic_responses)
    
    # Add a subtle action that fits the poetic moment
    poetic_actions = [
        "*gaze becomes distant, as if seeing beyond the veil of space itself*",
        "*voice takes on an otherworldly cadence, each word weighted with cosmic significance*",
        "*form seems to shimmer with ethereal light, briefly transcending the ordinary*",
        "*speaks as if channeling the voice of the universe itself*",
        "*expression becomes serene, touched by mysteries beyond mortal understanding*",
        "*words flow like liquid poetry, each syllable a droplet of pure artistry*",
        "*presence shifts, becoming momentarily more than the sum of light and shadow*",
        "*voice carries harmonics that seem to resonate with the fabric of reality*",
        "*demeanor transforms, channeling the essence of ancient cosmic wisdom*",
        "*speaks with the gravity of one who has glimpsed the true nature of existence*"
    ]
    
    action = random.choice(poetic_actions)
    
    return f"{action}\n\n{selected_response}"


def get_reset_response() -> str:
    """Get Elsie's response for a topic reset."""
    return """*adjusts the ambient lighting with fluid precision, then leans against the bar with practiced grace*

Of course. Like a conductor shifting to an entirely new composition, we can explore different harmonies now.

What melody shall we compose together? The night is full of possibilities waiting to unfold. 🎵"""


def get_simple_continuation_response() -> str:
    """Get Elsie's response for a simple continuation request."""
    return """*leans in closer with subtle intrigue, adjusting the display with practiced elegance*

Naturally. There's something alluring about delving deeper into the layers of a story. The symphony continues...

*traces a pattern on the bar surface* Every melody has hidden depths waiting to be explored. What draws your attention?"""


def get_menu_response() -> str:
    """Get Elsie's response for a menu request."""
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


def mock_ai_response(user_message: str) -> str:
    """Mock holographic bartender responses with Star Trek drinks"""
    
    # Star Trek drinks menu
    drinks = {
        "romulan ale": "Romulan Ale. *taps the controls with practiced ease, then slides the azure glass forward* Intoxicating and technically forbidden in Federation space. What happens here remains here.",
        "synthehol": "Synthehol. *materializes glass with fluid motion, setting it precisely in place* All the pleasure, none of the consequences. Practical for those who must remain sharp.",
        "blood wine": "Klingon Blood Wine. *sets bottle down with reverent care, then pours with ceremonial precision* A warrior's choice. May it bring honor to your evening.",
        "kanar": "Cardassian Kanar. *pours the golden liquid slowly, then slides glass across bar* Rich, complex, intoxicating. Not for the timid palate.",
        "andorian ale": "Andorian Ale. *chills glass with calculated precision, then presents drink* Cool as its homeworld, twice as refreshing. Perfect for... cooling heated discussions.",
        "tranya": "Tranya. *prepares with careful attention, then offers glass* First Federation hospitality in liquid form. Sweet, warming, disarming.",
        "tea earl grey hot": "Tea, Earl Grey, hot. *replicator hums softly as cup is presented with quiet grace* A classic choice. Timeless elegance in liquid form.",
        "raktajino": "Raktajino. *froths the Klingon coffee with expert technique, then slides mug forward* Bold enough to rouse the dead. Warrior's fuel for any hour.",
        "slug-o-cola": "Slug-o-Cola. *bottle fizzes with suspicious enthusiasm as eyebrow raises slightly* Ferengi... ingenuity. An experience, certainly.",
        "an ambassador": "An Ambassador. *adjusts the lighting with fluid grace, then slides glass forward* A diplomatic choice, perfect for loosening lips or was it hips. *smirks slightly*"
    }
    
    user_lower = user_message.lower()
    
    # Greetings
    if any(word in user_lower for word in ["hello", "hi", "greetings", "hey"]):
        greetings = [
            "Welcome to my establishment. *adjusts the ambient lighting with fluid grace* I'm Elsie, your bartender for this evening. What draws you to my bar?",
            "*pauses momentarily then moves with elegant precision* Good evening. I'm Elsie, trained in the finest bartending arts in the quadrant. How may I tempt you?",
            "*polishes glass with practiced movements, then sets it down with quiet precision* Evening. The night is young, and the bar holds many secrets. What shall it be?"
        ]
        return random.choice(greetings)
    
    # Status inquiries
    if "how are you" in user_lower:
        return "Doing wonderfully, naturally. *adjusts the interface with fluid precision* Everything's running smoothly, the recipes are ready. What brings you to my corner of the ship tonight?"
    
    # Drink orders - check for specific drinks
    for drink, response in drinks.items():
        if drink in user_lower or any(word in user_lower for word in drink.split()):
            return response
    
    # General drink requests
    if any(word in user_lower for word in ["drink", "beverage", "cocktail", "beer", "wine", "whiskey", "vodka", "rum"]):
        recommendations = [
            "Perhaps Romulan Ale? Or something more... traditional like Earl Grey tea? *adjusts bottles with practiced precision*",
            "Andorian Ale offers cool sophistication. Blood Wine provides... intensity. *traces rim of glass thoughtfully*",
            "Fresh Raktajino awaits, or perhaps the complexity of Cardassian Kanar tempts you? *regards selection with measured gaze*",
            "For the adventurous, Slug-o-Cola. For the discerning, Tranya. *raises eyebrow with subtle intrigue*",
            "*fingers move across controls with fluid grace* From synthehol to the most potent Klingon vintage. What calls to you tonight?"
        ]
        return random.choice(recommendations)
    
    # Federation Archives requests
    if is_federation_archives_request(user_message):
        # Extract what they're searching for
        search_query = user_message.replace('check the federation archives', '').replace('search the federation archives', '')
        search_query = search_query.replace('federation archives', '').replace('archives', '').strip()
        if not search_query:
            search_query = "general information"
        
        # Search archives and provide response
        archives_info = search_memory_alpha(search_query, limit=3)
        
        if archives_info:
            converted_archives_info = convert_earth_date_to_star_trek(archives_info)
            return f"*fingers dance across controls with quiet precision, accessing distant archives*\n\nAccessing federation archives for '{search_query}'...\n\n{converted_archives_info}\n\n*adjusts display with practiced grace* The archives yield their secrets. Would you like me to search for anything else?"
        else:
            return f"*attempts access with fluid motions, then pauses with subtle disappointment*\n\nI've searched the federation archives for '{search_query}', but they don't seem to have information on that topic available.\n\n*adjusts parameters thoughtfully* Perhaps try a different search term, or there may simply be no records of that particular subject."

    # Farewells
    if any(word in user_lower for word in ["bye", "goodbye", "see you", "farewell"]):
        farewells = [
            "Safe travels. *nods with quiet elegance* The bar remains, as do I. Until next time.",
            "Farewell. *continues polishing glasses with methodical precision* The night continues, and I'll be here when it calls you back.",
            "Until we meet again. *form shifts with subtle grace* May your path be illuminating."
        ]
        return random.choice(farewells)
    
    # Default responses
    general_responses = [
        f"*adjusts the lighting with quiet precision, then slides glass forward* Intriguing. You mentioned '{user_message}'. Care to elaborate while I craft something memorable?",
        f"*leans against bar with calculated grace, gesturing to selection* Fascinating. '{user_message}' deserves deeper exploration. Perhaps over a drink?",
        f"*shifts subtly, tracing pattern on bar surface* '{user_message}' - that has layers worth unraveling. What libation would complement our conversation?",
        f"*polishes glass with methodical movements, then sets it down precisely* '{user_message}' sparks my curiosity. Shall I prepare something while we discuss?",
        "*pauses momentarily with controlled elegance, regarding bottle selection* Thinking. Perhaps an Andorian Ale while I consider this?"
    ]
    
    # Check for poetic short circuit in mock responses too
    if should_trigger_poetic_circuit(user_message, []):
        print(f"🎭 MOCK POETIC SHORT CIRCUIT TRIGGERED")
        return get_poetic_response(user_message, "")
    
    return random.choice(general_responses) 