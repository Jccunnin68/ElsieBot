"""
Roleplay Handler - Engine-Driven Roleplay Logic
================================================

This module handles all incoming messages during an active roleplay session,
now acting as a lightweight orchestrator for the AttentionEngine.
"""
from typing import List, Dict

from .response_decision import ResponseDecision
from handlers.ai_wisdom.roleplay_context_builder import get_enhanced_roleplay_context

def handle_roleplay_message(user_message: str, conversation_history: List[Dict]) -> ResponseDecision:
    """
    Handles messages during a roleplay session using the new engine-driven architecture.

    Flow:
    1.  Check for non-LLM DGM commands first for efficiency.
    2.  If not a DGM command, delegate to the AttentionEngine to get the response strategy.
    3.  If the engine decides a response is needed, build the context for that strategy.
    4.  Return the final decision.
    """
    # Import dependencies lazily to avoid circular imports
    from ..service_container import get_roleplay_state, get_attention_engine
    from ..ai_attention.dgm_handler import check_dgm_post, handle_dgm_command
    
    rp_state = get_roleplay_state()
    
    # 1. Handle DGM commands (non-LLM)
    dgm_decision = handle_dgm_command(user_message)
    if dgm_decision:
        dgm_post_info = check_dgm_post(user_message)
        if dgm_post_info and dgm_post_info.get('is_scene_end'):
            rp_state.end_roleplay_session()
            print("🎬 DGM has ended the scene. Roleplay session terminated.")
        return dgm_decision

    # 2. Delegate to the AttentionEngine for all other roleplay messages
    attention_engine = get_attention_engine()
    decision = attention_engine.determine_response_strategy(user_message, conversation_history, rp_state)

    # 3. If a response is needed, build the necessary context
    if decision.needs_ai_generation:
        print(f"   🛠️ Building context for selected approach: {decision.strategy.get('approach')}")
        if 'reasoning' not in decision.strategy:
            decision.strategy['reasoning'] = f"Roleplay response determined by AttentionEngine with approach: {decision.strategy.get('approach', 'unknown')}"
        # The context builder now receives the entire strategy dictionary
        context_prompt = get_enhanced_roleplay_context(decision.strategy, user_message, conversation_history)
        decision.pre_generated_response = context_prompt

    return decision


def handle_cross_channel_busy(rp_state, channel_context: Dict) -> ResponseDecision:
    """
    Handles messages sent to a different channel while Elsie is in roleplay.
    
    Returns a pre-generated response indicating she's busy elsewhere.
    """
    print(f"   🚫 CROSS-CHANNEL BUSY STATE")
    
    # Get channel info for context
    current_channel = channel_context.get('channel_name', 'this channel')
    
    busy_responses = [
        f"*[Elsie seems focused on something happening in another part of the station]*",
        f"*[Elsie appears to be handling something urgent elsewhere and doesn't notice the activity in {current_channel}]*",
        f"*[Elsie is clearly engaged with patrons in another area of the ship]*"
    ]
    
    import random
    busy_response = random.choice(busy_responses)
    
    strategy = {
        'approach': 'roleplay_cross_channel_busy',
        'needs_database': False,
        'reasoning': f'Cross-channel busy - roleplay active in {rp_state.roleplay_channel}',
        'context_priority': 'minimal'
    }
    
    return ResponseDecision(
        needs_ai_generation=False,
        pre_generated_response=f"*is busy with patrons in another area*",
        strategy=strategy
    )


def _update_roleplay_state_from_decision(response_decision, contextual_cues, rp_state, turn_number: int):
    """
    Update roleplay state based on response decision.
    
    This maintains continuity across roleplay sessions and tracks
    character relationships and conversation dynamics.
    """
    try:
        if not contextual_cues:
            return
        
        # Update last activity tracking
        current_speaker = getattr(contextual_cues, 'current_speaker', None)
        if current_speaker:
            rp_state.last_speaker = current_speaker
            rp_state.last_turn_number = turn_number
        
        # Update character relationship tracking if response involves characters
        if hasattr(contextual_cues, 'known_characters') and contextual_cues.known_characters:
            for character, info in contextual_cues.known_characters.items():
                if character not in rp_state.character_relationships:
                    rp_state.character_relationships[character] = {
                        'first_interaction': turn_number,
                        'interaction_count': 1,
                        'last_interaction': turn_number
                    }
                else:
                    rp_state.character_relationships[character]['interaction_count'] += 1
                    rp_state.character_relationships[character]['last_interaction'] = turn_number
        
        print(f"      📊 Roleplay state updated: speaker={current_speaker}, turn={turn_number}")
        
    except Exception as e:
        print(f"      ⚠️  Error updating roleplay state: {e}")


