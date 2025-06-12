"""
Strategy Engine - Core Response Strategy Determination
=====================================================

This module contains Elsie's "inner monologue" logic for determining
the best response strategy based on message analysis and context.

The strategy engine analyzes messages and returns a strategy dictionary
containing approach, database needs, reasoning, and additional context.
"""

import re
from typing import Dict, List

# Imports for strategy detection functions
from handlers.ai_wisdom.roleplay_contexts import _check_roleplay_database_needs
from handlers.ai_logic.query_detection import (
    extract_continuation_focus,
    extract_ooc_log_url_request,
    is_character_query,
    is_specific_log_request,
    extract_tell_me_about_subject,
    is_stardancer_query,
    is_stardancer_command_query,
    extract_ship_log_query,
    is_ooc_query
)

# Import from new query_detection module (Phase 6B)
from handlers.ai_logic.query_detection import (
    is_federation_archives_request,
    is_continuation_request
)
# Import from ai_attention handlers (Phase 6A)
from handlers.ai_attention.roleplay_detection import detect_roleplay_triggers
from handlers.ai_attention.exit_conditions import detect_roleplay_exit_conditions
from handlers.ai_attention.character_tracking import (
    extract_character_names_from_emotes,
    extract_addressed_characters
)
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.response_logic import should_elsie_respond_in_roleplay
from handlers.ai_attention.channel_restrictions import is_roleplay_allowed_channel
from handlers.ai_attention.dgm_handler import check_dgm_post as _check_dgm_post
# from handlers.ai_emotion import is_simple_chat  # Removed to prevent circular import   
from handlers.ai_wisdom.context_coordinator  import get_context_for_strategy
from log_processor import is_log_query


def determine_response_strategy(user_message: str, conversation_history: list, channel_context: Dict = None) -> Dict[str, any]:
    """
    Elsie's inner monologue to determine the best response strategy.
    Enhanced with channel restrictions and passive listening for roleplay.
    Returns a strategy dict with approach, needs_database, and reasoning.
    """
    user_lower = user_message.lower().strip()
    
    # Get roleplay state manager
    rp_state = get_roleplay_state()
    turn_number = len(conversation_history) + 1
    
    # Inner monologue process
    strategy = {
        'approach': 'general',
        'needs_database': False,
        'reasoning': '',
        'context_priority': 'minimal'
    }
    
    # PRIORITY 1: Check for roleplay exit conditions if already in RP mode
    if rp_state.is_roleplaying:
        should_exit, exit_reason = detect_roleplay_exit_conditions(user_message)
        
        if should_exit:
            rp_state.end_roleplay_session(exit_reason)
            strategy.update({
                'approach': 'roleplay_exit',
                'needs_database': False,
                'reasoning': f'Exiting roleplay mode due to: {exit_reason}',
                'context_priority': 'none'
            })
            return strategy
        
        # Check for sustained topic shift
        is_roleplay, confidence_score, triggers = detect_roleplay_triggers(user_message, channel_context)
        rp_state.update_confidence(confidence_score)
        
        if not is_roleplay:
            rp_state.increment_exit_condition()
            if rp_state.should_exit_from_sustained_shift():
                rp_state.end_roleplay_session("sustained_topic_shift")
                strategy.update({
                    'approach': 'general',
                    'needs_database': False,
                    'reasoning': 'Sustained topic shift detected - exiting roleplay mode',
                    'context_priority': 'low'
                })
                return strategy
    
    # Continue with main strategy logic
    return _process_main_strategy_logic(user_message, conversation_history, channel_context, strategy, user_lower, rp_state, turn_number)


