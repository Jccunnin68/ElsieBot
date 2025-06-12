"""
Decision Extractor - Response Decision Extraction Logic
======================================================

This module contains the logic for extracting response decisions from
message analysis, determining whether AI generation is needed or if
pre-generated responses can be used.
"""

import random
from typing import Dict

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


def extract_response_decision(user_message: str, conversation_history: list, channel_context: Dict = None) -> ResponseDecision:
    """
    Extract the decision-making logic from get_gemma_response() without changing it.
    Preserves all existing guard rails and logic.
    """
    
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
        if rp_state.is_roleplaying:
            rp_state.mark_character_turn(turn_number, character_names[0])
        else:
            print(f"   ⚠️  Character detected but not in roleplay mode - potential detection issue")

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
            pre_generated_response="*adjusts the ambient lighting thoughtfully*\n\nOf course. *returns to regular bartending mode* I'm here whenever you need anything. What draws your attention now?",
            strategy=strategy
        )

    # Handle roleplay listening mode - provide subtle presence responses - PRESERVE EXISTING
    if strategy['approach'] == 'roleplay_listening':
        should_interject = strategy.get('should_interject', False)
        listening_count = strategy.get('listening_turn_count', 0)
        
        print(f"   👂 LISTENING MODE RESPONSE:")
        print(f"      - Should Interject: {should_interject}")
        print(f"      - Listening Turn: {listening_count}")
        
        if should_interject:
            # Very occasional subtle interjections to maintain presence
            interjection_responses = [
                "*quietly tends to the bar in the background*",
                "*adjusts the ambient lighting subtly*",
                "*continues her work with practiced efficiency*",
                "*maintains the bar's atmosphere unobtrusively*"
            ]
            print(f"✨ SUBTLE INTERJECTION - Listening turn {listening_count}")
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
        
        # Generate a subtle acknowledgment that doesn't interrupt the flow
        acknowledgment_responses = [
            "*nods gracefully*",
            "*inclines head with a subtle smile*",
            "*acknowledges with quiet elegance*",
            "*gives a brief, appreciative nod*",
            "*smiles warmly and steps back*"
        ]
        
        response = random.choice(acknowledgment_responses)
        print(f"   🙏 Generated acknowledgment response: '{response}'")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=response,
            strategy=strategy
        )
    
    # Handle simple implicit responses - PRESERVE EXISTING
    if (strategy['approach'] == 'roleplay_active' and 
        strategy.get('response_reason') == 'simple_implicit_response'):
        
        print(f"   💬 SIMPLE IMPLICIT RESPONSE:")
        print(f"      - Character following up after Elsie addressed them")
        print(f"      - Using normal AI response generation for natural conversation")
        # Continue to normal AI generation for natural conversation
    
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