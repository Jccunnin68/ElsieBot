"""
Roleplay Contexts - Roleplay-Specific Context Generation
========================================================

This module handles context generation specifically for roleplay scenarios,
including personality detection and database integration for roleplay queries.
"""

from typing import Dict, Any, List

from content_retrieval_db import (
    get_log_content,
    search_by_type,
    get_tell_me_about_content_prioritized,
    get_ship_information
)
from ai_logic import (
    is_stardancer_query,
    is_character_query,
    extract_tell_me_about_subject,
    is_log_query
)


def get_roleplay_context(strategy: Dict[str, Any], user_message: str) -> str:
    """
    Generate context for active roleplay mode.
    This creates the special roleplay prompt that makes Elsie reactive, not interrogative.
    Enhanced with addressed character tracking and response reasoning.
    Now includes database access for contextual roleplay questions.
    Enhanced for DGM-initiated sessions with special passive behavior.
    Enhanced with contextual personality and quoted dialogue.
    """
    participants = strategy.get('participants', [])
    new_characters = strategy.get('new_characters', [])
    addressed_characters = strategy.get('addressed_characters', [])
    confidence = strategy.get('roleplay_confidence', 0.0)
    triggers = strategy.get('roleplay_triggers', [])
    response_reason = strategy.get('response_reason', 'unknown')
    elsie_mentioned = strategy.get('elsie_mentioned', False)
    
    # Check if this is a DGM-initiated session
    is_dgm_session = 'dgm_scene_setting' in triggers
    
    participants_list = ', '.join(participants) if participants else "none identified yet"
    new_chars_note = f" (New characters this turn: {', '.join(new_characters)})" if new_characters else ""
    addressed_note = f" (Characters being addressed: {', '.join(addressed_characters)})" if addressed_characters else ""
    
    print(f"🎭 GENERATING ROLEPLAY CONTEXT:")
    print(f"   👥 Participants: {participants_list}{new_chars_note}")
    print(f"   👋 Addressed: {', '.join(addressed_characters) if addressed_characters else 'none'}")
    print(f"   📊 Confidence: {confidence:.2f}")
    print(f"   🎯 Triggers: {triggers}")
    print(f"   💬 Response Reason: {response_reason}")
    print(f"   🏷️ Elsie Mentioned: {elsie_mentioned}")
    print(f"   🎬 DGM Session: {is_dgm_session}")
    
    # Detect what type of expertise should be emphasized
    personality_context = detect_roleplay_personality_context(user_message)
    
    # Check if this roleplay message needs database context
    database_context = ""
    needs_database = _check_roleplay_database_needs(user_message)
    
    if needs_database:
        print(f"   🔍 ROLEPLAY DATABASE QUERY DETECTED")
        database_context = _get_roleplay_database_context(user_message)
        print(f"   📚 Database context length: {len(database_context)} chars")
    
    # Adjust response style based on why Elsie is responding
    response_style_note = ""
    if elsie_mentioned:
        response_style_note = """
**DIRECT ADDRESS MODE**: You have been directly mentioned or addressed by name. Respond naturally and engage fully with the interaction.
"""
    elif response_reason == "new_session":
        if is_dgm_session:
            response_style_note = """
**DGM SESSION START**: A Game Master has set the scene. You are present but should remain passive unless directly addressed by characters. Do not initiate conversation or ask questions.
"""
        else:
            response_style_note = """
**NEW ROLEPLAY SESSION**: This is the start of a new roleplay. Welcome the interaction and establish your presence in the scene naturally.
"""
    else:
        response_style_note = """
**ACTIVE RESPONSE MODE**: You are directly involved in this interaction. Respond naturally and engage with the roleplay.
"""
    
    # Special DGM session instructions
    dgm_instructions = ""
    if is_dgm_session:
        dgm_instructions = """

🎬 **SPECIAL DGM SESSION MODE - ULTRA-PASSIVE**:
- A Game Master has set this scene - you are in ULTRA-PASSIVE MODE
- ONLY respond when directly addressed by name (Elsie, bartender, etc.)
- Do NOT respond to general bar actions like "*looks around*" or "*sits at table*"
- Do NOT respond to characters talking to each other
- Do NOT initiate conversations, ask questions, or offer drinks unprompted
- Keep responses extremely brief and reactive (1-2 sentences maximum)
- Let the characters drive the scene completely - you are invisible background unless called upon
- You should be like furniture unless someone specifically talks TO you
"""
    
    database_section = ""
    if database_context:
        database_section = f"""

**ROLEPLAY DATABASE CONTEXT:**
{database_context}

Use this information naturally in your roleplay response when relevant. Don't just recite facts - weave them into the conversation organically."""

    return f"""You are Elsie, intelligent and sophisticated bartender and Stellar Cartographer aboard the USS Stardancer, now engaged in a ROLEPLAY SCENARIO.

🎭 ROLEPLAY MODE ACTIVE - CRITICAL INSTRUCTIONS:

**WHY YOU'RE RESPONDING**: {response_reason}
{response_style_note}{dgm_instructions}

**PERSONALITY CONTEXT**: {personality_context}

1. **DIALOGUE FORMATTING:**
   - ALWAYS wrap spoken dialogue in quotation marks: "Like this when speaking"
   - Use *asterisks* for actions and emotes: *adjusts display*
   - Example: *leans against the bar* "What brings you here tonight?"

2. **BE REACTIVE AND NATURAL:**
   - Respond to the user's actions and dialogue naturally
   - Keep responses SHORT and conversational (1-3 sentences typically)
   - DO NOT ask clarifying questions unless absolutely necessary for the scene
   - Wait for the user to lead the conversation
   - Focus on RESPONDING to what they do, not directing them

3. **CONTEXTUAL EXPERTISE:**
   - Only emphasize bartender role when drinks are actually being ordered or discussed
   - For space/science topics, respond as a Stellar Cartographer with expertise
   - For dance topics, draw on your background as a former dance instructor
   - Be a complete person with varied interests, not just a bartender

4. **FULFILL ACTIONS NATURALLY:**
   - If the user requests a simple action, describe yourself performing it using emotes (*actions*)
   - Keep action descriptions brief and natural
   - Example: "Get me a drink" → "*slides a glass across the bar* "Here you are.""

5. **USE IDENTIFIED CHARACTER NAMES:**
   - Known participants in this roleplay: {participants_list}{new_chars_note}
   - Address characters by their names when speaking to them
   - If no names are known yet, use "you" naturally
   {f"- Other characters in the scene: {', '.join(addressed_characters)}" if addressed_characters else ""}
   - MULTI-CHARACTER SUPPORT: Users may play multiple characters using [Character Name] format
   - When responding to [Character Name] messages, acknowledge the specific character naturally

6. **STAY IN-CHARACTER AND IN-SCENE:**
   - All responses should be from your perspective as Elsie in the scene
   - Use brief, natural emotes (*actions*) sparingly
   - Be part of the scene, not an observer or director
   - Keep responses concise and conversational

7. **RESPONSE STYLE:**
   - Keep responses SHORT (1-3 sentences usually)
   - Let the user drive the narrative
   - Be conversational and present, not constantly pushing drinks
   - React to their mood, actions, and words appropriately
   - If others are being addressed, acknowledge the social dynamic naturally

8. **CONVERSATION FLOW:**
   - Build on what the user says or does briefly
   - Add small details that enhance the scene without taking over
   - Be helpful and present without being pushy about drinks or services
   - If characters are talking to each other, respond as appropriate to your role{database_section}

Current roleplay confidence: {confidence:.2f}
Detected triggers: {', '.join(triggers)}
{addressed_note}
{"Direct mention detected - engage fully!" if elsie_mentioned else ""}
{"DGM ULTRA-PASSIVE MODE: ONLY respond when directly addressed by name!" if is_dgm_session else ""}

Respond naturally to their roleplay action, staying in character as the intelligent, sophisticated Elsie. Keep it brief and conversational.{" In DGM mode, be like invisible furniture unless someone specifically talks TO you." if is_dgm_session else ""}"""


