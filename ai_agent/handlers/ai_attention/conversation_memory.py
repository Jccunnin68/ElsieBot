"""
Conversation Memory - Advanced Conversation Context Analysis
===========================================================

This module provides sophisticated conversation memory management for Elsie's
roleplay mode, analyzing recent conversation history to suggest response styles
and maintain conversational continuity.
"""

import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import re

from ..ai_logic.response_decision import ResponseDecision


@dataclass
class ConversationTurn:
    """Represents a single turn in conversation history."""
    speaker: str
    message: str
    turn_number: int
    timestamp: float
    message_type: str = "standard"  # standard, emote, dialogue, mixed
    addressed_to: Optional[str] = None
    tone: Optional[str] = None
    themes: List[str] = None
    
    def __post_init__(self):
        if self.themes is None:
            self.themes = []


@dataclass
class ResponseSuggestion:
    """Represents an LLM-generated response style suggestion."""
    style: str
    tone: str
    approach: str
    themes: List[str]
    confidence: float
    reasoning: str
    conversation_direction: str
    character_dynamics: List[str]
    
    def __post_init__(self):
        if self.themes is None:
            self.themes = []
        if self.character_dynamics is None:
            self.character_dynamics = []


class ConversationMemory:
    """
    Manages conversation memory for roleplay sessions.
    Stores recent conversation history and LLM-generated response suggestions.
    """
    
    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.history: List[ConversationTurn] = []
        self.response_suggestions: Dict[int, ResponseSuggestion] = {}
        self.conversation_themes: List[str] = []
        self.active_dynamics: List[str] = []
        self.last_analysis_turn: int = 0
        
    def add_turn(self, speaker: str, message: str, turn_number: int, 
                 addressed_to: Optional[str] = None, message_type: str = "standard"):
        """Add a new conversation turn to memory."""
        turn = ConversationTurn(
            speaker=speaker,
            message=message,
            turn_number=turn_number,
            timestamp=time.time(),
            message_type=message_type,
            addressed_to=addressed_to
        )
        
        self.history.append(turn)
        
        # Maintain max history limit
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        print(f"   💭 CONVERSATION MEMORY: Added turn {turn_number} by {speaker}")
        print(f"      - Message type: {message_type}")
        print(f"      - Addressed to: {addressed_to or 'general'}")
        print(f"      - History length: {len(self.history)}")
    
    def get_recent_history(self, count: Optional[int] = None) -> List[ConversationTurn]:
        """Get recent conversation history."""
        if count is None:
            return self.history.copy()
        return self.history[-count:] if count <= len(self.history) else self.history.copy()
    
    def get_conversation_context_string(self) -> str:
        """Format recent conversation history as a string for LLM analysis."""
        if not self.history:
            return ""
        
        context_lines = []
        for turn in self.history:
            speaker_label = f"[{turn.speaker}]" if turn.speaker != "User" else "[Player]"
            addressed_note = f" (to {turn.addressed_to})" if turn.addressed_to else ""
            context_lines.append(f"{speaker_label}{addressed_note}: {turn.message}")
        
        return "\n".join(context_lines)
    
    def has_sufficient_context(self) -> bool:
        """Check if we have enough conversation history for meaningful analysis."""
        return len(self.history) >= 2
    
    def get_last_suggestion(self) -> Optional[ResponseSuggestion]:
        """Get the most recent response suggestion."""
        if not self.response_suggestions:
            return None
        latest_turn = max(self.response_suggestions.keys())
        return self.response_suggestions[latest_turn]
    
    def clear_memory(self):
        """Clear all conversation memory (called when roleplay session ends)."""
        self.history.clear()
        self.response_suggestions.clear()
        self.conversation_themes.clear()
        self.active_dynamics.clear()
        self.last_analysis_turn = 0
        print(f"   🧹 CONVERSATION MEMORY: Cleared all memory")