def _convert_to_final_response_decision(response_decision, contextual_cues) -> ResponseDecision:
    """
    Convert enhanced response decision to final ResponseDecision format.
    
    This bridges the enhanced contextual intelligence system with the
    final response decision format expected by the coordinator.
    """
    try:
        # Convert response type to approach
        approach = _convert_response_type_to_approach(response_decision.response_type)
        
        # Determine if database context is needed
        needs_database = _should_use_database(response_decision, contextual_cues)
        
        # Build comprehensive strategy
        strategy = {
            'approach': approach,
            'needs_database': needs_database,
            'reasoning': response_decision.reasoning,
            'context_priority': 'roleplay',
            'response_style': getattr(response_decision, 'response_style', 'natural'),
            'tone': getattr(response_decision, 'tone', 'friendly'),
            'confidence': getattr(response_decision, 'confidence', 0.8)
        }
        
        # Add character addressing if available
        if hasattr(response_decision, 'address_character') and response_decision.address_character:
            strategy['address_character'] = response_decision.address_character
        
        # Add knowledge context if available
        if hasattr(response_decision, 'knowledge_to_use') and response_decision.knowledge_to_use:
            strategy['knowledge_context'] = response_decision.knowledge_to_use
        
        return ResponseDecision(
            needs_ai_generation=response_decision.should_respond,
            pre_generated_response=None,
            strategy=strategy
        )
        
    except Exception as e:
        print(f"      ❌ Error converting to final response decision: {e}")
        # Safe fallback
        return ResponseDecision(
            needs_ai_generation=True,
            pre_generated_response=None,
            strategy={
                'approach': 'roleplay_active',
                'needs_database': False,
                'reasoning': f'Conversion error fallback: {e}',
                'context_priority': 'roleplay'
            }
        )


def _convert_response_type_to_approach(response_type) -> str:
    """Convert ResponseType enum to approach string."""
    try:
        response_type_str = str(response_type).lower()
        
        if 'active_dialogue' in response_type_str:
            return 'roleplay_active'
        elif 'supportive_listen' in response_type_str:
            return 'roleplay_supportive'
        elif 'group_acknowledgment' in response_type_str:
            return 'roleplay_group'
        elif 'subtle_service' in response_type_str:
            return 'roleplay_service'
        elif 'technical_expertise' in response_type_str:
            return 'roleplay_technical'
        else:
            return 'roleplay_active'
    except:
        return 'roleplay_active'


def _should_use_database(response_decision, contextual_cues) -> bool:
    """
    Determine if database context is needed for roleplay response.
    
    Enhanced to use database context for technical expertise and character knowledge.
    """
    try:
        # Check if response involves technical expertise
        if hasattr(response_decision, 'response_type'):
            response_type_str = str(response_decision.response_type).lower()
            if 'technical_expertise' in response_type_str:
                return True
        
        # Check if there are known characters to enhance
        if contextual_cues and hasattr(contextual_cues, 'known_characters'):
            if contextual_cues.known_characters and len(contextual_cues.known_characters) > 0:
                return True
        
        # Check for conversation themes that would benefit from database context
        if contextual_cues and hasattr(contextual_cues, 'conversation_dynamics'):
            dynamics = contextual_cues.conversation_dynamics
            if hasattr(dynamics, 'themes'):
                database_themes = ['stellar_cartography', 'navigation', 'exploration', 'technology', 'starfleet']
                if any(theme in dynamics.themes for theme in database_themes):
                    return True
        
        return False
        
    except Exception as e:
        print(f"      ⚠️  Error determining database usage: {e}")
        return False


def _convert_llm_routing_to_response_decision(routing_result: Dict, user_message: str):
    """
    Convert LLM routing result to response decision format.
    
    This bridges the new LLM routing system with the existing response decision system.
    """
    try:
        from ..ai_attention.contextual_cues import create_response_decision, ResponseType
        
        # Get routing information
        approach = routing_result.get('processing_approach', 'roleplay_active')
        confidence = routing_result.get('routing_confidence', 0.7)
        reasoning = routing_result.get('reasoning', 'LLM routing decision')
        response_type_str = routing_result.get('suggested_response_type', 'active_dialogue')
        
        # Convert response type string to enum
        response_type_map = {
            'active_dialogue': ResponseType.ACTIVE_DIALOGUE,
            'supportive_listen': ResponseType.SUPPORTIVE_LISTEN,
            'subtle_service': ResponseType.SUBTLE_SERVICE,
            'technical_expertise': ResponseType.TECHNICAL_EXPERTISE,
            'group_acknowledgment': ResponseType.GROUP_ACKNOWLEDGMENT,
            'none': ResponseType.NONE
        }
        
        response_type = response_type_map.get(response_type_str, ResponseType.ACTIVE_DIALOGUE)
        
        # Create response decision
        response_decision = create_response_decision(
            should_respond=True,
            response_type=response_type,
            reasoning=reasoning
        )
        
        # Add additional attributes
        response_decision.confidence = confidence
        response_decision.approach = approach
        response_decision.response_style = routing_result.get('response_style', 'natural')
        response_decision.tone = routing_result.get('tone', 'friendly')
        
        print(f"      ✅ LLM routing converted to response decision: {approach}")
        return response_decision
        
    except Exception as e:
        print(f"      ❌ Error converting LLM routing: {e}")
        # Fallback to basic response decision
        return _create_basic_response_decision(user_message)


def _create_basic_response_decision(user_message: str):
    """Create a basic response decision as fallback."""
    try:
        from ..ai_attention.contextual_cues import create_response_decision, ResponseType
        
        return create_response_decision(
            should_respond=True,
            response_type=ResponseType.ACTIVE_DIALOGUE,
            reasoning="Basic roleplay response fallback"
        )
    except:
        # Ultimate fallback - create minimal response decision structure
        class BasicResponseDecision:
            def __init__(self):
                self.should_respond = True
                self.response_type = type('ResponseType', (), {'value': 'active_dialogue'})()
                self.reasoning = "Minimal fallback response"
                self.confidence = 0.7
                self.response_style = 'natural'
                self.tone = 'friendly'
        
        return BasicResponseDecision()


 