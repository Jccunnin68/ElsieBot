"""
Decision Extractor - Response Decision Extraction Logic
======================================================

This module contains the logic for extracting response decisions from
message analysis, determining whether AI generation is needed or if
pre-generated responses can be used.
"""

import random
from typing import Dict, Optional

from config import GEMMA_API_KEY
from .response_decision import ResponseDecision
from .strategy_engine import determine_response_strategy

# Import from ai_attention handlers (Phase 6A)
from handlers.ai_attention.character_tracking import extract_character_names_from_emotes
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.response_logic import extract_drink_from_emote as _extract_drink_from_emote
from handlers.ai_emotion import (
    get_reset_response,
    get_simple_continuation_response,
    get_menu_response
)
from handlers.ai_attention.response_logic import should_elsie_respond_in_roleplay


def detect_mock_response_type(user_message: str) -> Optional[str]:
    """
    Detect what type of mock response this message would trigger.
    Returns the mock response type or None if not a mock response.
    """
    from handlers.ai_emotion.drink_menu import handle_drink_request, is_menu_request
    from handlers.ai_emotion.greetings import handle_greeting, handle_farewell, handle_status_inquiry
    from handlers.ai_emotion.personality_contexts import is_simple_chat
    
    # Check each mock response type in order
    try:
        from handlers.ai_logic.query_detection import is_federation_archives_request
        if is_federation_archives_request(user_message):
            return 'federation_archives'  # Keep as-is
    except ImportError:
        archives_patterns = ['federation archives', 'check archives', 'search archives']
        if any(pattern in user_message.lower() for pattern in archives_patterns):
            return 'federation_archives'  # Keep as-is
    
    if is_menu_request(user_message):
        return 'menu'  # EXCLUDED from AI variety
    
    if handle_drink_request(user_message):
        return 'drink_order'  # Enhance with AI
    
    if handle_greeting(user_message):
        return 'greeting'  # Enhance with AI
    
    if handle_status_inquiry(user_message):
        return 'status_inquiry'  # Enhance with AI
    
    if handle_farewell(user_message):
        return 'farewell'  # Enhance with AI
    
    if is_simple_chat(user_message):
        return 'conversational'  # Enhance with AI
    
    return None


def should_enhance_mock_with_ai(mock_type: str, api_key_available: bool, is_roleplay: bool) -> bool:
    """
    Determine if this mock response should be enhanced with AI variety.
    Only applies when in roleplay mode with API key available.
    """
    if not api_key_available or not is_roleplay:
        return False
    
    # Exclude certain types from AI enhancement
    excluded_types = ['federation_archives', 'menu']
    if mock_type in excluded_types:
        return False
    
    # 80% chance for enhancement
    return random.random() < 0.8


def should_use_ai_variety_for_roleplay(api_key_available: bool) -> bool:
    """
    Determine if we should use AI generation for roleplay variety.
    Returns True 80% of the time when API key is available.
    """
    if not api_key_available:
        return False
    return random.random() < 0.8  # 80% chance


