"""
Context Sensitivity - Advanced Pattern Recognition
=================================================

This module provides context-sensitive pattern recognition to distinguish
between different types of addressing and contextual mentions. This is crucial
for resolving conflicts between emotional support and group addressing detection.

Key functionality:
- Distinguish between direct group addressing vs contextual mentions
- Enhanced intimacy analysis with relationship context
- Sophisticated phrase pattern recognition
- Context-aware confidence scoring
"""

import re
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class AddressingType(Enum):
    """Types of addressing patterns"""
    DIRECT_GROUP = "direct_group"          # "Good morning everyone!"
    CONTEXTUAL_MENTION = "contextual_mention"  # "everyone's expectations"
    INDIVIDUAL_ADDRESS = "individual_address"   # "Hey John"
    NO_ADDRESSING = "no_addressing"        # No addressing detected


class ContextSensitivity(Enum):
    """Context sensitivity levels"""
    HIGH = "high"       # Clear contextual indicators
    MEDIUM = "medium"   # Some contextual indicators  
    LOW = "low"         # Minimal context
    NONE = "none"       # No context available


@dataclass
class AddressingAnalysis:
    """Results of addressing pattern analysis"""
    addressing_type: AddressingType
    confidence: float
    context_sensitivity: ContextSensitivity
    matched_patterns: List[str]
    contextual_indicators: List[str]
    reasoning: str


def distinguish_group_vs_contextual(message: str) -> Tuple[str, float]:
    """
    Distinguish between direct group addressing and contextual group mentions.
    
    This is the core function that fixes the emotional support misclassification issue.
    It determines whether "everyone" refers to addressing everyone or talking about everyone.
    
    Args:
        message: The message to analyze
        
    Returns:
        (addressing_type, confidence): Type and confidence score
    """
    message_lower = message.lower()
    
    # Special handling for the problematic case: "everyone's expectations"
    if re.search(r"everyone(?:\'s)?\s+expectations?", message_lower):
        print(f"   🎯 SPECIAL CASE DETECTED: 'everyone's expectations' → contextual mention")
        return "contextual_mention", 0.9
    
    # Direct group addressing patterns
    direct_group_patterns = [
        r'\b(good (morning|afternoon|evening)|hello|hi|hey) everyone\b',
        r'\beveryone[,!]?\s+(please|listen|attention)',
        r'\byou all\b(?!\s+(know|think|understand))',
    ]
    
    # Contextual mention patterns
    contextual_patterns = [
        r'\beveryone(?:\'s)?\s+(expectations?|opinion|view)',
        r'\beveryone expects\b',
        r'\bwhat everyone (thinks?|says?|believes?)',
        r'\beveryone (was|were|has|had)',
    ]
    
    # Check patterns
    for pattern in direct_group_patterns:
        if re.search(pattern, message_lower):
            return "direct_group", 0.8
    
    for pattern in contextual_patterns:
        if re.search(pattern, message_lower):
            return "contextual_mention", 0.8
    
    return "no_addressing", 0.6


