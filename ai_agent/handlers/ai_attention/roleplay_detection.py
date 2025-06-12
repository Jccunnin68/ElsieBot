"""
Roleplay Detection - Core Roleplay Pattern Recognition
====================================================

This module contains functions for detecting roleplay patterns in user messages.
It provides a clean interface for identifying user intent patterns related to roleplay.
"""

import re
from typing import List, Tuple, Dict, Optional

from .roleplay_types import (
    ROLEPLAY_INDICATORS,
    RoleplayDetection,
    RoleplayConfidence,
    RoleplayTrigger,
    MIN_ROLEPLAY_CONFIDENCE,
    MIN_CONTINUATION_CONFIDENCE,
    MIN_THREAD_CONFIDENCE,
    TRIGGER_TYPES
)

def detect_roleplay_triggers(user_message: str, channel_context: Optional[Dict] = None) -> RoleplayDetection:
    """
    Detect roleplay triggers in a user message.
    Returns a tuple of (is_roleplay, confidence_score, triggers).
    """
    triggers = []
    confidence_score = 0.0
    
    # Check for roleplay indicators
    for indicator_type, pattern in ROLEPLAY_INDICATORS.items():
        if re.search(pattern, user_message):
            triggers.append(TRIGGER_TYPES[indicator_type])
            confidence_score += 0.2  # Base confidence for each indicator
    
    # Check for character names in thread context
    if channel_context and channel_context.get('is_thread', False):
        confidence_score += 0.1  # Additional confidence for thread context
    
    # Determine if this is roleplay based on confidence threshold
    is_roleplay = confidence_score >= MIN_ROLEPLAY_CONFIDENCE
    
    return is_roleplay, confidence_score, triggers

def is_roleplay_message(user_message: str) -> bool:
    """
    Simple check if a message contains roleplay indicators.
    Returns True if any roleplay indicators are found.
    """
    for pattern in ROLEPLAY_INDICATORS.values():
        if re.search(pattern, user_message):
            return True
    return False

def get_roleplay_confidence(user_message: str, channel_context: Optional[Dict] = None) -> RoleplayConfidence:
    """
    Calculate roleplay confidence score for a message.
    Returns a float between 0.0 and 1.0.
    """
    confidence = 0.0
    
    # Check for roleplay indicators
    for pattern in ROLEPLAY_INDICATORS.values():
        if re.search(pattern, user_message):
            confidence += 0.2
    
    # Add context-based confidence
    if channel_context:
        if channel_context.get('is_thread', False):
            confidence += 0.1
        if channel_context.get('type', '').lower() in ['roleplay', 'rp']:
            confidence += 0.1
    
    return min(confidence, 1.0)  # Cap at 1.0

def extract_roleplay_triggers(user_message: str) -> List[RoleplayTrigger]:
    """
    Extract all roleplay triggers from a message.
    Returns a list of trigger types found.
    """
    triggers = []
    for indicator_type, pattern in ROLEPLAY_INDICATORS.items():
        if re.search(pattern, user_message):
            triggers.append(TRIGGER_TYPES[indicator_type])
    return triggers 