def _process_main_strategy_logic(user_message: str, conversation_history: list, channel_context: Dict, strategy: Dict, user_lower: str, rp_state, turn_number: int) -> Dict[str, any]:
    """Process the main strategy determination logic including roleplay and standard approaches."""
    
    # PRIORITY 2: Enhanced Roleplay detection and continuation with passive listening
    is_roleplay, confidence_score, triggers = detect_roleplay_triggers(user_message, channel_context)
    
    # Handle DGM posts
    strategy_dgm = _handle_dgm_posts(triggers, user_message, rp_state, turn_number, channel_context)
    if strategy_dgm:
        return strategy_dgm
    
    # Handle ongoing roleplay or new roleplay detection
    strategy_roleplay = _handle_roleplay_logic(is_roleplay, confidence_score, triggers, user_message, rp_state, turn_number, channel_context)
    if strategy_roleplay:
        return strategy_roleplay
    
    # If not roleplay, handle standard message types
    return _handle_standard_message_types(user_message, user_lower, strategy, conversation_history)


def _handle_dgm_posts(triggers: List[str], user_message: str, rp_state, turn_number: int, channel_context: Dict) -> Dict[str, any]:
    """Handle DGM (Deputy Game Master) posts."""
    
    if 'dgm_scene_setting' in triggers:
        print(f"   🎬 DGM SCENE SETTING DETECTED - Starting roleplay session but no response")
        # Start new session if not already roleplaying
        if not rp_state.is_roleplaying:
            dgm_characters = []
            # Extract DGM characters from the DGM result
            dgm_result = _check_dgm_post(user_message)
            if dgm_result.get('characters'):
                dgm_characters = dgm_result['characters']
            
            rp_state.start_roleplay_session(turn_number, triggers, channel_context, dgm_characters)
        
        return {
            'approach': 'dgm_scene_setting',
            'needs_database': False,
            'reasoning': 'DGM scene setting - start roleplay but no response',
            'context_priority': 'none'
        }
    
    if 'dgm_scene_end' in triggers:
        print(f"   🎬 DGM SCENE END DETECTED - Ending roleplay session")
        if rp_state.is_roleplaying:
            rp_state.end_roleplay_session("dgm_scene_end")
        
        return {
            'approach': 'dgm_scene_end',
            'needs_database': False,
            'reasoning': 'DGM scene end - end roleplay session',
            'context_priority': 'none'
        }
    
    if 'dgm_controlled_elsie' in triggers:
        print(f"   🎭 DGM-CONTROLLED ELSIE DETECTED - No response, add to context")
        # Get the DGM result to extract Elsie's content
        dgm_result = _check_dgm_post(user_message)
        elsie_content = dgm_result.get('elsie_content', '')
        
        # Start roleplay session if not already active
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(turn_number, triggers, channel_context)
        
        return {
            'approach': 'dgm_controlled_elsie',
            'needs_database': False,
            'reasoning': f'DGM controlling Elsie - no response, content: "{elsie_content[:50]}{"..." if len(elsie_content) > 50 else ""}"',
            'context_priority': 'dgm_elsie_context',
            'elsie_content': elsie_content
        }
    
    return None  # No DGM post detected


def _handle_roleplay_logic(is_roleplay: bool, confidence_score: float, triggers: List[str], user_message: str, rp_state, turn_number: int, channel_context: Dict) -> Dict[str, any]:
    """Handle roleplay detection and response logic."""
    
    # Special case: If already in roleplay, be more lenient about detecting continued RP
    if rp_state.is_roleplaying and not is_roleplay:
        # Check if this could be continued dialogue even without strong RP indicators
        has_dialogue_elements = any([
            '?' in user_message,  # Questions
            len(user_message.split()) >= 4,  # Substantial messages
            any(word in user_message.lower() for word in ['what', 'how', 'why', 'when', 'where', 'who']),
            any(word in user_message.lower() for word in ['think', 'feel', 'believe', 'suppose'])
        ])
        
        if has_dialogue_elements:
            print(f"   🔄 ONGOING RP: Treating as continued roleplay dialogue")
            is_roleplay = True
            confidence_score = 0.4  # Minimum threshold for continuing RP
            triggers = ["ongoing_session", "dialogue_continuation"]
    
    # SPECIAL CASE: Enhanced monitoring for unknown/thread channels
    channel_allows_rp = is_roleplay_allowed_channel(channel_context)
    is_unknown_channel = False
    if channel_context:
        channel_type = channel_context.get('type', 'unknown')
        is_thread = channel_context.get('is_thread', False)
        is_unknown_channel = (channel_type == 'unknown' or 'thread' in channel_type.lower())
    
    if channel_allows_rp and is_unknown_channel and not is_roleplay:
        # In unknown/thread channels, treat substantial messages as potential roleplay
        word_count = len(user_message.split())
        if word_count >= 3:
            print(f"   🔍 UNKNOWN CHANNEL MONITORING: Treating substantial message as roleplay")
            is_roleplay = True
            confidence_score = 0.3  # Lower threshold for unknown channels
            triggers = ["unknown_channel_monitoring"]
    
    if is_roleplay or rp_state.is_roleplaying:
        return _process_roleplay_response(user_message, rp_state, turn_number, channel_context, confidence_score, triggers)
    
    return None  # Not roleplay


