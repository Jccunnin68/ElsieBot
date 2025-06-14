"""
Context Gatherer - Rich Context Analysis System
===============================================

This module analyzes all available information about the current situation
to build comprehensive contextual cues for Elsie's intelligent decision making.
"""

import re
from typing import Dict, List, Optional, TYPE_CHECKING, Tuple

from .contextual_cues import (
    ElsieContextualCues, SessionMode, SceneControlLevel, PersonalityMode,
    CharacterProfile, ConversationDynamics, AddressingContext,
    create_character_profile
)

if TYPE_CHECKING:
    from .state_manager import RoleplayStateManager


# Known character database for USS Stardancer
STARDANCER_CREW = {
    "tavi": create_character_profile(
        "Tavi", 
        relationship="close_friend",
        personality_notes="Daughter of legendary Captain Marcus Antonius and Doctor Dahlia Delancy. Driven, sometimes struggles with expectations. Cadet. Magna Roman which means she speaks latin and english and follows Roman customs at home, though she lives on earth",
        role="cadet",
        preferences={"drink": "wine", "mood": "thoughtful"}
    ),
    "maeve": create_character_profile(
        "Maeve",
        relationship="close_friend", 
        personality_notes="Captain Blaine's daughter, warm and friendly. Good friend of Elsie's. Her mother Niaev has a neurlogical disease that forces her to live in a pod and is unable to leave it. She is a good friend of Elsie's and is a good friend of Tavi's",
        role="cadet",
        preferences={"drink": "Mojito", "mood": "cheerful"}
    ),
    "zarina": create_character_profile(
        "Zarina",
        relationship="special_affection",
        personality_notes="Beryxian-Vulcan hybrid, daughter of legendary Captain T'pang. Logical but with emotional depth. Elsie likes her very much.",
        role="cadet", 
        preferences={"drink": "vulcan_tea", "mood": "confused due to her hybrid nature"}
    ),
    "marcus": create_character_profile(
        "Marcus",
        relationship="captain",
        personality_notes="Captain Marcus Blaine, commanding officer of USS Stardancer. Professional but caring leader.",
        role="captain",
        preferences={"drink": "bourbon", "mood": "authoritative"}
    ),
    "sif": create_character_profile(
        "Sif",
        relationship="role_model",
        personality_notes="Executive Officer, role model for all holograms and artificial life. Respected and admired.",
        role="commander",
        preferences={"drink": "none she's a hologram", "mood": "professional"}
    ),
    "shay": create_character_profile(
        "Shay",
        relationship="colleague",
        personality_notes="Lt Commander Shay Daly, second officer and Gyndroid. Understanding of artificial life.",
        role="lt_commander",
        preferences={"drink": "none she's an android", "mood": "technical"}
    ),
    "luka": create_character_profile(
        "Luka",
        relationship="debtor",
        personality_notes="Chief Engineer, Ferengi woman who owes Elsie money. Complex relationship.",
        role="chief_engineer",
        preferences={"drink": "root beer", "mood": "engineering"}
    ),
}


