"""
Roleplay Message Handler - Context-Aware Character Interactions
==============================================================

This module handles ALL responses when Elsie is in roleplay mode.
Provides context-aware, character-driven responses including:
- Enhanced contextual intelligence from ai_attention
- Emotional intelligence from ai_emotion  
- Database queries via ai_wisdom (quick response mode)
- Character relationship tracking
- Cross-channel roleplay state management

CRITICAL: This handler is ONLY called when in roleplay mode.
ENHANCED: Quick database response mode for efficient roleplay flow.
"""

from typing import Dict, List, Optional

from .response_decision import ResponseDecision
from .query_detection import detect_query_type_with_conflicts


def handle_roleplay_message(user_message: str, conversation_history: List, channel_context: Dict) -> ResponseDecision:
    """
    Enhanced roleplay handler with quick database responses and contextual intelligence.
    
    Roleplay mode provides:
    - Quick database queries (single best result)
    - Enhanced contextual and emotional intelligence
    - Character relationship tracking
    - Cross-channel roleplay awareness
    - NO disambiguation (quick response flow)
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation turns
        channel_context: Channel and context information
        
    Returns:
        ResponseDecision with appropriate strategy
    """
    print(f"\n🎭 ROLEPLAY HANDLER - Enhanced quick response mode")
    
    # Handle cross-channel busy state first
    if is_cross_channel_message(channel_context):
        return handle_cross_channel_busy(None, channel_context)
    
    # Detect query type with conflict resolution
    query_info = detect_query_type_with_conflicts(user_message)
    
    print(f"   📋 Query Analysis: {query_info['type']} - {query_info.get('subject', 'N/A')}")
    if query_info.get('conflict_resolved'):
        print(f"      ⚖️  Conflict Resolution: {query_info['conflict_resolved']}")
    
    # Route to quick response strategies for database queries
    database_query_types = ['character', 'ship', 'ship_log', 'character_log', 'tell_me_about']
    if query_info['type'] in database_query_types:
        return _handle_roleplay_database_query(user_message, query_info)
    
    # Route to standard roleplay processing for non-database queries
    return _handle_standard_roleplay(user_message, conversation_history, channel_context)


def _handle_roleplay_database_query(user_message: str, query_info: Dict) -> ResponseDecision:
    """
    Quick database query for roleplay contexts - return single best result.
    
    KEY FEATURE: No disambiguation, just return the most relevant result quickly
    to maintain roleplay flow.
    """
    print(f"   🚀 ROLEPLAY QUICK DATABASE: {query_info['type']}")
    
    strategy = {
        'approach': 'roleplay_quick_database',
        'needs_database': True,
        'query_type': query_info['type'],
        'subject': query_info.get('subject'),
        'context_priority': 'roleplay',
        'reasoning': f"Roleplay quick database query: {query_info['type']} - {query_info.get('subject', 'N/A')}"
    }
    
    # Add specific query details
    if query_info.get('log_type'):
        strategy['log_type'] = query_info['log_type']
    
    # Add category intersection requirements
    if query_info.get('requires_category_intersection'):
        strategy['valid_categories'] = query_info['valid_categories']
        strategy['requires_category_intersection'] = True
        print(f"      📂 Category intersection required: {query_info['valid_categories']}")
    
    # Add conflict resolution info
    if query_info.get('conflict_resolved'):
        strategy['conflict_info'] = query_info['conflict_resolved']
        print(f"      ⚖️  Conflict resolved: {query_info['conflict_resolved']}")
    
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
        strategy=strategy
    )


def _handle_standard_roleplay(user_message: str, conversation_history: List, channel_context: Dict) -> ResponseDecision:
    """
    Standard roleplay processing using enhanced contextual intelligence.
    
    This uses the existing enhanced roleplay system with contextual cues
    and emotional intelligence integration.
    """
    print(f"   🎭 STANDARD ROLEPLAY PROCESSING")
    
    try:
        # Import roleplay state management
        from ..ai_attention.state_manager import get_roleplay_state
        
        # Get current roleplay session state
        session_id = channel_context.get('channel_id', 'unknown')
        rp_state = get_roleplay_state()
        turn_number = len(conversation_history) + 1
        
        print(f"      📊 Roleplay State: {rp_state.current_mode}")
        print(f"      🔄 Turn: {turn_number}")
        
        # Enhanced contextual intelligence processing
        from ..ai_attention.conversation_memory import ConversationMemory
        
        dgm = ConversationMemory()
        dgm_result = dgm.process_message_enhanced(
            user_message, 
            turn_number, 
            conversation_history, 
            channel_context
        )
        
        print(f"      🧠 DGM Processing: {dgm_result.get('processing_approach', 'unknown')}")
        
        # Process through decision engine
        response_decision = _process_dgm_action(dgm_result, user_message, turn_number, channel_context)
        
        # Update roleplay state
        _update_roleplay_state_from_decision(response_decision, dgm_result.get('contextual_cues'), rp_state, turn_number)
        
        # Convert to final response decision
        final_decision = _convert_to_final_response_decision(response_decision, dgm_result.get('contextual_cues'))
        
        return final_decision
        
    except Exception as e:
        print(f"   ❌ ERROR in standard roleplay processing: {e}")
        # Fallback to simple roleplay response
        return ResponseDecision(
            needs_ai_generation=True,
            pre_generated_response=None,
            strategy={
                'approach': 'roleplay_fallback',
                'needs_database': False,
                'reasoning': f'Roleplay processing error fallback: {e}',
                'context_priority': 'roleplay'
            }
        )


def handle_cross_channel_busy(rp_state, channel_context: Dict) -> ResponseDecision:
    """
    Handle cross-channel busy state - Elsie is active in another channel.
    
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


def _process_dgm_action(dgm_result: Dict, user_message: str, turn_number: int, channel_context: Optional[Dict]):
    """
    Process DGM (Dynamic Group Memory) action and convert to response decision.
    
    This bridges the DGM system with the response decision system.
    """
    try:
        from .response_decision_engine import create_response_decision_engine
        
        contextual_cues = dgm_result.get('contextual_cues')
        if not contextual_cues:
            print(f"      ⚠️  No contextual cues from DGM")
            return _create_basic_response_decision(user_message)
        
        # Use enhanced decision engine
        decision_engine = create_response_decision_engine()
        enhanced_decision = decision_engine.getNextResponseEnhanced(contextual_cues)
        
        return enhanced_decision
        
    except Exception as e:
        print(f"      ❌ Error processing DGM action: {e}")
        return _create_basic_response_decision(user_message)


def _create_basic_response_decision(user_message: str):
    """Create a basic response decision as fallback."""
    try:
        from handlers.ai_attention.contextual_cues import create_response_decision, ResponseType
        
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


def is_cross_channel_message(channel_context: Optional[Dict]) -> bool:
    """
    Check if this is a cross-channel message where Elsie might be busy.
    
    This helps manage roleplay state across multiple channels.
    """
    if not channel_context:
        return False
    
    try:
        # Implementation would check roleplay state across channels
        # For now, return False as this requires roleplay state management
        return False
        
    except Exception as e:
        print(f"      ⚠️  Error checking cross-channel state: {e}")
        return False 