def _process_roleplay_response(user_message: str, rp_state, turn_number: int, channel_context: Dict, confidence_score: float, triggers: List[str]) -> Dict[str, any]:
    """Process roleplay response logic and determine if Elsie should respond."""
    
    # Extract character names for speaker permanence
    character_names = extract_character_names_from_emotes(user_message)
    
    # Extract addressed characters (those being spoken to)
    addressed_characters = extract_addressed_characters(user_message)
    
    # Start new session if not already roleplaying
    if not rp_state.is_roleplaying:
        rp_state.start_roleplay_session(turn_number, triggers, channel_context)
    
    # Add new participants and addressed characters
    for name in character_names:
        rp_state.add_participant(name, "user", turn_number)
    
    for name in addressed_characters:
        rp_state.add_participant(name, "addressed", turn_number)
    
    # Track character turn for simple implicit response logic
    if character_names:
        # Use the first detected character as the speaker
        rp_state.mark_character_turn(turn_number, character_names[0])
    
    # Update confidence tracking
    rp_state.update_confidence(confidence_score)
    
    # Determine response style based on context
    should_respond, response_reason = should_elsie_respond_in_roleplay(user_message, rp_state, turn_number)
    
    # Check if this is a new session (first post in roleplay)
    is_new_session = rp_state.session_start_turn == turn_number
    is_dgm_session = rp_state.is_dgm_session()
    
    # Enhanced name detection for Elsie
    elsie_mentioned = _detect_elsie_mentioned(user_message)
    
    # Respond if:
    # 1. Normal response logic says to respond
    # 2. Elsie is mentioned by name
    # 3. New session AND not a DGM session (regular roleplay should have Elsie greet)
    should_respond_new_session = is_new_session and not is_dgm_session
    
    if should_respond or elsie_mentioned or should_respond_new_session:
        # Active response - preserve subtle_bar_service reason
        if response_reason == "subtle_bar_service":
            reason_priority = response_reason
        else:
            reason_priority = (
                "mentioned_by_name" if elsie_mentioned else
                "new_session" if should_respond_new_session else
                response_reason
            )
        
        rp_state.set_listening_mode(False, reason_priority)
        rp_state.mark_response_turn(turn_number)
        
        # Check if this roleplay message needs database context
        # Subtle bar service doesn't need database context
        needs_database = _check_roleplay_database_needs(user_message) if response_reason != 'subtle_bar_service' else False
        
        return {
            'approach': 'roleplay_active',
            'needs_database': needs_database,  # Enable database for contextual RP queries
            'reasoning': f'Roleplay response - {reason_priority}, participants: {rp_state.get_participant_names()}{", needs database" if needs_database else ""}',
            'context_priority': 'roleplay',
            'roleplay_confidence': confidence_score,
            'roleplay_triggers': triggers,
            'participants': rp_state.get_participant_names(),
            'new_characters': character_names,
            'addressed_characters': addressed_characters,
            'response_reason': reason_priority,
            'elsie_mentioned': elsie_mentioned
        }
    else:
        # Passive listening mode - check if we should interject
        should_interject = rp_state.should_interject_subtle_action(turn_number)
        rp_state.set_listening_mode(True, response_reason)
        
        if should_interject:
            rp_state.mark_interjection(turn_number)
        
        return {
            'approach': 'roleplay_listening',
            'needs_database': False,
            'reasoning': f'Roleplay listening - {response_reason}, tracking: {rp_state.get_participant_names()}',
            'context_priority': 'roleplay_listening',
            'roleplay_confidence': confidence_score,
            'participants': rp_state.get_participant_names(),
            'new_characters': character_names,
            'addressed_characters': addressed_characters,
            'should_interject': should_interject,
            'listening_turn_count': rp_state.listening_turn_count
        }