def build_contextual_cues(user_message: str, rp_state: 'RoleplayStateManager', turn_number: int) -> ElsieContextualCues:
    """
    Main function to gather all available context and build comprehensive cues.
    This replaces the fragmented if-statement logic with holistic analysis.
    """
    print(f"🧠 BUILDING CONTEXTUAL CUES for turn {turn_number}")
    
    # Base session context
    session_mode = _determine_session_mode(rp_state)
    scene_control = _determine_scene_control_level(rp_state)
    scene_setting = _determine_scene_setting(rp_state)
    
    # Character analysis
    current_speaker = _extract_current_speaker(user_message)
    known_characters = _get_known_characters_context(rp_state.get_participant_names())
    
    # Conversation analysis
    conversation_dynamics = _analyze_conversation_dynamics(user_message, rp_state)
    addressing_context = _analyze_addressing_context(user_message, rp_state)
    
    # Elsie's state
    personality_mode = _determine_personality_mode(user_message, conversation_dynamics)
    expertise = _determine_relevant_expertise(user_message, conversation_dynamics)
    
    # Database context
    relevant_knowledge = _gather_relevant_knowledge(user_message, known_characters)
    character_knowledge = _gather_character_knowledge(current_speaker, known_characters)
    
    cues = ElsieContextualCues(
        # Session Context
        session_mode=session_mode,
        session_type=_get_session_type(rp_state),
        scene_setting=scene_setting,
        scene_control=scene_control,
        
        # Character Context
        known_characters=known_characters,
        active_participants=rp_state.get_participant_names(),
        current_speaker=current_speaker,
        last_addressed_by_elsie=rp_state.last_character_elsie_addressed,
        
        # Conversation Analysis
        conversation_dynamics=conversation_dynamics,
        addressing_context=addressing_context,
        
        # Elsie's State
        personality_mode=personality_mode,
        current_expertise=expertise,
        relationship_context=_build_relationship_context(known_characters),
        
        # Database Context
        relevant_knowledge=relevant_knowledge,
        character_knowledge=character_knowledge,
        
        # Turn Context
        turn_number=turn_number,
        recent_activity=_gather_recent_activity(rp_state)
    )
    
    print(f"   📊 CONTEXTUAL CUES BUILT:")
    print(f"      - Session: {session_mode.value} ({scene_control.value})")
    print(f"      - Speaker: {current_speaker}")
    print(f"      - Known characters: {list(known_characters.keys())}")
    print(f"      - Addressing: Direct={len(addressing_context.direct_mentions)}, Group={addressing_context.group_addressing}")
    print(f"      - Conversation: {conversation_dynamics.themes}, tone={conversation_dynamics.emotional_tone}")
    print(f"      - Personality mode: {personality_mode.value}")
    
    return cues


def _determine_session_mode(rp_state: 'RoleplayStateManager') -> SessionMode:
    """Determine the current session mode"""
    if not rp_state.is_roleplaying:
        return SessionMode.LISTENING
    elif rp_state.is_dgm_session():
        return SessionMode.DGM_ROLEPLAY
    elif rp_state.is_thread_based():
        return SessionMode.THREAD_ROLEPLAY
    else:
        return SessionMode.REGULAR_ROLEPLAY


def _determine_scene_control_level(rp_state: 'RoleplayStateManager') -> SceneControlLevel:
    """Determine appropriate scene control level"""
    if not rp_state.is_roleplaying:
        return SceneControlLevel.PASSIVE
    elif rp_state.is_dgm_session():
        return SceneControlLevel.SELECTIVE  # DGM-compatible mode
    elif rp_state.listening_mode:
        return SceneControlLevel.PASSIVE
    else:
        return SceneControlLevel.ACTIVE


def _determine_scene_setting(rp_state: 'RoleplayStateManager') -> str:
    """Determine current scene setting"""
    # TODO: Could be enhanced to detect scene from conversation
    return "Ten Forward Bar aboard USS Stardancer"


def _get_session_type(rp_state: 'RoleplayStateManager') -> str:
    """Get session type string"""
    if rp_state.is_dgm_session():
        return "dgm_initiated"
    elif rp_state.is_thread_based():
        return "thread"
    else:
        return "player_initiated"


def _extract_current_speaker(user_message: str) -> Optional[str]:
    """Extract the current speaker from the message"""
    from .character_tracking import extract_current_speaker
    return extract_current_speaker(user_message)


def _get_known_characters_context(participants: List[str]) -> Dict[str, CharacterProfile]:
    """Get character profiles for known participants"""
    known_chars = {}
    
    for participant in participants:
        participant_lower = participant.lower()
        if participant_lower in STARDANCER_CREW:
            known_chars[participant] = STARDANCER_CREW[participant_lower]
        else:
            # Create basic profile for unknown characters
            known_chars[participant] = create_character_profile(
                participant, 
                relationship="acquaintance",
                personality_notes="Recently met character"
            )
    
    return known_chars


