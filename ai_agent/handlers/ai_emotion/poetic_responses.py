"""
Poetic Response Circuit for Elsie
=================================

This module handles Elsie's "poetic short circuit" moments - beautiful, 
esoteric responses that replace normal casual dialogue occasionally.
"""

import random
from typing import List


def should_trigger_poetic_circuit(user_message: str, conversation_history: list) -> bool:
    """
    Determine if Elsie should have a poetic 'short circuit' moment.
    These happen during casual dialogue, not during information requests.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation context
        
    Returns:
        True if a poetic response should be triggered (15% chance for eligible messages)
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


def get_poetic_response(user_message: str, original_response: str = "") -> str:
    """
    Generate an extremely esoteric, poetic response that replaces normal casual dialogue.
    These should be beautiful, mysterious, and deeply artistic.
    
    Args:
        user_message: The user's message (for context)
        original_response: The original response that would have been given
        
    Returns:
        A beautiful, poetic response with action formatting
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