def analyze_conversation_intimacy_enhanced(message: str, relationships: Dict) -> Tuple[str, float]:
    """
    Enhanced intimacy analysis that considers relationship context and emotional content.
    
    This helps determine when emotional content is likely to be shared based on
    the intimacy level of the conversation and existing relationships.
    """
    message_lower = message.lower()
    
    # Base intimacy indicators
    intimacy_indicators = {
        'intimate': [
            'personal', 'private', 'between us', 'confidential', 'secret',
            'deeply', 'intimate', 'vulnerable', 'exposed', 'raw'
        ],
        'personal': [
            'feel', 'feeling', 'emotional', 'struggle', 'difficulty', 'trouble',
            'worried', 'scared', 'anxious', 'overwhelmed', 'pressure',
            'expectations', 'failing', 'can\'t handle', 'don\'t know'
        ],
        'casual': [
            'by the way', 'just wondering', 'maybe', 'perhaps', 'might',
            'casual', 'quick question', 'simple', 'basic'
        ],
        'professional': [
            'report', 'duty', 'official', 'commander', 'captain', 'mission',
            'orders', 'protocol', 'procedure', 'regulation'
        ]
    }
    
    # Score each intimacy level
    intimacy_scores = {}
    for level, indicators in intimacy_indicators.items():
        score = sum(1 for indicator in indicators if indicator in message_lower)
        intimacy_scores[level] = score
    
    # Determine primary intimacy level
    max_score = max(intimacy_scores.values()) if intimacy_scores else 0
    if max_score == 0:
        primary_intimacy = 'casual'
        confidence = 0.6
    else:
        primary_intimacy = max(intimacy_scores, key=intimacy_scores.get)
        confidence = min(0.9, (max_score * 0.2) + 0.4)
    
    # Relationship context adjustments
    if relationships:
        current_speaker = relationships.get('current_speaker')
        if current_speaker:
            relationship = relationships.get('relationships', {}).get(current_speaker, 'unknown')
            
            # Adjust intimacy based on relationship
            if relationship in ['close_friend', 'special_affection']:
                if primary_intimacy == 'casual':
                    primary_intimacy = 'personal'
                    confidence += 0.1
            elif relationship in ['captain', 'superior']:
                if primary_intimacy == 'personal':
                    # Authority figures might still share personal content
                    confidence += 0.05
    
    # Check for emotional vulnerability indicators
    vulnerability_patterns = [
        r"i'?m (not|can'?t|don'?t)",
        r"i'?m (struggling|failing|having trouble)",
        r"it'?s (hard|difficult|tough)",
        r"i feel (lost|alone|overwhelmed|helpless)"
    ]
    
    vulnerability_count = sum(1 for pattern in vulnerability_patterns 
                             if re.search(pattern, message_lower))
    
    if vulnerability_count >= 2 and primary_intimacy == 'casual':
        primary_intimacy = 'personal'
        confidence += 0.15
    
    print(f"   💭 ENHANCED INTIMACY ANALYSIS:")
    print(f"      - Level: {primary_intimacy}")
    print(f"      - Confidence: {confidence:.2f}")
    print(f"      - Vulnerability indicators: {vulnerability_count}")
    if relationships:
        print(f"      - Relationship context: {relationships.get('current_speaker', 'unknown')}")
    
    return primary_intimacy, confidence


def resolve_addressing_conflict(group_confidence: float, emotional_confidence: float, 
                              context: Dict) -> Tuple[str, str, float]:
    """
    Resolve conflicts between group addressing and emotional context detection.
    
    This prevents emotional support scenarios from being misclassified as group addressing.
    """
    print(f"   ⚖️  ADDRESSING CONFLICT RESOLUTION:")
    print(f"      - Group addressing confidence: {group_confidence:.2f}")
    print(f"      - Emotional support confidence: {emotional_confidence:.2f}")
    
    # Get context
    message = context.get('message', '').lower()
    vulnerability_level = context.get('vulnerability_level', 'low')
    
    # Special case handling
    if "everyone's expectations" in message or "everyone expects" in message:
        emotional_score = emotional_confidence + 0.3
        print(f"      - 'Everyone's expectations' special case: +0.3 to emotional")
    else:
        emotional_score = emotional_confidence
    
    # Vulnerability bonus
    if vulnerability_level in ['moderate', 'high']:
        emotional_score += 0.15
        print(f"      - Vulnerability bonus: +0.15 to emotional")
    
    # Determine winner
    if emotional_score > group_confidence + 0.1:
        decision = 'emotional_support'
        confidence = emotional_score
        reasoning = f"Emotional context ({emotional_score:.2f}) overrides group addressing"
    else:
        decision = 'group_addressing'
        confidence = group_confidence
        reasoning = f"Group addressing ({group_confidence:.2f}) takes priority"
    
    print(f"      - DECISION: {decision}")
    print(f"      - Final confidence: {confidence:.2f}")
    
    return decision, reasoning, confidence


def get_context_sensitivity_level(message: str, conversation_history: List = None) -> ContextSensitivity:
    """
    Determine the context sensitivity level of a message.
    
    Higher sensitivity means more contextual information is available
    for making accurate classification decisions.
    """
    # Count available context indicators
    message_lower = message.lower()
    
    context_count = 0
    
    # Check for emotional content
    emotional_words = ['feel', 'emotion', 'trouble', 'difficult', 'struggle', 'pressure']
    if any(word in message_lower for word in emotional_words):
        context_count += 2
    
    # Check for addressing patterns
    if any(word in message_lower for word in ['everyone', 'you all', 'hello', 'hi']):
        context_count += 1
    
    # Check for relationship indicators
    if any(word in message_lower for word in ['friend', 'colleague', 'captain', 'personal']):
        context_count += 1
    
    # Check for conversation history
    if conversation_history and len(conversation_history) > 2:
        context_count += 1
    
    # Check for action descriptions
    if '*' in message:
        context_count += 1
    
    # Determine sensitivity level
    if context_count >= 5:
        return ContextSensitivity.HIGH
    elif context_count >= 3:
        return ContextSensitivity.MEDIUM
    elif context_count >= 1:
        return ContextSensitivity.LOW
    else:
        return ContextSensitivity.NONE