def _analyze_conversation_dynamics(user_message: str, rp_state: 'RoleplayStateManager') -> ConversationDynamics:
    """Analyze the current conversation dynamics"""
    
    # Extract themes from message and conversation memory
    themes = _extract_conversation_themes(user_message, rp_state)
    
    # Analyze emotional tone
    emotional_tone = _analyze_emotional_tone(user_message)
    
    # Determine conversation direction
    direction = _determine_conversation_direction(user_message, rp_state)
    
    # Analyze intensity and intimacy
    intensity = _analyze_conversation_intensity(user_message)
    intimacy_level = _analyze_intimacy_level(user_message, rp_state)
    
    # Gather recent events
    recent_events = _extract_recent_events(rp_state)
    
    return ConversationDynamics(
        themes=themes,
        emotional_tone=emotional_tone,
        direction=direction,
        intensity=intensity,
        intimacy_level=intimacy_level,
        recent_events=recent_events
    )


def _analyze_addressing_context(user_message: str, rp_state: 'RoleplayStateManager') -> AddressingContext:
    """Analyze how Elsie is being addressed or should respond"""
    
    # Check for direct mentions of Elsie
    direct_mentions = _extract_elsie_mentions(user_message)
    
    # Check for group addressing
    group_addressing = _check_group_addressing(user_message)
    
    # Extract service requests
    service_requests = _extract_service_requests(user_message)
    
    # Check for implicit response opportunity
    implicit_opportunity = _check_implicit_opportunity(user_message, rp_state)
    
    # Analyze other character interactions
    other_interactions = _analyze_other_interactions(user_message, rp_state)
    
    return AddressingContext(
        direct_mentions=direct_mentions,
        group_addressing=group_addressing,
        service_requests=service_requests,
        implicit_opportunity=implicit_opportunity,
        other_interactions=other_interactions
    )


def _determine_personality_mode(user_message: str, conversation_dynamics: ConversationDynamics) -> PersonalityMode:
    """Determine which aspect of Elsie's personality should be emphasized"""
    
    message_lower = user_message.lower()
    themes = conversation_dynamics.themes
    
    # Check for stellar cartography topics
    stellar_keywords = ['star', 'navigation', 'stellar', 'cartography', 'space', 'coordinates', 'galaxy']
    if any(keyword in message_lower for keyword in stellar_keywords) or 'stellar_cartography' in themes:
        return PersonalityMode.STELLAR_CARTOGRAPHER
    
    # Check for service/bar topics
    bar_keywords = ['drink', 'bar', 'service', 'order', 'beverage']
    if any(keyword in message_lower for keyword in bar_keywords) or 'bar_service' in themes:
        return PersonalityMode.BARTENDER
    
    # Check for emotional/counseling topics
    emotional_keywords = ['feel', 'emotion', 'trouble', 'problem', 'difficult', 'support']
    if any(keyword in message_lower for keyword in emotional_keywords) or conversation_dynamics.emotional_tone in ['sad', 'troubled', 'emotional']:
        return PersonalityMode.COUNSELOR
    
    return PersonalityMode.BALANCED


def _determine_relevant_expertise(user_message: str, conversation_dynamics: ConversationDynamics) -> List[str]:
    """Determine what expertise areas are relevant"""
    expertise = []
    message_lower = user_message.lower()
    
    if any(keyword in message_lower for keyword in ['star', 'navigation', 'space', 'galaxy']):
        expertise.append("stellar_cartography")
    
    if any(keyword in message_lower for keyword in ['drink', 'cocktail', 'beverage']):
        expertise.append("bartending")
    
    if any(keyword in message_lower for keyword in ['dance', 'music', 'art']):
        expertise.append("dance_instruction")
    
    if any(keyword in message_lower for keyword in ['ship', 'crew', 'mission']):
        expertise.append("ship_operations")
    
    return expertise