def _detect_elsie_mentioned(user_message: str) -> bool:
    """Detect if Elsie is mentioned by name in the message."""
    elsie_mentioned = False
    elsie_indicators = ['elsie', 'elise', 'elsy', 'els', 'bartender', 'barkeep']
    mention_patterns = [
        r'@elsie\b', r'\belsie[,:]', r'\belsie\?', r'\belsie!',
        r'\bbartender\b', r'\bbarkeep\b'
    ]
    
    message_lower = user_message.lower()
    
    # Check for direct name mentions
    for indicator in elsie_indicators:
        if indicator in message_lower:
            elsie_mentioned = True
            print(f"   🎯 ELSIE NAME DETECTED: '{indicator}' in message")
            break
    
    # Check for mention patterns
    if not elsie_mentioned:
        for pattern in mention_patterns:
            if re.search(pattern, message_lower):
                elsie_mentioned = True
                print(f"   🎯 ELSIE MENTION PATTERN: '{pattern}' matched")
                break
    
    return elsie_mentioned


def _handle_standard_message_types(user_message: str, user_lower: str, strategy: Dict[str, any], conversation_history: list) -> Dict[str, any]:
    """Handle standard (non-roleplay) message types."""
    
    # Federation Archives requests - specifically asking for external search
    if is_federation_archives_request(user_message):
        strategy.update({
            'approach': 'federation_archives',
            'needs_database': True,
            'reasoning': 'User specifically requested federation archives search',
            'context_priority': 'archives_only'
        })
        return strategy

    # Reset requests - no database needed
    reset_phrases = [
        "let's talk about something else", "lets talk about something else", 
        "change the subject", "something different", "new topic"
    ]
    if any(phrase in user_lower for phrase in reset_phrases):
        strategy.update({
            'approach': 'reset',
            'needs_database': False,
            'reasoning': 'User wants to change topics - use musical personality response',
            'context_priority': 'none'
        })
        return strategy
    
    # Continuation requests - analyze for focused deep dive
    if is_continuation_request(user_message):
        is_focused, focus_subject, context_type = extract_continuation_focus(user_message, conversation_history)
        
        if is_focused and focus_subject:
            strategy.update({
                'approach': 'focused_continuation',
                'needs_database': True,
                'reasoning': f'User wants deeper information about "{focus_subject}" from {context_type} context',
                'context_priority': 'high',
                'focus_subject': focus_subject,
                'context_type': context_type
            })
            return strategy
        else:
            strategy.update({
                'approach': 'simple_continuation',
                'needs_database': False,
                'reasoning': 'User wants to continue previous topic - provide general encouragement',
                'context_priority': 'reuse_previous'
            })
            return strategy
    
    # Continue with remaining standard message type checks
    return _handle_remaining_standard_types(user_message, user_lower, strategy)