def extract_response_decision(user_message: str, conversation_history: list, channel_context: Dict = None) -> ResponseDecision:
    """
    Extract the decision-making logic from get_gemma_response() without changing it.
    Preserves all existing guard rails and logic.
    """
    
    # CRITICAL: Check for ANY DGM post FIRST - Elsie NEVER responds to DGM posts
    import re
    if re.search(r'^\s*\[DGM\]', user_message, re.IGNORECASE):
        print(f"   🎬 DGM POST DETECTED - NEVER RESPOND")
        print(f"   🚫 Message starts with [DGM]: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        
        # Still need to process the DGM post for roleplay state management
        from handlers.ai_attention.dgm_handler import check_dgm_post
        dgm_result = check_dgm_post(user_message)
        
        # Create a minimal strategy for DGM handling
        dgm_strategy = {
            'approach': f"dgm_{dgm_result.get('action', 'post')}",
            'needs_database': False,
            'reasoning': f"DGM post detected - {dgm_result.get('action', 'unknown')} - NEVER RESPOND",
            'context_priority': 'none'
        }
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy=dgm_strategy
        )
    
    # Get roleplay state and log current status - PRESERVE EXISTING
    rp_state = get_roleplay_state()
    turn_number = len(conversation_history) + 1
    print(f"   🎭 Roleplay Active: {rp_state.is_roleplaying}")
    if rp_state.is_roleplaying:
        print(f"   👥 Participants: {rp_state.get_participant_names()}")
        print(f"   👂 Listening Mode: {rp_state.listening_mode}")
        print(f"   🔢 Listening Count: {rp_state.listening_turn_count}")
        print(f"   📅 Session Turn: {rp_state.session_start_turn}")
        print(f"   💬 Last Character Elsie Addressed: {rp_state.last_character_elsie_addressed}")
        print(f"   🗣️ Turn History: {rp_state.turn_history}")

    # UNIVERSAL CHARACTER TURN TRACKING - PRESERVE EXISTING
    character_names = extract_character_names_from_emotes(user_message)
    if character_names:
        print(f"   📝 UNIVERSAL TRACKING: Character speaking: {character_names[0]} (Turn {turn_number})")
        print(f"   📝 ALL DETECTED CHARACTERS: {character_names}")
        
        # DEBUG: Check if Elsie is being detected as a character
        for char in character_names:
            if char.lower() in ['elsie', 'elise', 'elsy', 'els', 'bartender', 'barkeep', 'barmaid']:
                print(f"   ⚠️  WARNING: Elsie detected as character: '{char}' - This should not happen!")
        
        if rp_state.is_roleplaying:
            print(f"   📝 ADDING CHARACTER TO ROLEPLAY: {character_names[0]}")
            rp_state.mark_character_turn(turn_number, character_names[0])
        else:
            print(f"   ⚠️  Character detected but not in roleplay mode - potential detection issue")

    # NEW: Check for mock responses in roleplay mode BEFORE other logic
    if rp_state.is_roleplaying:
        mock_type = detect_mock_response_type(user_message)
        if mock_type and should_enhance_mock_with_ai(mock_type, bool(GEMMA_API_KEY), True):
            print(f"   🎭 ROLEPLAY MOCK ENHANCEMENT - {mock_type.upper()} using AI generation")
            
            # Create strategy for AI-enhanced mock response
            mock_strategy = {
                'approach': 'roleplay_mock_enhanced',
                'needs_database': True,  # Use roleplay context
                'reasoning': f'Roleplay {mock_type} with AI variety',
                'context_priority': 'roleplay',
                'ai_variety_type': mock_type,
                'participants': rp_state.get_participant_names(),
                'mock_response_type': mock_type
            }
            return ResponseDecision(
                needs_ai_generation=True,
                pre_generated_response=None,
                strategy=mock_strategy
            )
        elif mock_type:
            print(f"   🎭 ROLEPLAY MOCK - {mock_type.upper()} using canned response (20% case or excluded)")
            # Fall through to normal strategy determination for canned response

    # Strategy determination - PRESERVE EXISTING
    strategy = determine_response_strategy(user_message, conversation_history, channel_context)
    print(f"\n🧠 ELSIE'S INNER MONOLOGUE:")
    print(f"   💭 Reasoning: {strategy['reasoning']}")
    print(f"   📋 Approach: {strategy['approach']}")
    print(f"   🔍 Needs Database: {strategy['needs_database']}")
    print(f"   🎯 Context Priority: {strategy['context_priority']}")
    
    # Log monitoring decisions - PRESERVE EXISTING
    if strategy['approach'].startswith('roleplay'):
        print(f"   🎭 ROLEPLAY MONITORING ACTIVE:")
        print(f"      - Approach: {strategy['approach']}")
        if 'response_reason' in strategy:
            print(f"      - Response Reason: {strategy['response_reason']}")
        if 'participants' in strategy:
            print(f"      - Tracked Participants: {strategy['participants']}")
        if 'should_interject' in strategy:
            print(f"      - Should Interject: {strategy['should_interject']}")
    elif rp_state.is_roleplaying:
        print(f"   ⚠️  IN ROLEPLAY BUT NOT RP APPROACH - Potential Issue!")
    
    # Handle special cases that don't need AI processing - PRESERVE EXISTING
    if strategy['approach'] == 'reset':
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=get_reset_response(),
            strategy=strategy
        )
    
    if strategy['approach'] == 'simple_continuation':
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=get_simple_continuation_response(),
            strategy=strategy
        )
    
    # CRITICAL: Double-check for DGM posts before any other processing
    from handlers.ai_attention.dgm_handler import check_dgm_post
    dgm_check = check_dgm_post(user_message)
    if dgm_check['is_dgm']:
        print(f"   🚨 CRITICAL DGM CHECK - DGM POST DETECTED:")
        print(f"      - Action: {dgm_check['action']}")
        print(f"      - Strategy Approach: {strategy['approach']}")
        print(f"      - DGM Controlled Elsie: {dgm_check['dgm_controlled_elsie']}")
        print(f"   🎬 FORCING NO_RESPONSE FOR DGM POST")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy=strategy
        )

    # Handle DGM posts - never respond - PRESERVE EXISTING
    if strategy['approach'] in ['dgm_scene_setting', 'dgm_scene_end']:
        print(f"   🎬 DGM POST - No response generated")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy=strategy
        )
    
    # Handle DGM-controlled Elsie posts - never respond but add to context - PRESERVE EXISTING
    if strategy['approach'] == 'dgm_controlled_elsie':
        print(f"   🎭 DGM-CONTROLLED ELSIE - No response, content added to context")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy=strategy
        )
    
    # Handle roleplay exit - PRESERVE EXISTING
    if strategy['approach'] == 'roleplay_exit':
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="*adjusts the ambient lighting thoughtfully*\n\nOf course. *returns to regular bartending mode* I'm here if you need anything.",
            strategy=strategy
        )

    # CRITICAL FIX: Check for implicit responses BEFORE handling listening mode
    # The strategy engine may have set 'roleplay_listening' but we need to double-check
    # if this should actually be an implicit response
    if strategy['approach'] == 'roleplay_listening':
        # Re-check if this should be an implicit response
       
        
        # Use the already imported get_roleplay_state and existing rp_state
        turn_number = len(conversation_history) + 1
        should_respond, response_reason = should_elsie_respond_in_roleplay(user_message, rp_state, turn_number)
        
        print(f"   🔍 DOUBLE-CHECKING IMPLICIT RESPONSE:")
        print(f"      - Should Respond: {should_respond}")
        print(f"      - Response Reason: {response_reason}")
        
        # If implicit response detected, override the listening strategy
        if should_respond and response_reason in ['implicit_single_character', 'implicit_multi_character']:
            print(f"   💬 OVERRIDING LISTENING MODE - Implicit response detected: {response_reason}")
            strategy['approach'] = 'roleplay_active'
            strategy['response_reason'] = response_reason
            return ResponseDecision(
                needs_ai_generation=True,
                pre_generated_response=None,
                strategy=strategy
            )
        
        # Otherwise, proceed with listening mode logic
        should_interject = strategy.get('should_interject', False)
        listening_count = strategy.get('listening_turn_count', 0)
        
        print(f"   👂 LISTENING MODE RESPONSE:")
        print(f"      - Should Interject: {should_interject}")
        print(f"      - Listening Turn: {listening_count}")
        
        if should_interject:
            if should_use_ai_variety_for_roleplay(bool(GEMMA_API_KEY)):
                print(f"✨ LISTENING INTERJECTION - Using AI generation for variety")
                strategy['ai_variety_type'] = 'listening_interjection'
                return ResponseDecision(
                    needs_ai_generation=True,
                    pre_generated_response=None,
                    strategy=strategy
                )
            else:
                # Keep existing canned response logic
                interjection_responses = [
                    "*quietly tends to the bar in the background*",
                    "*adjusts the ambient lighting subtly*",
                    "*continues her work with practiced efficiency*",
                    "*maintains the bar's atmosphere unobtrusively*"
                ]
                print(f"✨ LISTENING INTERJECTION - Using canned response (40% case)")
                return ResponseDecision(
                    needs_ai_generation=False,
                    pre_generated_response=random.choice(interjection_responses),
                    strategy=strategy
                )
        else:
            # Most of the time, completely silent listening
            print(f"👂 SILENT LISTENING - Turn {listening_count}")
            return ResponseDecision(
                needs_ai_generation=False,
                pre_generated_response="NO_RESPONSE",
                strategy=strategy
            )
    
    # Handle subtle bar service responses - PRESERVE EXISTING
    if strategy['approach'] == 'roleplay_active' and strategy.get('response_reason') == 'subtle_bar_service':
        # Extract the drink and character name
        drink = _extract_drink_from_emote(user_message)
        character_names = extract_character_names_from_emotes(user_message)
        character = character_names[0] if character_names else "the customer"
        
        print(f"   🥃 SUBTLE BAR SERVICE:")
        print(f"      - Drink: {drink}")
        print(f"      - Character: {character}")
        
        # Generate a simple service response
        if drink == 'drink':
            response = f"*gets a drink for {character}*"
        else:
            response = f"*gets a {drink} for {character}*"
        
        print(f"   🍺 Generated subtle service response: '{response}'")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=response,
            strategy=strategy
        )
    
    # Handle acknowledgment + redirect responses - PRESERVE EXISTING
    if (strategy['approach'] == 'roleplay_active' and 
        strategy.get('response_reason', '').startswith('acknowledgment_then_redirect_to_')):
        
        # Extract the character being redirected to
        other_character = strategy['response_reason'].replace('acknowledgment_then_redirect_to_', '')
        
        print(f"   🙏 ACKNOWLEDGMENT + REDIRECT:")
        print(f"      - Acknowledging thanks, then conversation moves to: {other_character}")
        
        if should_use_ai_variety_for_roleplay(bool(GEMMA_API_KEY)):
            print(f"   🙏 ACKNOWLEDGMENT - Using AI generation for variety")
            strategy['ai_variety_type'] = 'acknowledgment'
            strategy['other_character'] = other_character
            return ResponseDecision(
                needs_ai_generation=True,
                pre_generated_response=None,
                strategy=strategy
            )
        else:
            # Keep existing canned response logic
            acknowledgment_responses = [
                "*nods gracefully*",
                "*inclines head with a subtle smile*",
                "*acknowledges with quiet elegance*",
                "*gives a brief, appreciative nod*",
                "*smiles warmly and steps back*",
            ]
            
            response = random.choice(acknowledgment_responses)
            print(f"   🙏 Generated acknowledgment response: '{response}' (40% case)")
            return ResponseDecision(
                needs_ai_generation=False,
                pre_generated_response=response,
                strategy=strategy
            )
    
    # Handle new implicit response types - NEW
    if (strategy['approach'] == 'roleplay_active' and 
        strategy.get('response_reason') in ['implicit_single_character', 'implicit_multi_character']):
        
        response_reason = strategy.get('response_reason')
        print(f"   💬 IMPLICIT RESPONSE ({response_reason.upper()}):")
        print(f"      - Character continuing conversation chain with Elsie")
        print(f"      - Using AI response generation for natural conversation flow")
        
        return ResponseDecision(
            needs_ai_generation=True,
            pre_generated_response=None,
            strategy=strategy
        )
    
    # Menu requests - PRESERVE EXISTING
    user_lower = user_message.lower()
    if "menu" in user_lower or "what do you have" in user_lower or "what can you make" in user_lower:
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=get_menu_response(),
            strategy=strategy
        )
    
    # Handle OOC URL requests - PRESERVE EXISTING
    if strategy['approach'] == 'ooc_url':
        from ai_wisdom import handle_ooc_url_request
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=handle_ooc_url_request(user_message),
            strategy=strategy
        )
    
    # Everything else needs AI generation
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
        strategy=strategy
    ) 