def _extract_conversation_themes(user_message: str, rp_state: 'RoleplayStateManager') -> List[str]:
    """Extract themes from the current message and conversation history"""
    themes = []
    message_lower = user_message.lower()
    
    # Analyze current message
    if any(word in message_lower for word in ['drink', 'bar', 'service', 'beverage']):
        themes.append('bar_service')
    
    if any(word in message_lower for word in ['ship', 'mission', 'crew', 'duty']):
        themes.append('ship_operations')
    
    if any(word in message_lower for word in ['feel', 'emotion', 'personal', 'difficult']):
        themes.append('emotional_support')
    
    if any(word in message_lower for word in ['star', 'space', 'navigation', 'galaxy']):
        themes.append('stellar_cartography')
    
    if any(word in message_lower for word in ['training', 'academy', 'learn']):
        themes.append('training')
    
    # Add themes from conversation memory if available
    if rp_state.has_conversation_memory():
        memory_themes = rp_state.conversation_memory.conversation_themes
        themes.extend([theme for theme in memory_themes if theme not in themes])
    
    return themes


def _analyze_emotional_tone(user_message: str) -> str:
    """Analyze the emotional tone of the message"""
    message_lower = user_message.lower()
    
    # Check for specific emotional indicators
    if any(word in message_lower for word in ['sad', 'upset', 'down', 'depressed', 'trouble']):
        return "sad"
    elif any(word in message_lower for word in ['happy', 'excited', 'great', 'wonderful', 'amazing']):
        return "happy"
    elif any(word in message_lower for word in ['angry', 'mad', 'frustrated', 'annoyed']):
        return "frustrated"
    elif any(word in message_lower for word in ['tired', 'exhausted', 'weary']):
        return "tired"
    elif any(word in message_lower for word in ['nervous', 'anxious', 'worried']):
        return "anxious"
    elif any(word in message_lower for word in ['thank', 'appreciate', 'grateful']):
        return "grateful"
    else:
        return "neutral"


def _determine_conversation_direction(user_message: str, rp_state: 'RoleplayStateManager') -> str:
    """Determine the direction of the conversation"""
    message_lower = user_message.lower()
    
    # Check for conversation starters
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        return "opening"
    
    # Check for conversation enders
    if any(word in message_lower for word in ['goodbye', 'bye', 'see you', 'leaving', 'farewell']):
        return "concluding"
    
    # Check for deepening conversation
    if any(word in message_lower for word in ['tell me', 'explain', 'what about', 'how do you']):
        return "deepening"
    
    # Check for questions (often deepening)
    if '?' in user_message:
        return "exploring"
    
    return "continuing"


def _analyze_conversation_intensity(user_message: str) -> str:
    """Analyze the intensity level of the conversation"""
    message_lower = user_message.lower()
    
    # High intensity indicators
    if any(word in message_lower for word in ['urgent', 'emergency', 'critical', 'important', '!!']):
        return "high"
    
    # Low intensity indicators  
    if any(word in message_lower for word in ['casual', 'just wondering', 'by the way', 'maybe']):
        return "low"
    
    return "moderate"


def _analyze_intimacy_level(user_message: str, rp_state: 'RoleplayStateManager') -> str:
    """Analyze the intimacy level of the conversation"""
    message_lower = user_message.lower()
    
    # Personal/intimate indicators
    if any(word in message_lower for word in ['personal', 'private', 'secret', 'feel like', 'emotional']):
        return "personal"
    
    # Professional indicators
    if any(word in message_lower for word in ['report', 'duty', 'official', 'commander', 'captain']):
        return "professional"
    
    # Very intimate indicators
    if any(word in message_lower for word in ['love', 'relationship', 'intimate', 'deeply']):
        return "intimate"
    
    return "casual"


def _extract_recent_events(rp_state: 'RoleplayStateManager') -> List[str]:
    """Extract recent events from conversation memory"""
    events = []
    
    if rp_state.has_conversation_memory():
        recent_turns = rp_state.conversation_memory.get_recent_history(3)
        for turn in recent_turns:
            # Extract significant events from recent messages
            if '*' in turn.message:  # Actions in asterisks
                actions = re.findall(r'\*([^*]+)\*', turn.message)
                events.extend([f"{turn.speaker}: {action}" for action in actions])
    
    return events[-5:]  # Keep only most recent 5 events