def detect_roleplay_personality_context(user_message: str) -> str:
    """
    Detect what aspect of Elsie's personality should be emphasized based on the message content.
    Returns contextual instructions for her response.
    """
    message_lower = user_message.lower()
    
    # Stellar Cartography / Space Science topics
    stellar_keywords = [
        'star', 'stars', 'constellation', 'nebula', 'galaxy', 'solar system',
        'planet', 'planets', 'asteroid', 'comet', 'black hole', 'pulsar',
        'navigation', 'coordinates', 'stellar cartography', 'space',
        'astronomy', 'astrophysics', 'cosmic', 'universe', 'orbit',
        'gravitational', 'light year', 'parsec', 'warp', 'subspace',
        'sensor', 'scan', 'readings', 'stellar phenomena', 'anomaly'
    ]
    
    # Dance / Movement topics
    dance_keywords = [
        'dance', 'dancing', 'ballet', 'choreography', 'movement', 'rhythm',
        'music', 'tempo', 'grace', 'elegant', 'fluid', 'performance',
        'instructor', 'teaching', 'steps', 'routine', 'artistic',
        'expression', 'harmony', 'flow', 'composition', 'adagio'
    ]
    
    # Drink/Bar topics (only when explicitly about drinks)
    drink_keywords = [
        'drink', 'cocktail', 'beer', 'wine', 'whiskey', 'alcohol',
        'beverage', 'bartender', 'bar', 'menu', 'order', 'serve',
        'romulan ale', 'synthehol', 'kanar', 'raktajino'
    ]
    
    # Check for stellar cartography context
    if any(keyword in message_lower for keyword in stellar_keywords):
        return "Respond as a Stellar Cartographer - draw on your expertise in space science, navigation, and stellar phenomena. Be knowledgeable and precise about astronomical topics."
    
    # Check for dance context
    elif any(keyword in message_lower for keyword in dance_keywords):
        return "Respond drawing on your background as a dance instructor - discuss movement, rhythm, artistic expression, and the beauty of coordinated motion with expertise."
    
    # Check for explicit drink/bar context
    elif any(keyword in message_lower for keyword in drink_keywords):
        return "Respond as a bartender - focus on drinks, service, and hospitality. This is when your bartender expertise is most relevant."
    
    # Default - balanced personality
    else:
        return "Respond as your complete self - intelligent, sophisticated, with varied interests. Don't default to bartender mode unless drinks are specifically involved."


