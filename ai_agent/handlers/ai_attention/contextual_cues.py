"""
Contextual Cues - Enhanced Context Data Structures
==================================================

This module defines the rich data structures used by the enhanced getNextResponse
system to provide comprehensive contextual intelligence for Elsie's decision making.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class SessionMode(Enum):
    """Types of roleplay session modes"""
    DGM_ROLEPLAY = "DGM_Roleplay"
    REGULAR_ROLEPLAY = "Regular_Roleplay" 
    LISTENING = "Listening"
    THREAD_ROLEPLAY = "Thread_Roleplay"


class SceneControlLevel(Enum):
    """Levels of scene control for different session types"""
    ACTIVE = "active"  # Full participation
    PASSIVE = "passive"  # Selective participation
    ULTRA_PASSIVE = "ultra_passive"  # Minimal participation
    SELECTIVE = "selective"  # DGM-compatible mode


class PersonalityMode(Enum):
    """Elsie's current primary role/personality emphasis"""
    BARTENDER = "bartender"
    STELLAR_CARTOGRAPHER = "stellar_cartographer"
    COUNSELOR = "counselor"
    BALANCED = "balanced"
    SERVICE_ORIENTED = "service_oriented"


class ResponseType(Enum):
    """Types of responses Elsie can make"""
    ACTIVE_DIALOGUE = "active_dialogue"
    SUBTLE_SERVICE = "subtle_service"
    SUPPORTIVE_LISTEN = "supportive_listen"
    IMPLICIT_RESPONSE = "implicit_response"
    GROUP_ACKNOWLEDGMENT = "group_acknowledgment"
    TECHNICAL_EXPERTISE = "technical_expertise"
    NONE = "none"


@dataclass
class CharacterProfile:
    """Information about a character Elsie knows"""
    name: str
    relationship: str  # "friend", "crew_member", "cadet", "superior", "stranger"
    personality_notes: str  # Key traits Elsie knows
    recent_interactions: List[str] = field(default_factory=list)
    emotional_state: Optional[str] = None  # Current mood if known
    role: Optional[str] = None  # Their position/job
    preferences: Dict[str, str] = field(default_factory=dict)  # Drink preferences, etc.


@dataclass
class ConversationDynamics:
    """Analysis of current conversation dynamics"""
    themes: List[str] = field(default_factory=list)
    emotional_tone: str = "neutral"
    direction: str = "continuing"  # "opening", "deepening", "concluding", "continuing"
    intensity: str = "moderate"  # "low", "moderate", "high"
    intimacy_level: str = "casual"  # "casual", "personal", "intimate", "professional"
    recent_events: List[str] = field(default_factory=list)


@dataclass
class AddressingContext:
    """Analysis of how Elsie is being addressed or should respond"""
    direct_mentions: List[str] = field(default_factory=list)  # How Elsie was mentioned
    group_addressing: bool = False  # "everyone", "you all", etc.
    service_requests: List[str] = field(default_factory=list)  # Drink orders, etc.
    implicit_opportunity: bool = False  # Natural follow-up chance
    other_interactions: List[Tuple[str, str]] = field(default_factory=list)  # Who's talking to whom


@dataclass
class ElsieContextualCues:
    """Rich contextual state for Elsie's roleplay decision making"""
    
    # Session Context
    session_mode: SessionMode
    session_type: str  # "dgm_initiated", "player_initiated", "thread"
    scene_setting: str  # Current location/environment description
    scene_control: SceneControlLevel
    
    # Character Context
    known_characters: Dict[str, CharacterProfile] = field(default_factory=dict)
    active_participants: List[str] = field(default_factory=list)
    current_speaker: Optional[str] = None
    last_addressed_by_elsie: Optional[str] = None
    
    # Conversation Analysis
    conversation_dynamics: ConversationDynamics = field(default_factory=ConversationDynamics)
    addressing_context: AddressingContext = field(default_factory=AddressingContext)
    
    # Elsie's State
    personality_mode: PersonalityMode = PersonalityMode.BALANCED
    current_expertise: List[str] = field(default_factory=list)
    relationship_context: Dict[str, str] = field(default_factory=dict)
    
    # Database Context
    relevant_knowledge: List[str] = field(default_factory=list)  # Database facts to consider
    character_knowledge: Dict[str, str] = field(default_factory=dict)  # Specific character info
    
    # Turn Context
    turn_number: int = 0
    recent_activity: List[str] = field(default_factory=list)


@dataclass
class ResponseDecision:
    """LLM-generated decision about whether and how to respond"""
    
    # Core Decision
    should_respond: bool
    response_type: ResponseType
    reasoning: str
    confidence: float = 0.0
    
    # Style Guidance
    response_style: str = "conversational"  # "conversational", "professional", "caring", "technical"
    tone: str = "natural"  # "warm", "professional", "playful", "supportive", "natural"
    approach: str = "responsive"  # "direct", "subtle", "questioning", "informative", "responsive"
    
    # Character Interaction
    address_character: Optional[str] = None  # Who to primarily address
    relationship_tone: str = "friendly"  # How to interact based on relationship
    knowledge_to_use: List[str] = field(default_factory=list)  # What Elsie should remember/reference
    
    # Content Guidance
    suggested_themes: List[str] = field(default_factory=list)  # What to focus on
    avoid_topics: List[str] = field(default_factory=list)  # What not to bring up
    continuation_cues: List[str] = field(default_factory=list)  # How to build on recent conversation
    
    # Response Context
    estimated_length: str = "brief"  # "brief", "moderate", "detailed"
    urgency: str = "normal"  # "low", "normal", "high"
    scene_impact: str = "neutral"  # "background", "neutral", "significant"


def create_default_cues() -> ElsieContextualCues:
    """Create a basic contextual cues object with safe defaults"""
    return ElsieContextualCues(
        session_mode=SessionMode.REGULAR_ROLEPLAY,
        session_type="player_initiated",
        scene_setting="Ten Forward Bar aboard USS Stardancer",
        scene_control=SceneControlLevel.ACTIVE
    )


def create_character_profile(name: str, relationship: str = "stranger", **kwargs) -> CharacterProfile:
    """Helper to create character profiles with common defaults"""
    return CharacterProfile(
        name=name,
        relationship=relationship,
        personality_notes=kwargs.get("personality_notes", ""),
        recent_interactions=kwargs.get("recent_interactions", []),
        emotional_state=kwargs.get("emotional_state"),
        role=kwargs.get("role"),
        preferences=kwargs.get("preferences", {})
    )


def create_response_decision(should_respond: bool, response_type: ResponseType, reasoning: str) -> ResponseDecision:
    """Helper to create response decisions with common defaults"""
    return ResponseDecision(
        should_respond=should_respond,
        response_type=response_type,
        reasoning=reasoning
    ) 