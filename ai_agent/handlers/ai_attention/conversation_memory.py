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
    
    def process_message_enhanced(self, user_message: str, turn_number: int, 
                               conversation_history: List, channel_context: Dict) -> Dict:
        """
        LLM-enhanced message processing for roleplay routing decisions.
        Uses Gemma to determine optimal response approach before routing.
        
        Args:
            user_message: The current user message
            turn_number: Current turn number
            conversation_history: Previous conversation turns
            channel_context: Channel and context information
            
        Returns:
            Dict with processing_approach, contextual_cues, routing_confidence, etc.
        """
        print(f"   🤖 LLM-ENHANCED MESSAGE PROCESSING: Turn {turn_number}")
        
        try:
            # Build conversation context
            conversation_context = self.get_conversation_context_string()
            
            # Get roleplay state for context
            from .state_manager import get_roleplay_state
            rp_state = get_roleplay_state()
            
            # Build roleplay state context
            roleplay_context = {
                'is_roleplaying': rp_state.is_roleplaying,
                'participants': rp_state.get_participant_names(),
                'last_speaker': getattr(rp_state, 'last_speaker', None),
                'is_dgm_session': rp_state.is_dgm_session(),
                'listening_mode': getattr(rp_state, 'listening_mode', False)
            }
            
            # Get LLM routing decision
            routing_decision = self._get_llm_routing_decision(
                user_message, conversation_context, roleplay_context, channel_context
            )
            
            # Build contextual cues using existing system
            from .context_gatherer import build_contextual_cues
            contextual_cues = build_contextual_cues(user_message, rp_state, turn_number)
            
            print(f"      🎯 LLM Routing: {routing_decision['approach']} (confidence: {routing_decision['confidence']:.2f})")
            print(f"      💭 Reasoning: {routing_decision['reasoning']}")
            
            return {
                'processing_approach': routing_decision['approach'],
                'contextual_cues': contextual_cues,
                'routing_confidence': routing_decision['confidence'],
                'suggested_response_type': routing_decision['response_type'],
                'reasoning': routing_decision['reasoning'],
                'needs_database': routing_decision.get('needs_database', False),
                'priority_level': routing_decision.get('priority_level', 'medium')
            }
            
        except Exception as e:
            print(f"      ❌ LLM routing error: {e}")
            # Fallback to basic processing
            return self._get_fallback_routing_decision(user_message, turn_number)
    
    def _get_llm_routing_decision(self, user_message: str, conversation_context: str,
                                roleplay_context: Dict, channel_context: Dict) -> Dict:
        """Use Gemma LLM to make intelligent routing decisions."""
        
        try:
            from config import GEMMA_API_KEY
        except ImportError:
            GEMMA_API_KEY = None
        
        if not GEMMA_API_KEY:
            print(f"      ⚠️  No Gemma API key - using fallback routing")
            return self._get_rule_based_routing(user_message, roleplay_context)
        
        try:
            # Create the model
            import google.generativeai as genai
            genai.configure(api_key=GEMMA_API_KEY)
            model = genai.GenerativeModel('gemma-3-27b-it')
            
            # Create routing prompt
            prompt = self._create_routing_prompt(user_message, conversation_context, roleplay_context)
            
            # Get LLM response
            response = model.generate_content(prompt)
            
            if response and response.text:
                # Parse JSON response
                import json
                try:
                    result = json.loads(response.text.strip())
                    
                    # Validate required fields
                    required_fields = ['approach', 'confidence', 'response_type', 'reasoning']
                    if all(field in result for field in required_fields):
                        return result
                    else:
                        print(f"      ⚠️  LLM response missing fields: {response.text}")
                        return self._get_rule_based_routing(user_message, roleplay_context)
                        
                except json.JSONDecodeError as e:
                    print(f"      ⚠️  LLM response not valid JSON: {response.text}")
                    return self._get_rule_based_routing(user_message, roleplay_context)
            else:
                print(f"      ⚠️  Empty LLM response")
                return self._get_rule_based_routing(user_message, roleplay_context)
                
        except Exception as e:
            print(f"      ❌ LLM API error: {e}")
            return self._get_rule_based_routing(user_message, roleplay_context)
    
    def _create_routing_prompt(self, user_message: str, conversation_context: str,
                             roleplay_context: Dict) -> str:
        """Create optimized prompt for routing decisions."""
        
        participants_str = ", ".join(roleplay_context.get('participants', [])) or "none"
        
        return f"""You are Elsie's response routing intelligence. Analyze this roleplay situation and determine the optimal response approach.

ROLEPLAY CONTEXT:
- Session Active: {roleplay_context.get('is_roleplaying', False)}
- Participants: {participants_str}
- Last Speaker: {roleplay_context.get('last_speaker', 'unknown')}
- DGM Session: {roleplay_context.get('is_dgm_session', False)}
- Listening Mode: {roleplay_context.get('listening_mode', False)}

RECENT CONVERSATION:
{conversation_context if conversation_context else "No recent conversation history"}

CURRENT MESSAGE: "{user_message}"

ROUTING OPTIONS:
1. roleplay_active - Direct engagement, full participation
2. roleplay_supportive - Emotional support, listening mode  
3. roleplay_service - Bar service, professional interaction
4. roleplay_technical - Technical expertise, information sharing
5. roleplay_group - Group addressing, social interaction
6. roleplay_listening - Passive observation, minimal response
7. roleplay_fallback - Safe fallback for unclear situations

RESPONSE TYPES:
- active_dialogue - Direct conversation engagement
- supportive_listen - Emotional support and listening
- subtle_service - Bar service and professional tasks
- technical_expertise - Information and expertise sharing
- group_acknowledgment - Group social interaction
- none - No response needed

Respond with ONLY valid JSON:
{{
    "approach": "roleplay_active",
    "confidence": 0.85,
    "response_type": "active_dialogue", 
    "reasoning": "Character directly addressed Elsie with question",
    "needs_database": false,
    "priority_level": "high"
}}"""

    def _get_rule_based_routing(self, user_message: str, roleplay_context: Dict) -> Dict:
        """Fallback rule-based routing when LLM is unavailable."""
        
        message_lower = user_message.lower()
        
        # Check for direct Elsie mentions
        if any(name in message_lower for name in ['elsie', 'bartender']):
            return {
                'approach': 'roleplay_active',
                'confidence': 0.8,
                'response_type': 'active_dialogue',
                'reasoning': 'Direct mention detected - rule-based fallback',
                'needs_database': False,
                'priority_level': 'high'
            }
        
        # Check for service requests
        if any(word in message_lower for word in ['drink', 'order', 'serve', 'glass']):
            return {
                'approach': 'roleplay_service',
                'confidence': 0.7,
                'response_type': 'subtle_service',
                'reasoning': 'Service request detected - rule-based fallback',
                'needs_database': False,
                'priority_level': 'medium'
            }
        
        # Check for emotional content
        if any(word in message_lower for word in ['sad', 'upset', 'worried', 'trouble', 'help']):
            return {
                'approach': 'roleplay_supportive',
                'confidence': 0.6,
                'response_type': 'supportive_listen',
                'reasoning': 'Emotional content detected - rule-based fallback',
                'needs_database': False,
                'priority_level': 'medium'
            }
        
        # Default to listening mode
        return {
            'approach': 'roleplay_listening',
            'confidence': 0.5,
            'response_type': 'none',
            'reasoning': 'No clear indicators - rule-based fallback to listening',
            'needs_database': False,
            'priority_level': 'low'
        }
    
    def _get_fallback_routing_decision(self, user_message: str, turn_number: int) -> Dict:
        """Emergency fallback when all routing fails."""
        
        # Build basic contextual cues
        from .state_manager import get_roleplay_state
        from .context_gatherer import build_contextual_cues
        
        try:
            rp_state = get_roleplay_state()
            contextual_cues = build_contextual_cues(user_message, rp_state, turn_number)
        except:
            contextual_cues = None
        
        return {
            'processing_approach': 'roleplay_fallback',
            'contextual_cues': contextual_cues,
            'routing_confidence': 0.3,
            'suggested_response_type': 'active_dialogue',
            'reasoning': 'Emergency fallback - all routing methods failed',
            'needs_database': False,
            'priority_level': 'low'
        }








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


 