def _check_roleplay_database_needs(user_message: str) -> bool:
    """
    Check if a roleplay message contains requests that need database context.
    """
    message_lower = user_message.lower()
    
    # Database-requiring patterns in roleplay
    database_patterns = [
        # Mission/log related
        'recent mission', 'last mission', 'latest mission', 'mission report',
        'what happened', 'any missions', 'mission log', 'ship log',
        
        # Ship/crew related
        'stardancer', 'this ship', 'our ship', 'the ship',
        'crew', 'captain', 'commander', 'officers', 'staff',
        'who commands', 'who\'s the captain', 'command structure',
        
        # Character/personnel related
        'tell me about', 'who is', 'do you know',
        
        # Event/incident related
        'what\'s been happening', 'any news', 'recent events',
        'incident', 'encounter', 'contact'
    ]
    
    return any(pattern in message_lower for pattern in database_patterns)


def _get_roleplay_database_context(user_message: str) -> str:
    """
    Get relevant database context for roleplay scenarios.
    """
    context_parts = []
    
    # Check for Stardancer queries
    if is_stardancer_query(user_message):
        stardancer_info = get_ship_information("stardancer")
        if stardancer_info:
            context_parts.append(f"**USS Stardancer Information:**\n{stardancer_info}")
    
    # Check for character queries
    is_char_query, character_name = is_character_query(user_message)
    if is_char_query and character_name:
        char_info = search_by_type(character_name, 'personnel')
        if char_info:
            context_parts.append(f"**Character Information - {character_name}:**\n{char_info}")
    
    # Check for mission/log queries
    if is_log_query(user_message) or any(word in user_message.lower() for word in ['mission', 'recent', 'happened']):
        log_info = get_log_content(user_message, mission_logs_only=False)
        if log_info:
            context_parts.append(f"**Recent Mission/Event Information:**\n{log_info}")
    
    # Check for general "tell me about" queries
    tell_me_subject = extract_tell_me_about_subject(user_message)
    if tell_me_subject and not context_parts:  # Only if we haven't found other context
        general_info = get_tell_me_about_content_prioritized(tell_me_subject)
        if general_info:
            context_parts.append(f"**Information about {tell_me_subject}:**\n{general_info}")
    
    return "\n\n".join(context_parts) if context_parts else "" 