"""
Roleplay Detection Engine
=========================

Core detection logic for determining if a message contains roleplay content.
Uses confidence scoring and pattern matching to identify roleplay triggers.
"""

import re
from typing import Tuple, Dict, List

from .dgm_handler import check_dgm_post
from .channel_restrictions import is_roleplay_allowed_channel
from .character_tracking import is_valid_character_name


def detect_roleplay_triggers(user_message: str, channel_context: Dict = None) -> Tuple[bool, float, List[str]]:
    """
    Roleplay Detection Engine: Detect if user is initiating or continuing roleplay.
    Enhanced with passive listening and channel restrictions.
    Now includes DGM (Deputy Game Master) scene setting support.
    Returns (is_roleplay, confidence_score, detected_triggers)
    """
    print(f"\n🔍 ROLEPLAY DETECTION ENGINE:")
    print(f"   📝 Message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
    
    # Check for DGM (Deputy Game Master) posts first
    dgm_result = check_dgm_post(user_message)
    if dgm_result['is_dgm']:
        print(f"   🎬 DGM POST DETECTED: {dgm_result['action']}")
        return dgm_result['triggers_roleplay'], dgm_result['confidence'], dgm_result['triggers']
    
    # Check if we're in an appropriate channel for roleplay
    if not is_roleplay_allowed_channel(channel_context):
        print(f"   🚫 DETECTION BLOCKED: Roleplay not allowed in this channel")
        return False, 0.0, ["channel_restricted"]
    
    confidence_score = 0.0
    detected_triggers = []
    
    # Check if we're in a thread - threads get bonus confidence
    is_thread = False
    channel_type = "unknown"
    if channel_context:
        is_thread = channel_context.get('is_thread', False)
        channel_type = channel_context.get('type', 'unknown')
        discord_thread_types = ['public_thread', 'private_thread', 'news_thread']
        if is_thread or channel_type in discord_thread_types:
            is_thread = True
    
    print(f"   🎯 SCANNING FOR ROLEPLAY PATTERNS:")
    if is_thread:
        print(f"      🧵 THREAD CONTEXT DETECTED - Enhanced roleplay detection")
    
    # 1. Character Name Brackets - Very Strong Indicator
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    if bracket_matches:
        confidence_score += 0.7  # Very high confidence for character brackets
        detected_triggers.append("character_brackets")
        character_names = [name.strip() for name in bracket_matches if is_valid_character_name(name.strip())]
        print(f"      ✅ CHARACTER BRACKETS DETECTED: {character_names} (+0.7 confidence)")
    else:
        print(f"      ❌ No character brackets found")
    
    # 2. Emote-Based Detection (Primary Trigger) - Strong indicator
    emote_pattern = r'\*([^*]+)\*'
    emotes = re.findall(emote_pattern, user_message)
    if emotes:
        confidence_score += 0.6  # High confidence for emotes
        detected_triggers.append("emotes")
        print(f"      ✅ EMOTES DETECTED: {emotes} (+0.6 confidence)")
    else:
        print(f"      ❌ No emotes found")
    
    # 3. Quoted Dialogue - Moderate indicator
    quote_patterns = [
        r'"([^"]+)"',  # Standard quotes
        r'"([^"]+)"',  # Smart quotes
        r"'([^']+)'",  # Single smart quotes
    ]
    
    has_quotes = False
    for pattern in quote_patterns:
        if re.search(pattern, user_message):
            has_quotes = True
            break
    
    if has_quotes:
        quote_bonus = 0.4 if bracket_matches else 0.3
        confidence_score += quote_bonus
        detected_triggers.append("quoted_dialogue")
        print(f"      ✅ QUOTED DIALOGUE: Found quotes (+{quote_bonus} confidence)")
    else:
        print(f"      ❌ No quoted dialogue found")
    
    # 4. Second-Person Imperative Actions
    imperative_patterns = [
        r'^(look|tell|show|get|bring|give|take|come|go|sit|stand|walk|turn)',
        r'^(help|find|search|check|grab|pick)',
        r'\b(you should|you need to|you can|could you)\b'
    ]
    
    message_lower = user_message.lower().strip()
    imperative_found = False
    for pattern in imperative_patterns:
        if re.search(pattern, message_lower):
            confidence_score += 0.25
            detected_triggers.append("imperative_action")
            print(f"      ✅ IMPERATIVE ACTION: Pattern matched (+0.25 confidence)")
            imperative_found = True
            break
    
    if not imperative_found:
        print(f"      ❌ No imperative actions found")
    
    # 5. Narrative/Descriptive Language
    narrative_indicators = [
        r'\b(she|he|they)\s+(walked|moved|smiled|looked|turned|said|whispered|replied)',
        r'\b(the room|the air|the atmosphere|the place|around them|nearby)',
        r'\b(suddenly|quietly|slowly|carefully|nervously|confidently)\b',
        r'\b(seemed|appeared|felt|looked like|sounded)\b'
    ]
    
    narrative_found = False
    for pattern in narrative_indicators:
        if re.search(pattern, user_message, re.IGNORECASE):
            confidence_score += 0.15
            detected_triggers.append("narrative_tone")
            print(f"      ✅ NARRATIVE TONE: Pattern matched (+0.15 confidence)")
            narrative_found = True
            break
    
    if not narrative_found:
        print(f"      ❌ No narrative tone found")
    
    # 6. Character Actions Without Emotes
    action_indicators = [
        r'\b(nods|shrugs|sighs|laughs|chuckles|grins|frowns|winces)',
        r'\b(approaches|enters|exits|sits down|stands up|leans)',
        r'\b(gestures|points|waves|reaches for|holds)'
    ]
    
    action_found = False
    for pattern in action_indicators:
        if re.search(pattern, user_message, re.IGNORECASE):
            confidence_score += 0.2
            detected_triggers.append("character_actions")
            print(f"      ✅ CHARACTER ACTIONS: Pattern matched (+0.2 confidence)")
            action_found = True
            break
    
    if not action_found:
        print(f"      ❌ No character actions found")
    
    # 7. Thread Context Bonus
    thread_bonus = 0.0
    if is_thread:
        thread_rp_patterns = [
            r'\b(says|replies|responds|asks|tells|whispers|shouts)\b',
            r'\b(looks at|turns to|faces|addresses)\b',
            r'\b(thinking|wondering|feeling|realizing)\b',
            r'\b(meanwhile|suddenly|then|after|before)\b',
        ]
        
        for pattern in thread_rp_patterns:
            if re.search(pattern, user_message, re.IGNORECASE):
                thread_bonus += 0.25
                detected_triggers.append("thread_rp_pattern")
                print(f"      ✅ THREAD RP PATTERN: Matched (+0.25 thread bonus)")
                break
        
        word_count = len(user_message.split())
        if word_count >= 4:
            thread_bonus += 0.1
            detected_triggers.append("thread_context")
            print(f"      ✅ THREAD CONTEXT: Substantial message (+0.1 thread bonus)")
    
    confidence_score += thread_bonus
    
    # Determine if this qualifies as roleplay
    threshold = 0.2 if is_thread else 0.25
    is_roleplay = confidence_score >= threshold
    
    print(f"   📊 DETECTION RESULTS:")
    print(f"      - Total Confidence: {confidence_score:.2f}")
    print(f"      - Threshold: {threshold}")
    print(f"      - Thread Bonus: +{thread_bonus:.2f}")
    print(f"      - Triggers Found: {detected_triggers}")
    print(f"      - Is Roleplay: {is_roleplay}")
    print(f"   🎯 MONITORING STATUS: {'ROLEPLAY ACTIVE' if is_roleplay else 'STANDARD MODE'}")
    
    return is_roleplay, confidence_score, detected_triggers 