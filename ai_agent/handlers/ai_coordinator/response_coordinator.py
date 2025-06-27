"""
Response Coordinator - Main Response Coordination Logic
======================================================

This module contains the main entry point for coordinating AI responses,
optimizing the flow to avoid expensive AI calls when possible.
"""

from typing import Dict

from handlers.ai_logic.response_router import route_message


def coordinate_response(user_message: str, conversation_history: list, channel_context: Dict = None) -> str:
    """
    Main entry point that preserves all existing logic but optimizes flow.
    Replaces direct calls to get_gemma_response().
    
    OPTIMIZATION: Only makes expensive AI API calls when actually needed.
    
    Flow:
    1. Extract decision using all existing guard rails
    2. If pre-generated response available, return immediately
    3. Otherwise, proceed with AI generation
    
    Benefits:
    - DGM posts return NO_RESPONSE without API calls
    - Listening mode returns NO_RESPONSE without API calls  
    - Subtle bar service generates simple responses without AI
    - Acknowledgments use pre-defined responses
    - Only complex conversations need AI generation
    
    This preserves ALL existing logic while being 3-5x more efficient
    for common scenarios like DGM sessions and roleplay listening.
    """
    
    # Log channel and monitoring information - PRESERVE EXISTING
    print(f"\n🌐 CHANNEL & MONITORING DEBUG:")
    if channel_context:
        channel_type = channel_context.get('type', 'unknown')
        channel_name = channel_context.get('name', 'unknown')
        is_thread = channel_context.get('is_thread', False)
        is_dm = channel_context.get('is_dm', False)
        print(f"   📍 Channel: {channel_name} (Type: {channel_type})")
        print(f"   🧵 Thread: {is_thread} | 💬 DM: {is_dm}")
        print(f"   📋 Full Context: {channel_context}")
    else:
        print(f"   ⚠️  No channel context provided - assuming allowed")
    
    # For now, return a simple response since the old routing system is being refactored
    # TODO: Implement proper routing with the new service architecture
    return route_message(user_message, channel_context)
    
    # COMMENTED OUT: Old complex routing logic
    # This will be reimplemented with the new service architecture
    """
    # Make the decision using existing logic
    decision = route_message_to_handler(user_message, conversation_history, channel_context)
    
    # Extract handler and approach info for debugging
    approach = decision.strategy.get('approach', 'unknown')
    reasoning = decision.strategy.get('reasoning', 'no reasoning provided')
    
    # Determine which handler was used based on approach
    if approach.startswith('roleplay_'):
        handler_type = "ROLEPLAY_HANDLER"
    elif approach in ['comprehensive', 'ship_info', 'character_info', 'logs', 'tell_me_about', 'federation_archives', 'url_request', 'general', 'continuation']:
        handler_type = "STANDARD_HANDLER"
    elif approach.startswith('mock_'):
        handler_type = "MOCK_RESPONSE"
    elif approach == 'dgm_scene_setting':
        handler_type = "DGM_HANDLER"
    else:
        handler_type = "UNKNOWN_HANDLER"
    
    # If no AI needed, return the pre-generated response
    if not decision.needs_ai_generation:
        print(f"✅ Pre-generated response: {decision.strategy['reasoning']}")
        
        # SAFETY CHECK: Ensure we never return None
        if decision.pre_generated_response is None:
            print(f"   ⚠️  WARNING: pre_generated_response is None, defaulting to NO_RESPONSE")
            print(f"   📋 Strategy: {decision.strategy}")
            response = "NO_RESPONSE"
        else:
            response = decision.pre_generated_response
        
        # Handle tracking for roleplay responses that don't need AI
        if decision.strategy['approach'] == 'roleplay_active':
            from handlers.service_container import get_roleplay_state
            rp_state = get_roleplay_state()
            turn_number = len(conversation_history) + 1
            
            # Track who Elsie addressed for simple responses
            if decision.strategy.get('response_reason') == 'subtle_bar_service':
                from handlers.service_container import get_character_tracking_service
                char_service = get_character_tracking_service()
                character_names = char_service.extract_character_names_from_emotes(user_message)
                if character_names:
                    rp_state.set_last_character_addressed(character_names[0])
                    print(f"   📝 TRACKING UPDATE: Elsie addressed {character_names[0]} (subtle service)")
            
            # Ensure Elsie's response is tracked in turn history
            if not rp_state.turn_history or rp_state.turn_history[-1][1] != "Elsie":
                rp_state.mark_response_turn(turn_number)
                print(f"   📝 ENSURED: Elsie's response turn tracked")
        
        return response
    
    # Otherwise, do the expensive AI generation
    print(f"🤖 AI GENERATION NEEDED: {decision.strategy['reasoning']}")
    from handlers.service_container import get_ai_engine
    ai_engine = get_ai_engine()
    ai_response = ai_engine.generate_response_with_decision(decision, user_message, conversation_history)
    
    return ai_response
    """ 