"""
Conversation Utilities
======================

This module contains utilities for formatting and cleaning text,
primarily for post-processing AI responses and pre-processing user input.
"""
import re

def convert_to_third_person_emotes(text: str) -> str:
    """
    Converts first-person emotes to third-person.
    Example: *I smile* -> *smiles*
    """
    def replace_emote(match):
        emote_content = match.group(1)
        # Simple rule: if it starts with "I ", remove it and add 's' if the next word is a verb.
        # This is a basic implementation.
        if emote_content.lower().startswith('i '):
            verb = emote_content[2:].split(' ')[0]
            # A very naive check for verbs. A more robust solution would use NLP.
            if verb.endswith(('e', 's', 'h', 'x', 'z')):
                return f"*{verb}es*"
            else:
                return f"*{verb}s*"
        return match.group(0) # Return original if no "I"

    return re.sub(r'\*([^*]+)\*', replace_emote, text)


def strip_discord_emojis(text: str) -> str:
    """
    Strips custom Discord emojis from a string.
    Example: "Hello <:wave:12345> world" -> "Hello world"
    """
    return re.sub(r'<a?:\w+:\d+>', '', text).strip()