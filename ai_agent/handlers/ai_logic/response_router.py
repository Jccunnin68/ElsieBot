"""
Response Router - Main Entry Point for Message Handling
=====================================================

This module provides the single entry point for all message handling.
It checks roleplay mode and routes to the appropriate handler.

CRITICAL FLOW:
1. Message comes in
2. Check: Am I in roleplay mode?
3. Route to roleplay_handler OR non_roleplay_handler
4. Return ResponseDecision
"""

from typing import Dict, List, Optional

from .response_decision import ResponseDecision
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.dgm_handler import check_dgm_post
import re

# NEW: Import the enhanced decision engine
from .response_decision_engine import create_response_decision_engine


def route_message_to_handler(user_message: str, conversation_history: List, channel_context: Optional[Dict] = None) -> ResponseDecision:
    """
    Main entry point for all message handling. Routes to appropriate handler based on roleplay state.
    
    ENHANCED: Now uses the new response decision engine for roleplay scenarios.
    
    Args:
        user_message: The user's message content
        conversation_history: List of previous messages
        channel_context: Channel information (ID, name, type, etc.)
        
    Returns:
        ResponseDecision: Decision about how to respond
    """
    print(f"🎯 RESPONSE ROUTER - Processing message")
    print(f"   📝 Message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
    
    # Get current roleplay state
    rp_state = get_roleplay_state()
    turn_number = len(conversation_history) + 1
    
    print(f"   🎭 Roleplay State: {'ACTIVE' if rp_state.is_roleplaying else 'INACTIVE'}")
    
    # Check for cross-channel messages if in roleplay
    if rp_state.is_roleplaying:
        if not rp_state.is_message_from_roleplay_channel(channel_context):
            print(f"   🚫 Cross-channel message detected - returning busy response")
            return _handle_cross_channel_busy(rp_state, channel_context)
    
    # Check for DGM actions regardless of roleplay state
    dgm_result = check_dgm_post(user_message)
    if dgm_result['is_dgm']:
        print(f"   🎬 DGM Action detected: {dgm_result['action']}")
        return _process_dgm_action(dgm_result, user_message, turn_number, channel_context)
    
    # ENHANCED: Route based on roleplay state
    if rp_state.is_roleplaying:
        print(f"   🎭 ROUTING TO ENHANCED ROLEPLAY HANDLER")
        return _handle_roleplay_with_enhanced_intelligence(user_message, conversation_history, channel_context)
    else:
        print(f"   📝 ROUTING TO NON-ROLEPLAY HANDLER")
        return _handle_non_roleplay(user_message, conversation_history, channel_context)


def _handle_roleplay_with_enhanced_intelligence(user_message: str, conversation_history: List, channel_context: Dict) -> ResponseDecision:
    """
    ENHANCED: Handle roleplay messages using the new emotional intelligence system.
    
    This integrates:
    - ai_attention: Context gathering and roleplay state management
    - ai_emotion: Emotional intelligence and priority resolution
    - ai_logic: Decision engine and response strategy
    """
    print(f"   🧠 ENHANCED ROLEPLAY PROCESSING")
    
    try:
        # Get roleplay state
        rp_state = get_roleplay_state()
        turn_number = len(conversation_history) + 1
        
        # Step 1: Build comprehensive contextual cues
        from handlers.ai_attention.context_gatherer import build_contextual_cues
        contextual_cues = build_contextual_cues(user_message, rp_state, turn_number)
        
        # Add the original message to contextual cues for emotional analysis
        contextual_cues.current_message = user_message
        
        print(f"   📊 Contextual cues built:")
        print(f"      - Session mode: {contextual_cues.session_mode.value}")
        print(f"      - Current speaker: {contextual_cues.current_speaker}")
        print(f"      - Known characters: {list(contextual_cues.known_characters.keys())}")
        
        # Step 2: Use the enhanced decision engine
        decision_engine = create_response_decision_engine()
        response_decision = decision_engine.getNextResponseEnhanced(contextual_cues)
        
        # Step 3: Update roleplay state based on decision
        _update_roleplay_state_from_decision(response_decision, contextual_cues, rp_state, turn_number)
        
        # Step 4: Convert to final ResponseDecision format
        final_decision = _convert_to_final_response_decision(response_decision, contextual_cues)
        
        print(f"   ✅ ENHANCED ROLEPLAY DECISION COMPLETE:")
        print(f"      - Should respond: {final_decision.needs_ai_generation}")
        print(f"      - Strategy approach: {final_decision.strategy.get('approach', 'unknown')}")
        print(f"      - Reasoning: {final_decision.strategy.get('reasoning', 'No reasoning provided')}")
        
        return final_decision
        
    except Exception as e:
        print(f"   ❌ CRITICAL ERROR in enhanced roleplay processing: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
        
        # PHASE 3E: DO NOT fallback to old system - return safe default instead
        print(f"   🛡️ FABRICATION PROTECTION: Using safe default instead of old system fallback")
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="I'm having difficulty processing that request right now. Please try again in a moment.",
            strategy={
                'approach': 'safe_fallback',
                'needs_database': False,
                'reasoning': f'Enhanced decision engine error - safe fallback applied: {str(e)}',
                'context_priority': 'safety',
                'fabrication_controls_applied': True,
                'error_protection': True
            }
        )


def _update_roleplay_state_from_decision(response_decision, contextual_cues, rp_state, turn_number: int):
    """
    Update roleplay state based on the enhanced decision.
    """
    # Update conversation memory if available
    if hasattr(rp_state, 'add_conversation_turn'):
        current_speaker = contextual_cues.current_speaker or "User"
        addressed_to = response_decision.address_character
        
        rp_state.add_conversation_turn(
            speaker=current_speaker,
            message=getattr(contextual_cues, 'current_message', ''),
            turn_number=turn_number,
            addressed_to=addressed_to
        )
    
    # Update who Elsie might address in response
    if response_decision.should_respond and response_decision.address_character:
        rp_state.set_last_character_addressed(response_decision.address_character)
    
    # Update listening mode
    rp_state.set_listening_mode(
        not response_decision.should_respond,
        response_decision.reasoning
    )
    
    # Mark response turn if responding
    if response_decision.should_respond:
        rp_state.mark_response_turn(turn_number)


def _convert_to_final_response_decision(response_decision, contextual_cues) -> ResponseDecision:
    """
    Convert the enhanced ResponseDecision to the final ResponseDecision format.
    """
    from handlers.ai_attention.contextual_cues import ResponseType
    
    # Determine if AI generation is needed
    needs_ai_generation = response_decision.should_respond
    
    # Build strategy dictionary
    strategy = {
        'approach': _convert_response_type_to_approach(response_decision.response_type),
        'needs_database': _should_use_database(response_decision, contextual_cues),
        'reasoning': response_decision.reasoning,
        'context_priority': 'roleplay',
        'response_style': response_decision.response_style,
        'tone': response_decision.tone,
        'approach_style': response_decision.approach,
        'address_character': response_decision.address_character,
        'relationship_tone': response_decision.relationship_tone,
        'suggested_themes': response_decision.suggested_themes,
        'continuation_cues': response_decision.continuation_cues,
        'estimated_length': response_decision.estimated_length,
        'confidence': response_decision.confidence,
        'scene_impact': response_decision.scene_impact,
        
        # PHASE 3D: Fabrication control information
        'knowledge_to_use': getattr(response_decision, 'knowledge_to_use', []),
        'avoid_topics': getattr(response_decision, 'avoid_topics', []),
        
        # Contextual information
        'session_mode': contextual_cues.session_mode.value,
        'current_speaker': contextual_cues.current_speaker,
        'known_characters': list(contextual_cues.known_characters.keys()),
        'conversation_themes': contextual_cues.conversation_dynamics.themes,
        'emotional_tone': contextual_cues.conversation_dynamics.emotional_tone,
        'turn_number': contextual_cues.turn_number,
        
        # Enhanced decision information
        'enhanced_decision': True,
        'emotional_intelligence_used': True,
        'priority_resolution_used': True,
        'fabrication_controls_applied': True  # PHASE 3D: Mark that fabrication controls were used
    }
    
    return ResponseDecision(
        needs_ai_generation=needs_ai_generation,
        pre_generated_response=None,  # Enhanced decisions always need AI generation
        strategy=strategy
    )


def _convert_response_type_to_approach(response_type) -> str:
    """Convert ResponseType to strategy approach string."""
    from handlers.ai_attention.contextual_cues import ResponseType
    
    type_to_approach = {
        ResponseType.ACTIVE_DIALOGUE: 'roleplay_active',
        ResponseType.SUPPORTIVE_LISTEN: 'roleplay_supportive',
        ResponseType.SUBTLE_SERVICE: 'roleplay_subtle_service',
        ResponseType.GROUP_ACKNOWLEDGMENT: 'roleplay_group_response',
        ResponseType.IMPLICIT_RESPONSE: 'roleplay_implicit',
        ResponseType.TECHNICAL_EXPERTISE: 'roleplay_technical',
        ResponseType.NONE: 'roleplay_listening'
    }
    
    return type_to_approach.get(response_type, 'roleplay_active')


def _should_use_database(response_decision, contextual_cues) -> bool:
    """Determine if database access is needed for this response."""
    # Always use database for technical expertise
    from handlers.ai_attention.contextual_cues import ResponseType
    if response_decision.response_type == ResponseType.TECHNICAL_EXPERTISE:
        return True
    
    # Use database if character knowledge is needed
    if response_decision.address_character and contextual_cues.known_characters:
        return True
    
    # Use database if conversation themes suggest it
    themes = contextual_cues.conversation_dynamics.themes
    database_themes = ['ship_operations', 'stellar_cartography', 'crew_information', 'mission_logs']
    if any(theme in database_themes for theme in themes):
        return True
    
    # Default to not using database for simple responses
    return False


def _handle_non_roleplay(user_message: str, conversation_history: List, channel_context: Optional[Dict]) -> ResponseDecision:
    """
    Handle non-roleplay messages using the existing non-roleplay handler.
    """
    from .non_roleplay_handler import handle_non_roleplay_message
    return handle_non_roleplay_message(user_message, conversation_history)


def _process_dgm_action(dgm_result: Dict, user_message: str, turn_number: int, channel_context: Optional[Dict]):
    """Process DGM (Deputy Game Master) actions."""
    dgm_action = dgm_result['action']
    
    if dgm_action == 'scene_setting':
        print(f"   🎬 DGM Scene Setting - Starting roleplay session")
        
        # Start new roleplay session
        rp_state = get_roleplay_state()
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(
                turn_number=turn_number,
                initial_triggers=['dgm_scene_setting'],
                channel_context=channel_context,
                dgm_characters=dgm_result.get('characters', [])
            )
        
        # PHASE 2D: Store DGM scene context
        scene_context = dgm_result.get('scene_context', {})
        if scene_context:
            rp_state.store_dgm_scene_context(scene_context)
        
        # Return no-response decision with proper NO_RESPONSE string
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={
                'approach': 'dgm_scene_setting',
                'needs_database': False,
                'reasoning': 'DGM scene setting - no response needed',
                'context_priority': 'none'
            }
        )
    
    elif dgm_action == 'end_scene':
        print(f"   🎬 DGM Scene End - Ending roleplay session")
        
        # End roleplay session
        rp_state = get_roleplay_state()
        if rp_state.is_roleplaying:
            rp_state.end_roleplay_session('dgm_scene_end')
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={
                'approach': 'dgm_scene_end',
                'needs_database': False,
                'reasoning': 'DGM scene end - roleplay session ended',
                'context_priority': 'none'
            }
        )
    
    elif dgm_action == 'control_elsie':
        print(f"   🎭 DGM Controlled Elsie - Adding to context")
        
        # Ensure roleplay session is active
        rp_state = get_roleplay_state()
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(
                turn_number=turn_number,
                initial_triggers=['dgm_controlled_elsie'],
                channel_context=channel_context
            )
        
        # PHASE 2D: Store DGM scene context if present
        scene_context = dgm_result.get('scene_context', {})
        if scene_context:
            rp_state.store_dgm_scene_context(scene_context)
        
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy={
                'approach': 'dgm_controlled_elsie',
                'needs_database': False,
                'reasoning': f'DGM controlled Elsie - content: "{dgm_result.get("elsie_content", "")}"',
                'context_priority': 'dgm_elsie_context',
                'elsie_content': dgm_result.get('elsie_content', '')
            }
        )
    
    # Unknown DGM action
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response="NO_RESPONSE",
        strategy={
            'approach': 'general',
            'needs_database': False,
            'reasoning': f'Unknown DGM action: {dgm_action}',
            'context_priority': 'none'
        }
    )


def is_cross_channel_message(channel_context: Optional[Dict]) -> bool:
    """Check if this message is from a different channel than the current roleplay."""
    rp_state = get_roleplay_state()
    
    if not rp_state.is_roleplaying or not channel_context:
        return False
    
    return not rp_state.is_message_from_roleplay_channel(channel_context)


def _handle_cross_channel_busy(rp_state, channel_context: Dict) -> ResponseDecision:
    """Handle messages from different channels when in roleplay mode."""
    channel_info = rp_state.get_roleplay_channel_info()
    
    # Check if this is a DM
    is_dm = channel_context and channel_context.get('type', '').lower() in ['dm', 'group_dm']
    
    if is_dm:
        busy_message = f"I am currently roleplaying in {channel_info['channel_name']}. DM interactions are paused during roleplay sessions."
    else:
        busy_message = f"I am currently roleplaying in {channel_info['channel_name']}. Please try again later or join that thread."
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=busy_message,
        strategy={
            'approach': 'cross_channel_busy',
            'needs_database': False,
            'reasoning': f'Cross-channel message while roleplaying in {channel_info["channel_name"]}',
            'context_priority': 'none',
            'roleplay_channel': channel_info['channel_name']
        }
    ) 