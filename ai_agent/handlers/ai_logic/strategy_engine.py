"""
Strategy Engine - Core Response Strategy Determination
=====================================================

This module contains Elsie's "inner monologue" logic for determining
the best response strategy based on message analysis and context.

The strategy engine analyzes messages and returns a strategy dictionary
containing approach, database needs, reasoning, and additional context.
"""

import re
from typing import Dict, List, Optional
import traceback

# Imports for strategy detection functions
from handlers.ai_logic.query_detection import (
    extract_continuation_focus,
    extract_ooc_log_url_request,
    is_character_query,
    is_specific_log_request,
    extract_tell_me_about_subject,
    is_stardancer_query,
    is_stardancer_command_query,
    extract_ship_log_query,
    is_ooc_query,
    is_log_query,
    is_federation_archives_request,
    is_ship_plus_log_query,
    is_character_plus_log_query
)

# Import from new query_detection module (Phase 6B)
from handlers.ai_logic.query_detection import (
    is_continuation_request
)

# Import from ai_attention handlers (Phase 6A)
from handlers.ai_attention.roleplay_detection import detect_roleplay_triggers
from handlers.ai_attention.exit_conditions import detect_roleplay_exit_conditions
from handlers.ai_attention.roleplay_strategy import process_roleplay_strategy
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.dgm_handler import check_dgm_post as _check_dgm_post

# Import shared roleplay types
from handlers.ai_attention.roleplay_types import (
    APPROACH_TYPES,
    CONTEXT_PRIORITIES,
    EXIT_CONDITIONS,
    TRIGGER_TYPES
)

def determine_response_strategy(user_message: str, conversation_history: list, channel_context: Optional[Dict] = None) -> Dict[str, any]:
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
        'approach': APPROACH_TYPES['general'],
        'needs_database': False,
        'reasoning': '',
        'context_priority': CONTEXT_PRIORITIES['none']
    }
    
    # PRIORITY 1: Check for roleplay exit conditions if already in RP mode
    if rp_state.is_roleplaying:
        should_exit, exit_reason = detect_roleplay_exit_conditions(user_message)
        
        if should_exit:
            rp_state.end_roleplay_session(exit_reason)
            strategy.update({
                'approach': APPROACH_TYPES['roleplay_exit'],
                'needs_database': False,
                'reasoning': f'Exiting roleplay mode due to: {exit_reason}',
                'context_priority': CONTEXT_PRIORITIES['none']
            })
            return strategy
        
        # Check for sustained topic shift
        is_roleplay, confidence_score, triggers = detect_roleplay_triggers(user_message, channel_context)
        rp_state.update_confidence(confidence_score)
        
        if not is_roleplay:
            rp_state.increment_exit_condition()
            if rp_state.should_exit_from_sustained_shift():
                rp_state.end_roleplay_session(EXIT_CONDITIONS['sustained_topic_shift'])
                strategy.update({
                    'approach': APPROACH_TYPES['general'],
                    'needs_database': False,
                    'reasoning': 'Sustained topic shift detected - exiting roleplay mode',
                    'context_priority': CONTEXT_PRIORITIES['none']
                })
                return strategy
    
    # Process main strategy logic
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
    if is_roleplay or rp_state.is_roleplaying:
        return process_roleplay_strategy(user_message, turn_number, channel_context, confidence_score, triggers)
    
    # If not roleplay, handle standard message types
    return _handle_standard_message_types(user_message, user_lower, strategy, conversation_history)

def _handle_dgm_posts(triggers: List[str], user_message: str, rp_state, turn_number: int, channel_context: Dict) -> Optional[Dict[str, any]]:
    """Handle DGM (Deputy Game Master) posts."""
    
    if TRIGGER_TYPES['dgm_scene_setting'] in triggers:
        print(f"   🎬 DGM SCENE SETTING DETECTED - Starting roleplay session but no response")
        
        # DGM posts override channel restrictions - force start roleplay session
        print(f"   🚀 DGM OVERRIDE: Starting roleplay in any channel type")
        
        # Start new session if not already roleplaying
        if not rp_state.is_roleplaying:
            dgm_characters = []
            # Extract DGM characters from the DGM result
            dgm_result = _check_dgm_post(user_message)
            if dgm_result.get('characters'):
                dgm_characters = dgm_result['characters']
            
            rp_state.start_roleplay_session(turn_number, triggers, channel_context, dgm_characters)
        
        return {
            'approach': APPROACH_TYPES['dgm_scene_setting'],
            'needs_database': False,
            'reasoning': 'DGM scene setting - start roleplay but no response (channel restrictions overridden)',
            'context_priority': CONTEXT_PRIORITIES['none']
        }
    
    if TRIGGER_TYPES['dgm_scene_end'] in triggers:
        print(f"   🎬 DGM SCENE END DETECTED - Ending roleplay session")
        if rp_state.is_roleplaying:
            rp_state.end_roleplay_session(EXIT_CONDITIONS['dgm_scene_end'])
        
        return {
            'approach': APPROACH_TYPES['dgm_scene_end'],
            'needs_database': False,
            'reasoning': 'DGM scene end - end roleplay session',
            'context_priority': CONTEXT_PRIORITIES['none']
        }
    
    if TRIGGER_TYPES['dgm_controlled_elsie'] in triggers:
        print(f"   🎭 DGM-CONTROLLED ELSIE DETECTED - No response, add to context")
        
        # DGM posts override channel restrictions - force start roleplay session
        print(f"   🚀 DGM OVERRIDE: Starting/continuing roleplay in any channel type")
        
        # Get the DGM result to extract Elsie's content
        dgm_result = _check_dgm_post(user_message)
        elsie_content = dgm_result.get('elsie_content', '')
        
        # Start roleplay session if not already active
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(turn_number, triggers, channel_context)
        
        return {
            'approach': APPROACH_TYPES['dgm_controlled_elsie'],
            'needs_database': False,
            'reasoning': f'DGM controlling Elsie - no response, content: "{elsie_content[:50]}{"..." if len(elsie_content) > 50 else ""}" (channel restrictions overridden)',
            'context_priority': CONTEXT_PRIORITIES['dgm_elsie_context'],
            'elsie_content': elsie_content
        }
    
    return None  # No DGM post detected