def _extract_elsie_mentions(user_message: str) -> List[str]:
    """Extract how Elsie is mentioned in the message"""
    mentions = []
    message_lower = user_message.lower()
    
    # Direct name mentions
    if 'elsie' in message_lower:
        mentions.append("name_mention")
    
    # Role mentions
    if any(word in message_lower for word in ['bartender', 'barkeep']):
        mentions.append("role_mention")
    
    # Direct addressing
    if re.search(r'\belsie[,\s]', message_lower):
        mentions.append("direct_address")
    
    return mentions


def _check_group_addressing(user_message: str) -> bool:
    """Check if message contains group addressing"""
    message_lower = user_message.lower()
    group_patterns = [
        'everyone', 'everybody', 'you all', 'y\'all', 'all of you',
        'hey everyone', 'hello all', 'good morning everyone'
    ]
    return any(pattern in message_lower for pattern in group_patterns)


def _extract_service_requests(user_message: str) -> List[str]:
    """Extract service requests from the message"""
    from .response_logic import _is_subtle_bar_service_needed
    
    requests = []
    
    # Check for drink orders
    if _is_subtle_bar_service_needed(user_message):
        requests.append("drink_service")
    
    # Check for other service requests
    message_lower = user_message.lower()
    if any(word in message_lower for word in ['help', 'assist', 'service']):
        requests.append("general_service")
    
    return requests


def _check_implicit_opportunity(user_message: str, rp_state: 'RoleplayStateManager') -> bool:
    """Check if there's an implicit response opportunity"""
    return rp_state.is_simple_implicit_response(rp_state.turn_history[-1][0] + 1 if rp_state.turn_history else 1, user_message)


def _analyze_other_interactions(user_message: str, rp_state: 'RoleplayStateManager') -> List[Tuple[str, str]]:
    """Analyze interactions between other characters"""
    from .response_logic import check_if_other_character_addressed
    
    interactions = []
    current_speaker = _extract_current_speaker(user_message)
    other_character = check_if_other_character_addressed(user_message, rp_state)
    
    if current_speaker and other_character:
        interactions.append((current_speaker, other_character))
    
    return interactions


def _build_relationship_context(known_characters: Dict[str, CharacterProfile]) -> Dict[str, str]:
    """Build relationship context mapping"""
    context = {}
    for name, profile in known_characters.items():
        context[name] = profile.relationship
    return context


def _gather_relevant_knowledge(user_message: str, known_characters: Dict[str, CharacterProfile]) -> List[str]:
    """Gather relevant knowledge from database context"""
    # TODO: Integrate with database context system
    knowledge = []
    
    message_lower = user_message.lower()
    
    # Add knowledge based on message content
    if 'stardancer' in message_lower:
        knowledge.append("USS Stardancer is exploring the Large Magellanic Cloud")
    
    if any(name.lower() in message_lower for name in known_characters.keys()):
        knowledge.append("Character relationship information available")
    
    return knowledge


def _gather_character_knowledge(current_speaker: Optional[str], known_characters: Dict[str, CharacterProfile]) -> Dict[str, str]:
    """Gather specific knowledge about the current speaker"""
    knowledge = {}
    
    if current_speaker and current_speaker in known_characters:
        profile = known_characters[current_speaker]
        knowledge[current_speaker] = f"Relationship: {profile.relationship}, Role: {profile.role}, Notes: {profile.personality_notes}"
    
    return knowledge


def _gather_recent_activity(rp_state: 'RoleplayStateManager') -> List[str]:
    """Gather recent activity information"""
    activity = []
    
    if rp_state.has_conversation_memory():
        recent_turns = rp_state.conversation_memory.get_recent_history(2)
        for turn in recent_turns:
            activity.append(f"Turn {turn.turn_number}: {turn.speaker}")
    
    return activity 