def getNextResponse(conversation_history: List[Dict[str, Any]], 
                   memory_store: ConversationMemory,
                   character_context: Optional[Dict[str, Any]] = None) -> Tuple[ResponseSuggestion, bool]:
    """
    Core subroutine to analyze conversation and suggest response characteristics.
    
    This doesn't generate the actual response - it analyzes conversation flow
    and suggests the style/approach Elsie should use for her response.
    
    Args:
        conversation_history: List of recent conversation turns
        memory_store: ConversationMemory instance to update
        character_context: Optional context about Elsie's character state
        
    Returns:
        (ResponseSuggestion, should_analyze_now): Tuple of suggestion and whether to analyze
    """
    
    # Check if we have enough context for analysis
    if not memory_store.has_sufficient_context():
        print(f"   💭 CONVERSATION ANALYSIS: Insufficient context ({len(memory_store.history)} turns)")
        # Return default suggestion
        default_suggestion = ResponseSuggestion(
            style="contextual",
            tone="natural",
            approach="responsive",
            themes=[],
            confidence=0.5,
            reasoning="Insufficient conversation history for detailed analysis",
            conversation_direction="continuing",
            character_dynamics=[]
        )
        return default_suggestion, False
    
    # Check if we need fresh analysis (every 2 turns or when context changes significantly)  
    current_turn = conversation_history[-1].get('turn_number', 0) if conversation_history else 0
    needs_analysis = (
        current_turn - memory_store.last_analysis_turn >= 2 or 
        memory_store.last_analysis_turn == 0
    )
    
    if not needs_analysis:
        # Return cached suggestion if recent
        cached_suggestion = memory_store.get_last_suggestion()
        if cached_suggestion:
            print(f"   💭 CONVERSATION ANALYSIS: Using cached suggestion (confidence: {cached_suggestion.confidence:.2f})")
            return cached_suggestion, False
    
    print(f"   💭 CONVERSATION ANALYSIS: Analyzing conversation flow...")
    
    # Format conversation for analysis
    conversation_context = memory_store.get_conversation_context_string()
    
    # Generate response suggestion using LLM analysis
    try:
        suggestion = _analyze_conversation_with_llm(conversation_context, character_context)
        
        # Store the suggestion
        memory_store.response_suggestions[current_turn] = suggestion
        memory_store.last_analysis_turn = current_turn
        
        # Update conversation themes
        memory_store.conversation_themes = list(set(memory_store.conversation_themes + suggestion.themes))
        memory_store.active_dynamics = suggestion.character_dynamics
        
        print(f"   💭 CONVERSATION ANALYSIS: Generated suggestion")
        print(f"      - Style: {suggestion.style}")
        print(f"      - Tone: {suggestion.tone}")  
        print(f"      - Approach: {suggestion.approach}")
        print(f"      - Confidence: {suggestion.confidence:.2f}")
        print(f"      - Direction: {suggestion.conversation_direction}")
        print(f"      - Themes: {suggestion.themes}")
        
        return suggestion, True
        
    except Exception as e:
        print(f"   ❌ CONVERSATION ANALYSIS ERROR: {e}")
        # Return fallback suggestion
        fallback_suggestion = ResponseSuggestion(
            style="natural",
            tone="friendly", 
            approach="responsive",
            themes=[],
            confidence=0.3,
            reasoning=f"Analysis failed: {str(e)}",
            conversation_direction="continuing",
            character_dynamics=[]
        )
        return fallback_suggestion, False


def _analyze_conversation_with_llm(conversation_context: str, 
                                 character_context: Optional[Dict[str, Any]] = None) -> ResponseSuggestion:
    """
    Analyze conversation using LLM to generate response suggestions.
    This is a placeholder for the actual LLM integration.
    """
    
    # For now, provide rule-based analysis
    # TODO: Replace with actual LLM API call
    
    print(f"   🤖 LLM ANALYSIS: Analyzing conversation context...")
    print(f"      - Context length: {len(conversation_context)} chars")
    
    # Simple analysis based on conversation patterns
    context_lower = conversation_context.lower()
    
    # Detect conversation style
    style = "contextual"
    if "*" in conversation_context:  # Contains emotes
        style = "emotive"
    elif '"' in conversation_context:  # Contains dialogue
        style = "conversational"
    elif any(word in context_lower for word in ['orders', 'requests', 'drink', 'service']):
        style = "service_oriented"
    
    # Detect tone
    tone = "natural"
    if any(word in context_lower for word in ['happy', 'excited', 'great', 'wonderful']):
        tone = "upbeat"
    elif any(word in context_lower for word in ['sad', 'tired', 'difficult', 'problem']):
        tone = "supportive"
    elif any(word in context_lower for word in ['thank', 'please', 'appreciate']):
        tone = "warm"
    
    # Detect approach
    approach = "responsive"
    if "?" in conversation_context:
        approach = "answering"
    elif any(word in context_lower for word in ['tell me', 'what about', 'explain']):
        approach = "informative"
    elif any(word in context_lower for word in ['hello', 'hi', 'hey']):
        approach = "welcoming"
    
    # Detect themes
    themes = []
    if any(word in context_lower for word in ['drink', 'bar', 'service']):
        themes.append("bar_service")
    if any(word in context_lower for word in ['ship', 'mission', 'crew']):
        themes.append("ship_operations")
    if any(word in context_lower for word in ['dance', 'music', 'art']):
        themes.append("artistic")
    if any(word in context_lower for word in ['star', 'space', 'navigation']):
        themes.append("stellar_cartography")
    
    # Detect conversation direction
    direction = "continuing"
    if any(word in context_lower for word in ['goodbye', 'see you', 'leaving']):
        direction = "concluding"
    elif any(word in context_lower for word in ['hello', 'hi', 'greetings']):
        direction = "opening"
    elif "?" in conversation_context:
        direction = "exploring"
    
    # Create suggestion
    suggestion = ResponseSuggestion(
        style=style,
        tone=tone,
        approach=approach,
        themes=themes,
        confidence=0.75,  # Rule-based analysis confidence
        reasoning="Rule-based analysis of conversation patterns",
        conversation_direction=direction,
        character_dynamics=[]  # TODO: Detect character dynamics
    )
    
    return suggestion


