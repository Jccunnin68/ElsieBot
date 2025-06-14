"""
Emotional Analysis - Enhanced Emotional Intelligence
===================================================

This module provides sophisticated emotional analysis capabilities for Elsie,
including enhanced emotional tone detection, emotional support opportunity
identification, and confidence-based emotional context analysis.

This addresses the issue where emotional support scenarios were being
misclassified as group addressing by providing more nuanced emotional detection.
"""

import re
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class EmotionalTone(Enum):
    """Enhanced emotional tone classifications"""
    HAPPY = "happy"
    SAD = "sad"
    FRUSTRATED = "frustrated"
    ANXIOUS = "anxious"
    TIRED = "tired"
    GRATEFUL = "grateful"
    EXCITED = "excited"
    CONCERNED = "concerned"
    OVERWHELMED = "overwhelmed"
    CONFIDENT = "confident"
    VULNERABLE = "vulnerable"
    NEUTRAL = "neutral"


class EmotionalIntensity(Enum):
    """Emotional intensity levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class EmotionalContext:
    """Comprehensive emotional context analysis"""
    primary_tone: EmotionalTone
    secondary_tones: List[EmotionalTone]
    intensity: EmotionalIntensity
    confidence: float
    support_indicators: List[str]
    vulnerability_level: str
    emotional_keywords: List[str]
    contextual_clues: List[str]


def analyze_emotional_tone_enhanced(message: str) -> Tuple[str, float, EmotionalContext]:
    """
    Enhanced emotional tone analysis with confidence scoring and context.
    
    This replaces the basic emotional tone detection with sophisticated analysis
    that can distinguish between different emotional contexts and intensities.
    
    Returns:
        (tone_string, confidence, emotional_context)
    """
    message_lower = message.lower()
    
    # Enhanced emotional pattern detection
    emotional_patterns = {
        EmotionalTone.SAD: {
            'keywords': ['sad', 'upset', 'down', 'depressed', 'melancholy', 'heartbroken', 'gloomy', 'miserable'],
            'phrases': [
                'feeling down', 'so sad', 'really upset', 'getting me down',
                'makes me sad', 'feeling blue', 'down in the dumps'
            ],
            'contextual': ['trouble', 'difficulty', 'struggling', 'hard time', 'can\'t handle']
        },
        EmotionalTone.FRUSTRATED: {
            'keywords': ['frustrated', 'angry', 'mad', 'annoyed', 'irritated', 'furious', 'aggravated'],
            'phrases': [
                'so frustrated', 'really annoying', 'driving me crazy', 'fed up',
                'can\'t stand', 'really mad', 'getting on my nerves'
            ],
            'contextual': ['why does', 'always goes wrong', 'never works', 'impossible']
        },
        EmotionalTone.ANXIOUS: {
            'keywords': ['anxious', 'nervous', 'worried', 'scared', 'afraid', 'panicked', 'stressed'],
            'phrases': [
                'so worried', 'really nervous', 'scared about', 'afraid that',
                'anxiety', 'panic', 'stress', 'overwhelming'
            ],
            'contextual': ['what if', 'worried about', 'nervous about', 'afraid of']
        },
        EmotionalTone.OVERWHELMED: {
            'keywords': ['overwhelmed', 'too much', 'can\'t cope', 'drowning', 'suffocating'],
            'phrases': [
                'so much pressure', 'can\'t handle', 'too overwhelming', 'drowning in',
                'can\'t keep up', 'falling behind', 'too many'
            ],
            'contextual': ['expectations', 'pressure', 'responsibilities', 'demands']
        },
        EmotionalTone.VULNERABLE: {
            'keywords': ['vulnerable', 'exposed', 'helpless', 'alone', 'isolated'],
            'phrases': [
                'feel so alone', 'nobody understands', 'all by myself',
                'feel helpless', 'don\'t know what to do'
            ],
            'contextual': ['struggling with', 'having trouble', 'difficult for me']
        },
        EmotionalTone.GRATEFUL: {
            'keywords': ['grateful', 'thankful', 'appreciate', 'blessed', 'lucky'],
            'phrases': [
                'so grateful', 'really appreciate', 'thank you', 'means a lot',
                'can\'t thank you enough', 'so thankful'
            ],
            'contextual': ['helped me', 'made my day', 'so kind']
        },
        EmotionalTone.HAPPY: {
            'keywords': ['happy', 'excited', 'thrilled', 'delighted', 'joyful', 'elated'],
            'phrases': [
                'so happy', 'really excited', 'can\'t wait', 'thrilled about',
                'makes me smile', 'feeling great'
            ],
            'contextual': ['wonderful', 'amazing', 'fantastic', 'perfect']
        }
    }
    
    # Analyze message for emotional patterns
    detected_emotions = []
    emotional_keywords = []
    contextual_clues = []
    
    for tone, patterns in emotional_patterns.items():
        score = 0
        found_keywords = []
        found_clues = []
        
        # Check direct keywords
        for keyword in patterns['keywords']:
            if keyword in message_lower:
                score += 2
                found_keywords.append(keyword)
        
        # Check emotional phrases
        for phrase in patterns['phrases']:
            if phrase in message_lower:
                score += 3
                found_keywords.append(phrase)
        
        # Check contextual indicators
        for context in patterns['contextual']:
            if context in message_lower:
                score += 1
                found_clues.append(context)
        
        if score > 0:
            detected_emotions.append((tone, score, found_keywords, found_clues))
            emotional_keywords.extend(found_keywords)
            contextual_clues.extend(found_clues)
    
    # Determine primary emotion and confidence
    if detected_emotions:
        # Sort by score to get primary emotion
        detected_emotions.sort(key=lambda x: x[1], reverse=True)
        primary_tone, primary_score, primary_keywords, primary_clues = detected_emotions[0]
        
        # Calculate confidence based on score and context
        confidence = min(0.95, (primary_score * 0.2) + 0.3)
        
        # Get secondary emotions
        secondary_tones = [emotion[0] for emotion in detected_emotions[1:3]]
        
    else:
        primary_tone = EmotionalTone.NEUTRAL
        confidence = 0.8
        secondary_tones = []
    
    # Determine emotional intensity
    intensity = _calculate_emotional_intensity(message_lower, primary_tone)
    
    # Detect support indicators
    support_indicators = _detect_support_indicators(message_lower)
    
    # Analyze vulnerability level
    vulnerability_level = _analyze_vulnerability_level(message_lower, primary_tone)
    
    # Create emotional context
    emotional_context = EmotionalContext(
        primary_tone=primary_tone,
        secondary_tones=secondary_tones,
        intensity=intensity,
        confidence=confidence,
        support_indicators=support_indicators,
        vulnerability_level=vulnerability_level,
        emotional_keywords=emotional_keywords,
        contextual_clues=contextual_clues
    )
    
    print(f"   🎭 ENHANCED EMOTIONAL ANALYSIS:")
    print(f"      - Primary Tone: {primary_tone.value} (confidence: {confidence:.2f})")
    print(f"      - Intensity: {intensity.value}")
    print(f"      - Support Indicators: {support_indicators}")
    print(f"      - Vulnerability: {vulnerability_level}")
    print(f"      - Keywords: {emotional_keywords[:3]}")  # Show first 3
    
    return primary_tone.value, confidence, emotional_context


def detect_emotional_support_opportunity(message: str, context: Dict) -> Tuple[bool, float]:
    """
    Detect when someone needs emotional support with high confidence.
    
    This is the key function that fixes the group addressing vs emotional support
    classification issue by providing sophisticated emotional support detection.
    
    Args:
        message: The user message to analyze
        context: Additional context including relationships, conversation state
        
    Returns:
        (needs_support, confidence): Boolean and confidence score (0.0-1.0)
    """
    message_lower = message.lower()
    
    # High-confidence emotional support indicators
    strong_support_patterns = [
        # Direct emotional distress expressions
        r"i'?m having trouble",
        r"i'?m struggling with",
        r"i can'?t handle",
        r"i don'?t know what to do",
        r"i feel (so|really|very)? (overwhelmed|lost|alone|helpless)",
        r"it'?s (so|really|very)? (hard|difficult|tough|challenging)",
        r"i'?m (really|so|very)? (worried|scared|afraid|anxious)",
        
        # Pressure and expectations
        r"(living up to|meeting|fulfilling).*(expectations|standards|demands)",
        r"(so much|too much|overwhelming).*(pressure|stress|weight)",
        r"everyone expects",
        r"pressure to (be|do|perform)",
        
        # Vulnerability expressions
        r"i'?m not (good|strong|capable) enough",
        r"i'?m failing",
        r"i can'?t (seem to|manage to)",
        r"nothing i do",
        r"always (mess|screw) up",
        
        # Seeking understanding/help
        r"(nobody|no one) understands",
        r"i need (help|support|someone)",
        r"i don'?t know who to talk to",
        r"feeling (so|really|very)? alone"
    ]
    
    # Medium-confidence indicators (need additional context)
    moderate_support_patterns = [
        r"it'?s been (hard|difficult|tough|rough)",
        r"i'?m (tired|exhausted|worn out)",
        r"(things|everything) (seem|feel|look) (hopeless|impossible|overwhelming)",
        r"i wish i could",
        r"if only i",
        r"i used to be"
    ]
    
    # Context enhancers (increase confidence when combined with emotional indicators)
    context_enhancers = [
        # Personal/intimate setting indicators
        'personal', 'private', 'between us', 'confidential',
        
        # Physical distress indicators
        'sits heavily', 'slumps', 'sighs deeply', 'looks down',
        'shoulders droop', 'head in hands',
        
        # Isolation indicators
        'alone at', 'by myself', 'sits apart', 'quietly'
    ]
    
    support_score = 0.0
    matched_patterns = []
    
    # Check strong support patterns
    for pattern in strong_support_patterns:
        if re.search(pattern, message_lower):
            support_score += 0.3
            matched_patterns.append(pattern)
    
    # Check moderate support patterns
    for pattern in moderate_support_patterns:
        if re.search(pattern, message_lower):
            support_score += 0.15
            matched_patterns.append(pattern)
    
    # Check context enhancers
    context_bonus = 0.0
    for enhancer in context_enhancers:
        if enhancer in message_lower:
            context_bonus += 0.1
    
    # Apply context bonus (max 0.2)
    support_score += min(0.2, context_bonus)
    
    # Check for emotional actions (asterisk actions that show distress)
    emotional_actions = re.findall(r'\*([^*]+)\*', message)
    for action in emotional_actions:
        action_lower = action.lower()
        if any(word in action_lower for word in ['heavily', 'sadly', 'wearily', 'tiredly', 'slumps', 'sighs']):
            support_score += 0.1
    
    # Relationship context bonus (closer relationships = more likely to share emotional content)
    if context and 'relationship' in context:
        relationship = context['relationship']
        if relationship in ['close_friend', 'special_affection']:
            support_score += 0.1
        elif relationship in ['friend', 'colleague']:
            support_score += 0.05
    
    # Intimacy context bonus
    if context and 'intimacy_level' in context:
        intimacy = context['intimacy_level']
        if intimacy in ['personal', 'intimate']:
            support_score += 0.1
        elif intimacy == 'casual':
            support_score += 0.05
    
    # Cap confidence at 0.95
    confidence = min(0.95, support_score)
    needs_support = confidence >= 0.4  # Threshold for emotional support detection
    
    if needs_support:
        print(f"   💝 EMOTIONAL SUPPORT DETECTED:")
        print(f"      - Confidence: {confidence:.2f}")
        print(f"      - Matched patterns: {len(matched_patterns)}")
        print(f"      - Top patterns: {matched_patterns[:2]}")
        if context:
            print(f"      - Relationship context: {context.get('relationship', 'unknown')}")
            print(f"      - Intimacy level: {context.get('intimacy_level', 'unknown')}")
    
    return needs_support, confidence


def analyze_emotional_context(message: str) -> Dict:
    """
    Comprehensive emotional context analysis for decision making.
    
    Returns a dictionary with emotional analysis results that can be used
    by other systems for decision making.
    """
    tone, confidence, context = analyze_emotional_tone_enhanced(message)
    needs_support, support_confidence = detect_emotional_support_opportunity(message, {})
    
    return {
        'emotional_tone': tone,
        'emotional_confidence': confidence,
        'needs_support': needs_support,
        'support_confidence': support_confidence,
        'intensity': context.intensity.value,
        'vulnerability_level': context.vulnerability_level,
        'support_indicators': context.support_indicators,
        'emotional_keywords': context.emotional_keywords,
        'contextual_clues': context.contextual_clues,
        'primary_tone_enum': context.primary_tone,
        'secondary_tones': [tone.value for tone in context.secondary_tones]
    }


def _calculate_emotional_intensity(message: str, primary_tone: EmotionalTone) -> EmotionalIntensity:
    """Calculate the intensity of the emotional expression"""
    
    # Intensity multipliers
    high_intensity_words = ['really', 'very', 'extremely', 'incredibly', 'absolutely', 'completely', 'totally']
    extreme_intensity_words = ['overwhelmingly', 'devastatingly', 'unbearably', 'impossibly']
    
    # Punctuation intensity indicators
    exclamation_count = message.count('!')
    question_count = message.count('?')
    caps_ratio = sum(1 for c in message if c.isupper()) / len(message) if message else 0
    
    intensity_score = 1.0  # Base intensity
    
    # Word-based intensity
    for word in high_intensity_words:
        if word in message.lower():
            intensity_score += 0.3
    
    for word in extreme_intensity_words:
        if word in message.lower():
            intensity_score += 0.5
    
    # Punctuation-based intensity
    intensity_score += exclamation_count * 0.2
    intensity_score += caps_ratio * 0.5
    
    # Repetition-based intensity (repeated letters or words)
    if re.search(r'([a-z])\1{2,}', message.lower()):  # "sooo", "noooo"
        intensity_score += 0.3
    
    # Tone-specific intensity adjustments
    if primary_tone in [EmotionalTone.FRUSTRATED, EmotionalTone.ANXIOUS, EmotionalTone.OVERWHELMED]:
        intensity_score += 0.2  # These emotions tend to be more intense
    
    # Classify intensity
    if intensity_score >= 2.5:
        return EmotionalIntensity.EXTREME
    elif intensity_score >= 1.8:
        return EmotionalIntensity.HIGH
    elif intensity_score >= 1.2:
        return EmotionalIntensity.MODERATE
    else:
        return EmotionalIntensity.LOW


def _detect_support_indicators(message: str) -> List[str]:
    """Detect specific indicators that someone needs support"""
    indicators = []
    message_lower = message.lower()
    
    support_patterns = {
        'seeking_help': ['need help', 'need advice', 'don\'t know what to do', 'could use some help'],
        'expressing_struggle': ['struggling with', 'having trouble', 'can\'t handle', 'difficult for me'],
        'feeling_isolated': ['feel alone', 'nobody understands', 'all by myself', 'no one to talk to'],
        'showing_vulnerability': ['not sure if', 'afraid that', 'worried about', 'scared of'],
        'expressing_inadequacy': ['not good enough', 'failing at', 'can\'t seem to', 'always mess up']
    }
    
    for category, patterns in support_patterns.items():
        for pattern in patterns:
            if pattern in message_lower:
                indicators.append(category)
                break  # Only add category once
    
    return indicators


def _analyze_vulnerability_level(message: str, primary_tone: EmotionalTone) -> str:
    """Analyze the level of vulnerability expressed in the message"""
    message_lower = message.lower()
    
    high_vulnerability_indicators = [
        'i\'m not', 'i can\'t', 'i don\'t know', 'i\'m afraid',
        'i\'m scared', 'i feel lost', 'i\'m struggling', 'i\'m failing'
    ]
    
    moderate_vulnerability_indicators = [
        'it\'s hard', 'it\'s difficult', 'i\'m worried', 'i\'m concerned',
        'i\'m not sure', 'i wonder if', 'maybe i', 'perhaps i'
    ]
    
    vulnerability_score = 0
    
    for indicator in high_vulnerability_indicators:
        if indicator in message_lower:
            vulnerability_score += 2
    
    for indicator in moderate_vulnerability_indicators:
        if indicator in message_lower:
            vulnerability_score += 1
    
    # Tone-based vulnerability adjustment
    if primary_tone in [EmotionalTone.VULNERABLE, EmotionalTone.OVERWHELMED, EmotionalTone.ANXIOUS]:
        vulnerability_score += 1
    
    if vulnerability_score >= 4:
        return "high"
    elif vulnerability_score >= 2:
        return "moderate"
    else:
        return "low"


def get_emotional_response_style(emotional_context: EmotionalContext) -> Dict[str, str]:
    """
    Get recommended response style based on emotional context.
    
    This helps other systems determine how to respond appropriately
    to different emotional states.
    """
    tone = emotional_context.primary_tone
    intensity = emotional_context.intensity
    vulnerability = emotional_context.vulnerability_level
    
    # Response style recommendations
    style_map = {
        EmotionalTone.SAD: {
            "approach": "empathetic",
            "tone": "gentle",
            "style": "supportive"
        },
        EmotionalTone.FRUSTRATED: {
            "approach": "validating",
            "tone": "understanding",
            "style": "calming"
        },
        EmotionalTone.ANXIOUS: {
            "approach": "reassuring",
            "tone": "calm",
            "style": "stabilizing"
        },
        EmotionalTone.OVERWHELMED: {
            "approach": "grounding",
            "tone": "peaceful",
            "style": "simplifying"
        },
        EmotionalTone.VULNERABLE: {
            "approach": "protective",
            "tone": "warm",
            "style": "accepting"
        },
        EmotionalTone.GRATEFUL: {
            "approach": "acknowledging",
            "tone": "warm",
            "style": "reciprocal"
        },
        EmotionalTone.HAPPY: {
            "approach": "celebratory",
            "tone": "upbeat",
            "style": "encouraging"
        }
    }
    
    base_style = style_map.get(tone, {
        "approach": "responsive",
        "tone": "natural",
        "style": "balanced"
    })
    
    # Adjust for intensity
    if intensity == EmotionalIntensity.HIGH:
        base_style["intensity_note"] = "respond with higher energy"
    elif intensity == EmotionalIntensity.LOW:
        base_style["intensity_note"] = "respond gently, don't overwhelm"
    
    # Adjust for vulnerability
    if vulnerability == "high":
        base_style["vulnerability_note"] = "be extra gentle and supportive"
    
    return base_style 