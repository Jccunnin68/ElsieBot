"""
Conversation Emotions - Conversation-Level Emotional Intelligence
===============================================================

This module provides conversation-level emotional intelligence that can analyze
emotional context across multiple conversation turns and build emotional memory
to improve response accuracy and empathy.

Key Features:
- Multi-turn emotional context tracking
- Emotional relationship building over time
- Conversation emotional arc analysis
- Enhanced empathy response generation
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .emotional_analysis import EmotionalTone, EmotionalContext


class ConversationMood(Enum):
    """Overall conversation mood states"""
    SUPPORTIVE = "supportive"
    CELEBRATORY = "celebratory" 
    PROBLEM_SOLVING = "problem_solving"
    CASUAL_FRIENDLY = "casual_friendly"
    PROFESSIONAL = "professional"
    INTIMATE_PERSONAL = "intimate_personal"
    NEUTRAL = "neutral"


@dataclass
class ConversationTurn:
    """A single turn in conversation with emotional context"""
    speaker: str
    message: str
    emotional_context: EmotionalContext
    timestamp: datetime
    turn_number: int
    addressed_to: Optional[str] = None
    support_provided: bool = False


@dataclass
class EmotionalRelationship:
    """Emotional relationship state between Elsie and a character"""
    character_name: str
    trust_level: float = 0.5  # 0.0 to 1.0
    comfort_level: float = 0.5  # 0.0 to 1.0
    support_history: List[str] = field(default_factory=list)
    conversation_count: int = 0
    last_interaction: Optional[datetime] = None


class ConversationEmotionalIntelligence:
    """
    Main class for conversation-level emotional intelligence.
    
    This tracks emotional context across conversation turns and builds
    emotional relationships over time.
    """
    
    def __init__(self):
        self.character_relationships: Dict[str, EmotionalRelationship] = {}
        self.emotional_memory: List[ConversationTurn] = []
        self.max_memory_turns = 50  # Keep last 50 turns in memory
    
    def detect_emotional_support_opportunity_enhanced(self, current_message: str,
                                                    conversation_history: List[Dict]) -> Tuple[bool, float, str]:
        """
        Enhanced emotional support detection using conversation-level intelligence.
        
        This uses the full conversation context to make better decisions about
        when emotional support is needed.
        """
        from .emotional_analysis import detect_emotional_support_opportunity
        
        # Basic emotional support detection
        basic_needs_support, basic_confidence = detect_emotional_support_opportunity(
            current_message, {}
        )
        
        # Enhanced analysis using conversation context
        enhancement_factors = []
        confidence_bonus = 0.0
        
        # Check for repeated emotional distress in recent conversation
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Last 3 messages
            emotional_count = 0
            for msg in recent_messages:
                content = msg.get('content', '').lower()
                if any(word in content for word in ['trouble', 'difficult', 'struggling', 'worried', 'anxious']):
                    emotional_count += 1
            
            if emotional_count >= 2:
                confidence_bonus += 0.2
                enhancement_factors.append("repeated emotional content in conversation")
        
        # Check for vulnerability patterns
        if any(pattern in current_message.lower() for pattern in ["i'm having trouble", "everyone's expectations", "can't handle"]):
            confidence_bonus += 0.15
            enhancement_factors.append("vulnerability expression patterns")
        
        # Calculate final confidence
        enhanced_confidence = min(0.95, basic_confidence + confidence_bonus)
        enhanced_needs_support = enhanced_confidence >= 0.4
        
        reasoning = f"Basic: {basic_confidence:.2f}, enhanced: {enhanced_confidence:.2f}"
        if enhancement_factors:
            reasoning += f" ({', '.join(enhancement_factors)})"
        
        print(f"   🔍 ENHANCED SUPPORT DETECTION:")
        print(f"      - Basic confidence: {basic_confidence:.2f}")
        print(f"      - Enhanced confidence: {enhanced_confidence:.2f}")
        print(f"      - Enhancement factors: {enhancement_factors}")
        
        return enhanced_needs_support, enhanced_confidence, reasoning
    
    def get_empathy_response_guidance(self, target_character: str, 
                                    emotional_context: Dict) -> Dict[str, str]:
        """
        Get guidance for crafting an empathetic response based on emotional context.
        """
        if target_character in self.character_relationships:
            relationship = self.character_relationships[target_character]
        else:
            # Create new relationship
            relationship = EmotionalRelationship(character_name=target_character)
            self.character_relationships[target_character] = relationship
        
        # Determine guidance based on relationship and context
        guidance = {
            'approach': self._determine_empathy_approach(relationship, emotional_context),
            'tone': self._determine_response_tone(emotional_context),
            'style': self._determine_response_style(relationship),
            'support_style': 'balanced'
        }
        
        return guidance
    
    def _determine_empathy_approach(self, relationship: EmotionalRelationship, 
                                   emotional_context: Dict) -> str:
        """Determine the best empathy approach"""
        emotional_tone = emotional_context.get('emotional_tone', 'neutral')
        
        if relationship.trust_level > 0.7:
            return "direct_caring"
        elif emotional_tone in ['vulnerable', 'overwhelmed']:
            return "gentle_supportive"
        elif emotional_tone == 'frustrated':
            return "validating_understanding"
        else:
            return "warm_professional"
    
    def _determine_response_tone(self, emotional_context: Dict) -> str:
        """Determine appropriate response tone"""
        emotional_tone = emotional_context.get('emotional_tone', 'neutral')
        
        if emotional_tone in ['sad', 'anxious', 'overwhelmed']:
            return "gentle"
        elif emotional_tone == 'happy':
            return "upbeat"
        else:
            return "warm"
    
    def _determine_response_style(self, relationship: EmotionalRelationship) -> str:
        """Determine appropriate response style"""
        if relationship.conversation_count > 5:
            return "familiar_friendly"
        else:
            return "professional_warm"