def _handle_remaining_standard_types(user_message: str, user_lower: str, strategy: Dict[str, any]) -> Dict[str, any]:
    """Handle the remaining standard message types."""
    
    # Simple chat - no database needed (using local import to avoid circular dependency)
    try:
        from handlers.ai_emotion.personality_contexts import is_simple_chat
        if is_simple_chat(user_message):
            strategy.update({
                'approach': 'simple_chat',
                'needs_database': False,
                'reasoning': 'Simple conversational response - use bartender personality',
                'context_priority': 'minimal'
            })
            return strategy
    except ImportError:
        # Fallback simple chat detection if import fails
        simple_chat_patterns = ['hi', 'hello', 'hey', 'how are you', 'thanks', 'thank you', 'bye', 'goodbye']
        if any(pattern in user_message.lower().strip() for pattern in simple_chat_patterns):
            strategy.update({
                'approach': 'simple_chat',
                'needs_database': False,
                'reasoning': 'Simple conversational response (fallback detection) - use bartender personality',
                'context_priority': 'minimal'
            })
            return strategy
    
    # Stardancer queries - check early to catch command queries before general context
    if is_stardancer_query(user_message):
        strategy.update({
            'approach': 'stardancer_info',
            'needs_database': True,
            'reasoning': 'Stardancer information request - need strict database adherence with guard rails',
            'context_priority': 'high',
            'stardancer_specific': True,
            'command_query': is_stardancer_command_query(user_message)
        })
        return strategy
    
    # OOC URL requests - database needed
    if extract_ooc_log_url_request(user_message)[0]:
        strategy.update({
            'approach': 'ooc_url',
            'needs_database': True,
            'reasoning': 'OOC URL request - need to search database for specific page',
            'context_priority': 'none'
        })
        return strategy
    
    # Character queries - database needed
    if is_character_query(user_message)[0]:
        strategy.update({
            'approach': 'character',
            'needs_database': True,
            'reasoning': 'Character information request - need personnel/character database search',
            'context_priority': 'high'
        })
        return strategy
    
    # Log queries - database needed (specific mission log requests)
    if is_specific_log_request(user_message) or is_log_query(user_message):
        strategy.update({
            'approach': 'logs',
            'needs_database': True,
            'reasoning': 'Specific mission log request - search only mission_log type pages',
            'context_priority': 'high',
            'log_specific': True
        })
        return strategy
    
    # General mission/event queries (broader search)
    if any(keyword in user_lower for keyword in ['mission', 'recent', 'last mission', 'what happened']):
        strategy.update({
            'approach': 'logs',
            'needs_database': True,
            'reasoning': 'General mission/event information request - comprehensive search',
            'context_priority': 'high',
            'log_specific': False
        })
        return strategy
    
    # Tell me about queries - database needed
    if extract_tell_me_about_subject(user_message):
        # Check if this is specifically about Stardancer
        if is_stardancer_query(user_message):
            strategy.update({
                'approach': 'stardancer_info',
                'needs_database': True,
                'reasoning': 'Stardancer information request - need strict database adherence with guard rails',
                'context_priority': 'high',
                'stardancer_specific': True,
                'command_query': is_stardancer_command_query(user_message)
            })
            return strategy
        else:
            strategy.update({
                'approach': 'tell_me_about',
                'needs_database': True,
                'reasoning': 'Information request about specific subject - need prioritized database search',
                'context_priority': 'high'
            })
            return strategy
    
    # Ship queries - database needed
    if extract_ship_log_query(user_message)[0]:
        # Check if this is specifically about Stardancer
        if is_stardancer_query(user_message):
            strategy.update({
                'approach': 'stardancer_info',
                'needs_database': True,
                'reasoning': 'Stardancer ship information request - need strict database adherence with guard rails',
                'context_priority': 'high',
                'stardancer_specific': True,
                'command_query': is_stardancer_command_query(user_message)
            })
            return strategy
        else:
            strategy.update({
                'approach': 'ship_logs',
                'needs_database': True,
                'reasoning': 'Ship-specific information request - need comprehensive ship database search',
                'context_priority': 'high'
            })
            return strategy
    
    # OOC queries - may need database
    if is_ooc_query(user_message)[0]:
        strategy.update({
            'approach': 'ooc',
            'needs_database': True,
            'reasoning': 'OOC query - may need handbook or schedule information',
            'context_priority': 'medium'
        })
        return strategy
    
    # General conversation that might benefit from context
    if len(user_message.split()) > 3:  # More substantial messages
        strategy.update({
            'approach': 'general_with_context',
            'needs_database': True,
            'reasoning': 'Substantial conversation - provide light database context for richer responses',
            'context_priority': 'low'
        })
        return strategy
    
    # Default to simple chat for short unclear messages
    strategy.update({
        'approach': 'simple_chat',
        'needs_database': False,
        'reasoning': 'Short/unclear message - treat as casual conversation',
        'context_priority': 'minimal'
    })
    return strategy 