def extract_conversation_metadata(message: str) -> Dict[str, Any]:
    """
    Extract metadata from a message (type, addressed_to, themes).
    """
    metadata = {
        'message_type': 'standard',
        'addressed_to': None,
        'has_emotes': False,
        'has_dialogue': False,
        'themes': []
    }
    
    # Detect message type
    has_emotes = '*' in message
    has_dialogue = '"' in message
    
    if has_emotes and has_dialogue:
        metadata['message_type'] = 'mixed'
    elif has_emotes:
        metadata['message_type'] = 'emote'
    elif has_dialogue:
        metadata['message_type'] = 'dialogue'
    
    metadata['has_emotes'] = has_emotes
    metadata['has_dialogue'] = has_dialogue
    
    # TODO: Extract addressed_to from message patterns
    # TODO: Extract themes from message content
    
    return metadata


def format_conversation_for_context(memory_store: ConversationMemory, 
                                  include_analysis: bool = True) -> str:
    """
    Format conversation memory for inclusion in roleplay context.
    """
    if not memory_store.history:
        return ""
    
    lines = ["**Recent Conversation Context:**"]
    
    # Add recent turns
    for turn in memory_store.get_recent_history():
        speaker_label = f"[{turn.speaker}]" if turn.speaker != "User" else "[Player]"
        lines.append(f"{speaker_label}: {turn.message}")
    
    # Add analysis if available and requested
    if include_analysis:
        suggestion = memory_store.get_last_suggestion()
        if suggestion:
            lines.append("")
            lines.append("**Conversation Analysis:**")
            lines.append(f"- Style: {suggestion.style}")
            lines.append(f"- Tone: {suggestion.tone}")
            lines.append(f"- Direction: {suggestion.conversation_direction}")
            if suggestion.themes:
                lines.append(f"- Themes: {', '.join(suggestion.themes)}")
            lines.append(f"- Suggested approach: {suggestion.approach}")
    
    return "\n".join(lines)


def track_elsie_response(response_text: str, turn_number: int, memory_store: ConversationMemory, addressed_to: Optional[str] = None):
    """
    Track Elsie's response in conversation memory.
    This should be called after Elsie generates a response.
    Enhanced to track who Elsie is addressing for implicit response logic.
    """
    if not response_text or not memory_store:
        return
    
    # Extract who Elsie might be addressing from her response
    if not addressed_to:
        addressed_to = _extract_addressed_character_from_response(response_text)
    
    # Add Elsie's response to conversation memory
    memory_store.add_turn(
        speaker="Elsie",
        message=response_text,
        turn_number=turn_number,
        addressed_to=addressed_to,
        message_type="response"
    )
    
    print(f"   💭 ELSIE RESPONSE TRACKED: Turn {turn_number}")
    print(f"      - Response length: {len(response_text)} chars")
    print(f"      - Addressed to: {addressed_to or 'general'}")
    print(f"      - Memory size: {len(memory_store.history)} turns")





def _get_relationship_tone(speaker: Optional[str], known_characters: Dict[str, Any]) -> str:
    """Get appropriate relationship tone for addressing a character"""
    if not speaker or speaker not in known_characters:
        return "friendly"
    
    relationship = known_characters[speaker].relationship
    
    if relationship in ["close_friend", "special_affection"]:
        return "warm"
    elif relationship in ["captain", "superior"]:
        return "respectful"
    elif relationship in ["colleague", "crew_member"]:
        return "professional"
    elif relationship == "debtor":
        return "slightly_teasing"
    else:
        return "friendly"


def _extract_addressed_character_from_response(response_text: str) -> Optional[str]:
    """
    Extract who Elsie is addressing from her response text.
    This helps with implicit response tracking.
    """
    # Look for direct addressing patterns in Elsie's response
    addressing_patterns = [
        r'^([A-Z][a-z]+),\s',  # "Name, ..."
        r'\b([A-Z][a-z]+),?\s+(?:what|how|why|where|when)',  # "Name, what..."
        r'\*[^*]*(?:turns? to|looks? at|speaks? to|addresses?)\s+([A-Z][a-z]+)',  # Emote addressing
        r'"[^"]*([A-Z][a-z]+)[^"]*"',  # Character name in dialogue (less reliable)
    ]
    
    for pattern in addressing_patterns:
        match = re.search(pattern, response_text)
        if match:
            character_name = match.group(1)
            # Filter out common words that aren't character names
            if character_name.lower() not in ['the', 'and', 'but', 'for', 'you', 'your']:
                print(f"   👤 ADDRESSED CHARACTER DETECTED: {character_name}")
                return character_name
    
    return None


def get_global_conversation_tracker():
    """
    Get the global conversation tracker for use in response callbacks.
    This allows other modules to track Elsie's responses without circular imports.
    """
    from .state_manager import get_roleplay_state
    rp_state = get_roleplay_state()
    if rp_state.is_roleplaying:
        return rp_state.conversation_memory
    return None 