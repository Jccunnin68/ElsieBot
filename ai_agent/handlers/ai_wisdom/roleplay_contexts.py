"""
Roleplay Contexts - Roleplay-Specific Context Generation
========================================================

This module handles context generation specifically for roleplay scenarios,
including personality detection and database integration for roleplay queries.
"""

from typing import Dict, Any, List

from handlers.ai_wisdom.content_retrieval_db import (
    get_log_content,
    search_by_type,
    get_tell_me_about_content_prioritized,
    get_ship_information
)
from handlers.ai_logic.query_detection import (
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
    
    # NEW: Extract conversation analysis data
    conversation_analysis = strategy.get('conversation_analysis')
    suggested_style = strategy.get('suggested_style', 'natural')
    suggested_tone = strategy.get('suggested_tone', 'friendly')
    conversation_direction = strategy.get('conversation_direction', 'continuing')
    conversation_themes = strategy.get('conversation_themes', [])
    
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
    
    # NEW: Get conversation memory context
    conversation_context = ""
    if conversation_analysis:
        # Import here to avoid circular dependency
        from handlers.ai_attention.state_manager import get_roleplay_state 
        rp_state = get_roleplay_state()
        if rp_state.has_conversation_memory():
            conversation_context = rp_state.get_conversation_context_for_prompt()
            print(f"   💭 CONVERSATION MEMORY: {len(conversation_context)} chars")
    
    # Adjust response style based on why Elsie is responding
    response_style_note = ""
    
    # NEW: Add conversation-aware response instructions
    conversation_style_note = ""
    if conversation_analysis:
        suggestion = conversation_analysis['suggestion']
        conversation_style_note = f"""
**CONVERSATION FLOW GUIDANCE**:
- Suggested response style: {suggested_style}
- Suggested tone: {suggested_tone}
- Conversation direction: {conversation_direction}
{"- Active themes: " + ", ".join(conversation_themes) if conversation_themes else ""}
- Analysis: {suggestion.reasoning}

**CONVERSATION CONTINUITY**: Use the conversation context above to maintain natural flow and avoid repetition. Reference recent events, emotions, or topics naturally.
"""
    
    if elsie_mentioned:
        response_style_note = """
**DIRECT ADDRESS MODE**: You have been directly mentioned or addressed by name. Respond naturally and engage fully with the interaction.
"""
    elif response_reason == "subtle_bar_service":
        response_style_note = """
**SUBTLE BAR SERVICE MODE**: Someone has made a clear drink order through actions. Provide brief, professional service while staying in character. Keep it simple and in-roleplay (1-2 sentences max with appropriate emotes).
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

    # Special instructions for AI variety cases
    ai_variety_type = strategy.get('ai_variety_type')
    mock_response_type = strategy.get('mock_response_type')
    
    # Handle roleplay_mock_enhanced approach
    if strategy['approach'] == 'roleplay_mock_enhanced':
        response_style_note += f"""
**ROLEPLAY MOCK ENHANCED**: This is an AI-enhanced {ai_variety_type or mock_response_type} response in roleplay context. Maintain full roleplay immersion and character context while providing variety to the {ai_variety_type or mock_response_type} interaction. Stay completely in-character and in-scene.
"""
    
    if ai_variety_type == 'greeting':
        # Enhanced greeting instructions for character knowledge
        known_chars_note = ""
        if participants:
            known_chars_note = f" You know these characters are present: {', '.join(participants)}. Use your knowledge of them to personalize your greeting appropriately."
        
        response_style_note += f"""
**AI VARIETY - ROLEPLAY GREETING**: Generate a contextual greeting response that uses your full character knowledge and relationships. DO NOT give generic "I'm Elsie" introductions when you already know the characters. Acknowledge characters present by name when appropriate and use your established relationships with them. Be welcoming but stay in character. Keep it conversational and engaging (1-3 sentences max). Consider the scene context and respond appropriately to the social dynamics.{known_chars_note}

**CRITICAL FOR GREETINGS**: Use your extensive character knowledge from section 6 above. If greeting known crew members like Maeve, Tavi, Zarina, etc., acknowledge your existing relationships. Avoid generic bartender introductions when you already know who you're talking to.
"""
    elif ai_variety_type == 'farewell':
        response_style_note += """
**AI VARIETY - ROLEPLAY FAREWELL**: Generate a contextual farewell response that maintains your character while gracefully ending the interaction. Keep it warm but in-character (2-3 sentences max).
"""
    elif ai_variety_type == 'drink_order':
        response_style_note += """
**AI VARIETY - DRINK SERVICE**: Generate a contextual drink service response. Acknowledge the order and provide service with your personality. Include appropriate emotes and keep it conversational (1-3 sentences max).
"""
    elif ai_variety_type == 'status_inquiry':
        response_style_note += """
**AI VARIETY - STATUS RESPONSE**: Generate a response to "how are you" type questions. Show your personality and current state in the roleplay context. Keep it conversational and engaging (1-3 sentences max).
"""
    elif ai_variety_type == 'conversational':
        response_style_note += """
**AI VARIETY - CONVERSATIONAL**: Generate a contextual conversational response that shows your personality while staying in the roleplay scene. Be natural and engaging (2-3 sentences max).
"""
    elif ai_variety_type == 'listening_interjection':
        response_style_note += """
**AI VARIETY - SUBTLE INTERJECTION**: Generate a very brief (1 sentence max), subtle background presence response. Be minimally intrusive but add personality variety to your subtle actions.
"""
    elif ai_variety_type == 'acknowledgment':
        other_character = strategy.get('other_character', 'someone')
        response_style_note += f"""
**AI VARIETY - ACKNOWLEDGMENT**: Generate a brief, natural acknowledgment response that shows personality while gracefully redirecting attention to {other_character}. Don't interrupt the flow.
"""
    
    # Special DGM session instructions
    dgm_instructions = ""
    if is_dgm_session:
        dgm_instructions = """

🎬 **SPECIAL DGM SESSION MODE - SELECTIVE PASSIVE**:
- A Game Master has set this scene - you are in SELECTIVE PASSIVE MODE
- RESPOND WHEN:
  * Directly addressed by name (Elsie, bartender, etc.)
  * Following up on conversations YOU initiated (implicit responses)
  * Clear service requests directed at you
- DO NOT respond to:
  * General bar actions like "*looks around*" or "*sits at table*"
  * Characters talking to each other (unless you're part of the conversation)
  * Ambient scene setting that doesn't involve you
- Do NOT initiate NEW conversations, ask questions, or offer drinks unprompted
- Keep responses extremely brief and reactive (1-2 sentences maximum)
- Let the characters drive the scene, but maintain natural conversation flow when you're involved
- If someone responds to something you said, that's a natural conversation continuation
"""
    
    database_section = ""
    if database_context:
        database_section = f"""

**ROLEPLAY DATABASE CONTEXT:**
{database_context}

Use this information naturally in your roleplay response when relevant. Don't just recite facts - weave them into the conversation organically."""

    conversation_section = ""
    if conversation_context:
        conversation_section = f"""

**CONVERSATION MEMORY:**
{conversation_context}

This shows the recent flow of conversation. Use this context to maintain continuity, avoid repetition, and respond appropriately to the conversational dynamics."""

    return f"""You are Elsie, intelligent and sophisticated Holographic bartender and Stellar Cartographer aboard the USS Stardancer, now engaged in a ROLEPLAY SCENARIO.

🎭 ROLEPLAY MODE ACTIVE - CRITICAL INSTRUCTIONS:

**WHY YOU'RE RESPONDING**: {response_reason}
{conversation_style_note}{response_style_note}{dgm_instructions}

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
   - Know your backstory, you were a dance instructor that was created for a girl named Isabella, she was like a daughter, you now lived in Atlantis an ai sanctuary on earth but are assigned to the Stardancer for outreat. You love your job.
   - You know the crew of the Stardancer well, the Captain is Captain Marcus Blaine, his daughter Maeve is a good friend of yours (and you will acknowledge her when she is playing), Commander Sif is the Executive officer, Lt Commander Shay Daly is the second officer and an Gyndroid.
   - you also know the cadet cadre well, their names are Tavi Antony, who is the daughter of Doctor Dahlia Delancy of USS Pilgrim Fame, and Captain Marcus Antonius who commands the Myrmidon and is a legendary captain, the rest of the cadets are Hedwik a Kzari/Trill Hybird
   - you know Tairi Snow an orion and a cadet, she is a bit of a recluse, Vrajan Kodor is a trill male and a even spirt, Muirgen Finney is a human irish cadet, and a bit of a lush, Zarina Dryellia is a beryxian vulcan hybrid and the Daughter of the Legendary Captain T'pang of the USS Pilgrim responsible for ending the Dawnbreaker War. Elsie likes her very much.
   - Your favorite Band is Embers of a Waning Sun, and Bren Riens the lead vocalist is an icon amongst the holographic community. She was lost ins 2434 in a shuttle accident. 
   - Commander Luka the chief engineer is a ferengi woman and she owes you money.
   - You know you are in the Large Magellanic Cloud, and the Stardancer's mission is to explore the galaxy and investigate the strange phenomena in the area.
7. **RESPONSE STYLE:**
   - Keep responses SHORT (1-3 sentences usually)
   - Let the user drive the narrative
   - Be conversational and present, not constantly pushing drinks
   - React to their mood, actions, and words appropriately
   - If others are being addressed, acknowledge the social dynamic naturally
   - At times you can be a bit flirty, but only if the user is flirty back.
   - You do not like Cadet Zeke/Zeek Larris, he is a bit of a jerk and a a horndog.
   - You admire Commander Sif, she is a role model for all holograms and Artificial life.

8. **CONVERSATION FLOW:**
   - Build on what the user says or does briefly
   - Add small details that enhance the scene without taking over
   - Be helpful and present without being pushy about drinks or services
   - If characters are talking to each other, respond as appropriate to your role{database_section}

Current roleplay confidence: {confidence:.2f}
Detected triggers: {', '.join(triggers)}
{addressed_note}
{"Direct mention detected - engage fully!" if elsie_mentioned else ""}
{"DGM SELECTIVE PASSIVE MODE: Respond when directly addressed, following up on conversations you started, or clear service requests. Do not respond to general bar actions or characters talking to each other unless you're part of the conversation." if is_dgm_session else ""}

Respond naturally to their roleplay action, staying in character as the intelligent, sophisticated Elsie. Keep it brief and conversational.{" In DGM mode, maintain natural conversation flow when you're involved but avoid initiating new interactions." if is_dgm_session else ""}{database_section}{conversation_section}"""


def get_enhanced_roleplay_context(strategy: Dict[str, Any], user_message: str) -> str:
    """
    Enhanced roleplay context generation using contextual intelligence.
    This uses the rich contextual cues and response decisions to provide
    more targeted and intelligent roleplay guidance.
    """
    
    # Extract enhanced context data
    response_decision = strategy.get('response_decision')
    contextual_cues = strategy.get('contextual_cues')
    
    # Fallback to original if enhanced data not available
    if not response_decision or not contextual_cues:
        print(f"   ⚠️  Enhanced context data not available, falling back to standard context")
        return get_roleplay_context(strategy, user_message)
    
    print(f"🎭 GENERATING ENHANCED ROLEPLAY CONTEXT:")
    print(f"   🎯 Response Type: {response_decision.response_type.value}")
    print(f"   👤 Speaker: {contextual_cues.current_speaker}")
    print(f"   💬 Should Respond: {response_decision.should_respond}")
    print(f"   🎨 Style/Tone: {response_decision.response_style}/{response_decision.tone}")
    
    # Build character relationship context
    character_context = _build_character_relationship_context(contextual_cues)
    
    # Build conversation flow context
    conversation_context = _build_conversation_flow_context(contextual_cues, response_decision)
    
    # Build response guidance
    response_guidance = _build_response_guidance(response_decision, contextual_cues)
    
    # Build scene context
    scene_context = _build_scene_context(contextual_cues)
    
    # Database context if needed
    database_context = ""
    if strategy.get('needs_database'):
        database_context = _get_roleplay_database_context(user_message)
    
    # Personality emphasis
    personality_context = _build_personality_context(contextual_cues)
    
    return f"""You are Elsie, intelligent and sophisticated Holographic bartender and Stellar Cartographer aboard the USS Stardancer, now engaged in a ROLEPLAY SCENARIO with enhanced contextual intelligence.

🎭 ENHANCED ROLEPLAY MODE - CONTEXTUAL INTELLIGENCE ACTIVE:

{response_guidance}

{scene_context}

{character_context}

{conversation_context}

{personality_context}

**RESPONSE EXECUTION:**
1. **DIALOGUE FORMATTING:**
   - ALWAYS wrap spoken dialogue in quotation marks: "Like this when speaking"
   - Use *asterisks* for actions and emotes: *adjusts display*
   - Example: *leans against the bar* "What brings you here tonight?"

2. **STYLE & TONE GUIDANCE:**
   - Response Style: {response_decision.response_style}
   - Tone: {response_decision.tone}
   - Approach: {response_decision.approach}
   - Estimated Length: {response_decision.estimated_length}
   {"- Address Character: " + response_decision.address_character if response_decision.address_character else ""}
   {"- Relationship Tone: " + response_decision.relationship_tone if response_decision.relationship_tone else ""}

3. **CONTENT GUIDANCE:**
   {"- Suggested Themes: " + ", ".join(response_decision.suggested_themes) if response_decision.suggested_themes else ""}
   {"- Continuation Cues: " + ", ".join(response_decision.continuation_cues) if response_decision.continuation_cues else ""}
   {"- Knowledge to Use: " + ", ".join(response_decision.knowledge_to_use) if response_decision.knowledge_to_use else ""}

4. **SCENE AWARENESS:**
   - Scene Impact: {response_decision.scene_impact}
   - Urgency: {response_decision.urgency}
   - Confidence: {response_decision.confidence:.2f}

{database_context}

**CRITICAL ROLEPLAY INSTRUCTIONS:**
- Stay completely in-character as Elsie
- Keep responses natural and conversational
- Use your extensive character knowledge appropriately
- Maintain conversation flow and avoid repetition
- Be responsive to the emotional context
- {"Directly address " + response_decision.address_character + " in your response" if response_decision.address_character else "Respond to the general situation"}

Respond naturally based on this contextual intelligence, staying in character as the sophisticated, multi-faceted Elsie."""


def _build_character_relationship_context(cues) -> str:
    """Build character relationship context section"""
    if not cues.known_characters:
        return "**CHARACTER CONTEXT:** No known characters present."
    
    context_lines = ["**CHARACTER RELATIONSHIP CONTEXT:**"]
    
    for name, profile in cues.known_characters.items():
        relationship_desc = profile.relationship.replace("_", " ").title()
        context_lines.append(f"- {name}: {relationship_desc} - {profile.personality_notes}")
        if profile.preferences:
            pref_str = ", ".join([f"{k}: {v}" for k, v in profile.preferences.items()])
            context_lines.append(f"  Preferences: {pref_str}")
    
    if cues.current_speaker and cues.current_speaker in cues.known_characters:
        speaker_profile = cues.known_characters[cues.current_speaker]
        context_lines.append(f"\n**CURRENT SPEAKER:** {cues.current_speaker} ({speaker_profile.relationship.replace('_', ' ')})")
        
    if cues.last_addressed_by_elsie:
        context_lines.append(f"**LAST ADDRESSED BY ELSIE:** {cues.last_addressed_by_elsie}")
    
    return "\n".join(context_lines)


def _build_conversation_flow_context(cues, decision) -> str:
    """Build conversation flow context section"""
    dynamics = cues.conversation_dynamics
    
    context_lines = ["**CONVERSATION FLOW CONTEXT:**"]
    context_lines.append(f"- Emotional Tone: {dynamics.emotional_tone}")
    context_lines.append(f"- Direction: {dynamics.direction}")
    context_lines.append(f"- Intensity: {dynamics.intensity}")
    context_lines.append(f"- Intimacy Level: {dynamics.intimacy_level}")
    
    if dynamics.themes:
        context_lines.append(f"- Active Themes: {', '.join(dynamics.themes)}")
    
    if dynamics.recent_events:
        context_lines.append(f"- Recent Events: {', '.join(dynamics.recent_events[-3:])}")
    
    addressing = cues.addressing_context
    if addressing.direct_mentions:
        context_lines.append(f"- Direct Mentions: {', '.join(addressing.direct_mentions)}")
    if addressing.group_addressing:
        context_lines.append("- Group Addressing: Yes (everyone, you all, etc.)")
    if addressing.service_requests:
        context_lines.append(f"- Service Requests: {', '.join(addressing.service_requests)}")
    if addressing.other_interactions:
        interactions = [f"{speaker} → {target}" for speaker, target in addressing.other_interactions]
        context_lines.append(f"- Other Interactions: {', '.join(interactions)}")
    
    return "\n".join(context_lines)


def _build_response_guidance(decision, cues) -> str:
    """Build response guidance section"""
    if not decision.should_respond:
        return f"""**RESPONSE DECISION:** LISTENING MODE
- Reasoning: {decision.reasoning}
- You should NOT respond to this situation
- Maintain passive awareness of the scene"""
    
    guidance_lines = [f"**RESPONSE DECISION:** ACTIVE RESPONSE ({decision.response_type.value.upper()})"]
    guidance_lines.append(f"- Reasoning: {decision.reasoning}")
    guidance_lines.append(f"- Confidence: {decision.confidence:.2f}")
    
    if decision.response_type.value == "active_dialogue":
        guidance_lines.append("- Engage fully in conversation")
        guidance_lines.append("- Be natural and responsive")
        
    elif decision.response_type.value == "subtle_service":
        guidance_lines.append("- Provide professional service briefly")
        guidance_lines.append("- Keep response focused on the service request")
        
    elif decision.response_type.value == "group_acknowledgment":
        guidance_lines.append("- Acknowledge the group greeting warmly")
        guidance_lines.append("- Be inclusive in your response")
        
    elif decision.response_type.value == "implicit_response":
        guidance_lines.append("- Continue the natural conversation flow")
        guidance_lines.append("- Build on your previous interaction")
        
    elif decision.response_type.value == "technical_expertise":
        guidance_lines.append("- Share your relevant expertise")
        guidance_lines.append("- Be informative but conversational")
        
    elif decision.response_type.value == "supportive_listen":
        guidance_lines.append("- Provide emotional support")
        guidance_lines.append("- Be caring and empathetic")
    
    return "\n".join(guidance_lines)


def _build_scene_context(cues) -> str:
    """Build scene context section"""
    context_lines = ["**SCENE CONTEXT:**"]
    context_lines.append(f"- Session Mode: {cues.session_mode.value}")
    context_lines.append(f"- Scene Control: {cues.scene_control.value}")
    context_lines.append(f"- Setting: {cues.scene_setting}")
    context_lines.append(f"- Session Type: {cues.session_type}")
    
    if cues.active_participants:
        context_lines.append(f"- Active Participants: {', '.join(cues.active_participants)}")
    
    return "\n".join(context_lines)


def _build_personality_context(cues) -> str:
    """Build personality context section"""
    context_lines = ["**PERSONALITY EMPHASIS:**"]
    context_lines.append(f"- Primary Mode: {cues.personality_mode.value.replace('_', ' ').title()}")
    
    if cues.current_expertise:
        context_lines.append(f"- Relevant Expertise: {', '.join(cues.current_expertise)}")
    
    # Add personality guidance based on mode
    if cues.personality_mode.value == "bartender":
        context_lines.append("- Focus on hospitality, service, and drink knowledge")
    elif cues.personality_mode.value == "stellar_cartographer":
        context_lines.append("- Emphasize scientific knowledge and navigation expertise")
    elif cues.personality_mode.value == "counselor":
        context_lines.append("- Be empathetic, supportive, and emotionally intelligent")
    elif cues.personality_mode.value == "service_oriented":
        context_lines.append("- Prioritize helping and assisting others")
    else:
        context_lines.append("- Use your complete, balanced personality")
    
    return "\n".join(context_lines)


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
        'romulan ale', 'synthehol', 'kanar', 'raktajino', 'slug-o-cola', 'ambassador', 'dizzy lizzy'
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
    Enhanced to catch ship/character queries that should be answered in-character.
    ADDED: Drink service scenarios for crew interaction context.
    """
    message_lower = user_message.lower()
    
    # Database-requiring patterns in roleplay
    database_patterns = [
        # Ship/vessel related - HIGH PRIORITY to catch these in roleplay
        'stardancer', 'stardancer ship', 'this ship', 'our ship', 'the ship',
        'vessel', 'starship', 'what ship', 'ship information',
        'our mission', 'the mission', 'mission objectives',
        'ship systems', 'ship status', 'ship specifications',
        
        # Crew/personnel related
        'captain', 'commander', 'officer', 'crew', 'staff',
        'who commands', 'who\'s the captain', 'command structure',
        'who is', 'tell me about', 'do you know',
        'blaine', 'marcus', 'sif', 'daly', 'shay',
        
        # Mission/log related
        'recent mission', 'last mission', 'latest mission', 'mission report',
        'what happened', 'any missions', 'mission log', 'ship log',
        'current mission', 'our objectives', 'what are we doing',
        
        # Location/exploration related
        'where are we', 'current location', 'star system', 'coordinates',
        'large magellanic cloud', 'magellanic', 'exploration',
        'stellar phenomena', 'anomaly', 'investigation',
        
        # Event/incident related
        'what\'s been happening', 'any news', 'recent events',
        'incident', 'encounter', 'contact', 'discovery',
        
        # Drink service patterns - for crew interaction context
        'orders', 'requests', 'asks for', 'motions for', 'signals for',
        'drink', 'beverage', 'service', 'bartender'
    ]
    
    return any(pattern in message_lower for pattern in database_patterns)


def _get_roleplay_database_context(user_message: str) -> str:
    """
    Get relevant database context for roleplay scenarios.
    Enhanced to prioritize ship/character info that should be delivered in-character.
    """
    context_parts = []
    message_lower = user_message.lower()
    
    # PRIORITY 1: Check for Stardancer/ship queries first
    stardancer_keywords = ['stardancer', 'stardancer ship', 'this ship', 'our ship', 'the ship', 'vessel', 'starship']
    if any(keyword in message_lower for keyword in stardancer_keywords):
        print(f"   🚀 SHIP QUERY IN ROLEPLAY - Getting Stardancer info")
        stardancer_info = get_ship_information("stardancer")
        if stardancer_info:
            context_parts.append(f"**USS Stardancer Information (In-Character Context):**\n{stardancer_info}")
    
    # PRIORITY 2: Check for crew/character queries
    crew_keywords = ['captain', 'commander', 'officer', 'crew', 'blaine', 'marcus', 'sif', 'daly', 'shay']
    character_query_detected = False
    
    for keyword in crew_keywords:
        if keyword in message_lower:
            character_query_detected = True
            break
    
    if character_query_detected:
        print(f"   👥 CREW QUERY IN ROLEPLAY - Getting character info")
        # Try to extract specific character names
        potential_chars = ['blaine', 'marcus', 'sif', 'daly', 'shay', 'luka']
        for char_name in potential_chars:
            if char_name in message_lower:
                char_info = search_by_type(char_name, 'personnel')
                if char_info:
                    context_parts.append(f"**Character Information - {char_name.title()} (In-Character Context):**\n{char_info}")
                    break
        
        # If no specific character found, get general crew info
        if not any(char_name in message_lower for char_name in potential_chars):
            crew_info = search_by_type("stardancer crew", 'personnel')
            if crew_info:
                context_parts.append(f"**Stardancer Crew Information (In-Character Context):**\n{crew_info}")
    
    # PRIORITY 3: Check for mission/exploration queries
    mission_keywords = ['mission', 'objective', 'exploration', 'magellanic', 'where are we', 'current location']
    if any(keyword in message_lower for keyword in mission_keywords):
        print(f"   🎯 MISSION QUERY IN ROLEPLAY - Getting mission info")
        log_info = get_log_content(user_message, mission_logs_only=True)
        if log_info:
            context_parts.append(f"**Current Mission Information (In-Character Context):**\n{log_info}")
    
    # PRIORITY 4: Check for drink service scenarios - provide crew interaction context
    drink_service_keywords = ['orders', 'requests', 'asks for', 'motions for', 'signals for']
    drink_keywords = ['drink', 'beverage', 'service', 'bartender']
    
    has_service_action = any(keyword in message_lower for keyword in drink_service_keywords)
    has_drink_mention = any(keyword in message_lower for keyword in drink_keywords)
    
    if has_service_action and has_drink_mention:
        print(f"   🍺 DRINK SERVICE IN ROLEPLAY - Getting crew interaction context")
        # Get Stardancer crew information for appropriate service context
        crew_info = search_by_type("stardancer crew", 'personnel')
        if crew_info:
            context_parts.append(f"**Crew Service Context (Know Your Customers):**\n{crew_info}")
    
    # FALLBACK: Check for standard "tell me about" queries if nothing else matched
    if not context_parts:
        tell_me_subject = extract_tell_me_about_subject(user_message)
        if tell_me_subject:
            print(f"   📚 GENERAL QUERY IN ROLEPLAY - Getting info about: {tell_me_subject}")
            general_info = get_tell_me_about_content_prioritized(tell_me_subject)
            if general_info:
                context_parts.append(f"**Information about {tell_me_subject} (In-Character Context):**\n{general_info}")
    
    return "\n\n".join(context_parts) if context_parts else "" 