def _handle_standard_message_types(user_message: str, user_lower: str, strategy: Dict, conversation_history: list) -> Dict[str, any]:
    """Handle standard (non-roleplay) message types."""
    
    print(f"\n🔍 STRATEGY ENGINE DEBUG:")
    print(f"   📝 Processing message: {user_message}")
    print(f"   🔄 Current strategy: {strategy}")
    
    # Check for continuation requests
    is_continuation = is_continuation_request(user_message)
    if is_continuation:
        # Get focus from conversation history if needed
        _, focus, _ = extract_continuation_focus(user_message, conversation_history)
        print(f"   ✅ Detected continuation request with focus: {focus}")
        strategy.update({
            'approach': APPROACH_TYPES['continuation'],
            'needs_database': True,
            'reasoning': f'Continuation request detected - focus: {focus}',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for log URL requests
    is_log_url, log_url = extract_ooc_log_url_request(user_message)
    if is_log_url:
        strategy.update({
            'approach': APPROACH_TYPES['log_url'],
            'needs_database': True,
            'reasoning': f'Log URL request detected - URL: {log_url}',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for character queries
    is_character, character_name = is_character_query(user_message)
    if is_character:
        strategy.update({
            'approach': APPROACH_TYPES['character_info'],
            'needs_database': True,
            'reasoning': f'Character query detected - character: {character_name}',
            'context_priority': CONTEXT_PRIORITIES['none'],
            'character_name': character_name
        })
        return strategy
    
    # Check for specific log requests
    is_specific_log = is_specific_log_request(user_message)
    if is_specific_log:
        strategy.update({
            'approach': APPROACH_TYPES['specific_log'],
            'needs_database': True,
            'reasoning': 'Specific log request detected',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for "tell me about" queries
    subject = extract_tell_me_about_subject(user_message)
    if subject:
        strategy.update({
            'approach': APPROACH_TYPES['tell_me_about'],
            'needs_database': True,
            'reasoning': f'"Tell me about" query detected - subject: {subject}',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for Stardancer queries
    is_stardancer = is_stardancer_query(user_message)
    if is_stardancer:
        strategy.update({
            'approach': APPROACH_TYPES['stardancer_info'],
            'needs_database': True,
            'reasoning': 'Stardancer query detected',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for Stardancer command queries
    is_command = is_stardancer_command_query(user_message)
    if is_command:
        strategy.update({
            'approach': APPROACH_TYPES['stardancer_command'],
            'needs_database': True,
            'reasoning': 'Stardancer command query detected',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for ship log queries
    is_ship_log, ship_details = extract_ship_log_query(user_message)
    if is_ship_log:
        strategy.update({
            'approach': APPROACH_TYPES['ship_log'],
            'needs_database': True,
            'reasoning': f'Ship log query detected - ship: {ship_details.get("ship")}',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for OOC queries
    is_ooc, ooc_subject = is_ooc_query(user_message)
    if is_ooc:
        strategy.update({
            'approach': APPROACH_TYPES['ooc'],
            'needs_database': False,
            'reasoning': f'OOC query detected - subject: {ooc_subject}',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for log queries
    if is_log_query(user_message):
        strategy.update({
            'approach': APPROACH_TYPES['log_query'],
            'needs_database': True,
            'reasoning': 'Log query detected',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for Federation Archives requests
    if is_federation_archives_request(user_message):
        strategy.update({
            'approach': APPROACH_TYPES['federation_archives'],
            'needs_database': True,
            'reasoning': 'Federation Archives request detected',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for ship+log queries
    is_ship_log, ship_name, log_type = is_ship_plus_log_query(user_message)
    if is_ship_log:
        strategy.update({
            'approach': APPROACH_TYPES['ship_log_combined'],
            'needs_database': True,
            'reasoning': f'Ship+log query detected - ship: {ship_name}, log type: {log_type}',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # Check for character+log queries
    is_char_log, char_name, log_type = is_character_plus_log_query(user_message)
    if is_char_log:
        strategy.update({
            'approach': APPROACH_TYPES['character_log_combined'],
            'needs_database': True,
            'reasoning': f'Character+log query detected - character: {char_name}, log type: {log_type}',
            'context_priority': CONTEXT_PRIORITIES['none']
        })
        return strategy
    
    # If we get here, treat as a general message
    strategy.update({
        'approach': APPROACH_TYPES['general'],
        'needs_database': False,
        'reasoning': 'General message or greeting detected',
        'context_priority': CONTEXT_PRIORITIES['none']
    })
    return strategy 