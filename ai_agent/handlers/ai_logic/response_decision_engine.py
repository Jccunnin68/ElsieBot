"""
Response Decision Engine - Core Decision Making with Emotional Intelligence
==========================================================================

This module contains the primary decision engine that integrates emotional intelligence
from ai_emotion with contextual intelligence from ai_attention to make holistic 
response decisions for roleplay scenarios.

This replaces the fragmented decision logic with a comprehensive AI-driven system.
"""

from typing import Dict, List, Optional, Tuple
import traceback

from handlers.ai_logic.response_decision import ResponseDecision


class ResponseDecisionEngine:
    """
    Core decision engine that integrates emotional intelligence from ai_emotion
    with contextual intelligence from ai_attention to make holistic decisions.
    
    This is the primary decision maker that was moved from conversation_memory.py
    and enhanced with full emotional intelligence integration.
    
    ENHANCED: Now integrates with AI wisdom components for database context.
    """
    
    def __init__(self):
        self.last_analysis = None  # Cache for debugging
        
    def getNextResponseEnhanced(self, contextual_cues) -> 'ResponseDecision':
        """
        Enhanced response decision making using contextual and emotional intelligence.
        
        MOVED from conversation_memory.py and enhanced with ai_emotion integration.
        ENHANCED: Now integrates with AI wisdom for database context when needed.
        
        Args:
            contextual_cues: ElsieContextualCues with rich contextual state
            
        Returns:
            ResponseDecision with comprehensive response guidance
        """
        print(f"🧠 ENHANCED DECISION ENGINE - Turn {contextual_cues.turn_number}")
        
        try:
            # Import here to avoid circular dependencies
            from handlers.ai_attention.contextual_cues import ResponseDecision, ResponseType, create_response_decision
            
            # Step 1: Emotional Intelligence Analysis
            emotional_context = self._analyze_emotional_context(contextual_cues)
            
            # Step 2: Context Sensitivity Analysis  
            addressing_analysis = self._analyze_addressing_context(contextual_cues)
            
            # Step 3: Priority Conflict Resolution
            decision_result = self._resolve_decision_conflicts(
                emotional_context, 
                addressing_analysis, 
                contextual_cues
            )
            
            # Step 4: Build Comprehensive ResponseDecision
            response_decision = self._build_response_decision(
                decision_result,
                emotional_context,
                addressing_analysis,
                contextual_cues
            )
            
            # Step 5: ENHANCED - Generate AI Wisdom Context if needed
            if self._should_use_database_context(response_decision, contextual_cues):
                print(f"   🧠 AI WISDOM INTEGRATION: Adding database context")
                wisdom_context = self._get_ai_wisdom_context(response_decision, contextual_cues)
                response_decision.knowledge_to_use.extend(wisdom_context.get('database_facts', []))
                response_decision.continuation_cues.extend(wisdom_context.get('context_cues', []))
            
            # Cache for debugging
            self.last_analysis = {
                'emotional_context': emotional_context,
                'addressing_analysis': addressing_analysis,
                'decision_result': decision_result,
                'contextual_cues': contextual_cues
            }
            
            print(f"   ✅ ENHANCED DECISION GENERATED:")
            print(f"      - Should respond: {response_decision.should_respond}")
            print(f"      - Response type: {response_decision.response_type.value}")
            print(f"      - Reasoning: {response_decision.reasoning}")
            print(f"      - Confidence: {response_decision.confidence:.2f}")
            print(f"      - AI Wisdom: {'✅ Used' if self._should_use_database_context(response_decision, contextual_cues) else '❌ Not needed'}")
            
            return response_decision
            
        except Exception as e:
            print(f"   ❌ ERROR in getNextResponseEnhanced: {e}")
            print(f"   📋 Traceback: {traceback.format_exc()}")
            # Return safe default
            from handlers.ai_attention.contextual_cues import create_response_decision, ResponseType
            return create_response_decision(
                should_respond=False,
                response_type=ResponseType.NONE,
                reasoning=f"Error in enhanced analysis: {e}"
            )
    
    def _analyze_emotional_context(self, contextual_cues) -> Dict:
        """
        Analyze emotional context using ai_emotion modules.
        """
        try:
            # Import emotional intelligence modules
            from handlers.ai_emotion.emotional_analysis import analyze_emotional_context
            from handlers.ai_emotion.conversation_emotions import ConversationEmotionalIntelligence
            
            # Extract message from contextual cues
            current_message = getattr(contextual_cues, 'current_message', '')
            if not current_message:
                # Try to get from addressing context
                addressing_context = getattr(contextual_cues, 'addressing_context', None)
                if addressing_context and hasattr(addressing_context, 'original_message'):
                    current_message = addressing_context.original_message
                else:
                    current_message = "No message content available"
            
            # Basic emotional analysis
            emotional_context = analyze_emotional_context(current_message)
            
            # Enhanced conversation emotional analysis
            conversation_emotions = ConversationEmotionalIntelligence()
            
            # Build conversation history from contextual cues
            conversation_history = []
            if hasattr(contextual_cues, 'recent_activity'):
                conversation_history = contextual_cues.recent_activity
            
            # Enhanced emotional support detection
            needs_support, support_confidence, support_reasoning = (
                conversation_emotions.detect_emotional_support_opportunity_enhanced(
                    current_message, 
                    conversation_history
                )
            )
            
            # Combine analyses
            enhanced_emotional_context = {
                **emotional_context,
                'enhanced_support_needs': needs_support,
                'enhanced_support_confidence': support_confidence,
                'enhanced_support_reasoning': support_reasoning,
                'conversation_emotional_analysis': True
            }
            
            print(f"   🎭 EMOTIONAL ANALYSIS COMPLETE:")
            print(f"      - Emotional tone: {emotional_context.get('emotional_tone', 'neutral')}")
            print(f"      - Support needed: {needs_support} (confidence: {support_confidence:.2f})")
            print(f"      - Vulnerability level: {emotional_context.get('vulnerability_level', 'low')}")
            
            return enhanced_emotional_context
            
        except Exception as e:
            print(f"   ⚠️  ERROR in emotional analysis: {e}")
            return {
                'emotional_tone': 'neutral',
                'needs_support': False,
                'support_confidence': 0.0,
                'error': str(e)
            }
    
    def _analyze_addressing_context(self, contextual_cues) -> Dict:
        """
        Analyze addressing context using ai_emotion context sensitivity AND contextual cues.
        
        FIXED: Now properly integrates with contextual cues addressing detection.
        """
        try:
            # FIRST: Check contextual cues for direct addressing
            addressing_context = getattr(contextual_cues, 'addressing_context', None)
            
            if addressing_context:
                direct_mentions = getattr(addressing_context, 'direct_mentions', [])
                group_addressing = getattr(addressing_context, 'group_addressing', False)
                service_requests = getattr(addressing_context, 'service_requests', [])
                
                print(f"   👥 CONTEXTUAL CUES ADDRESSING:")
                print(f"      - Direct mentions: {direct_mentions}")
                print(f"      - Group addressing: {group_addressing}")
                print(f"      - Service requests: {service_requests}")
                
                # PRIORITY 1: Direct individual addressing (highest priority)
                if direct_mentions:
                    addressing_type = 'individual_address'
                    addressing_confidence = 0.9
                    print(f"   🎯 INDIVIDUAL ADDRESSING DETECTED from contextual cues")
                    
                    return {
                        'addressing_type': addressing_type,
                        'addressing_confidence': addressing_confidence,
                        'is_individual_address': True,
                        'is_contextual_mention': False,
                        'is_direct_group': False,
                        'direct_mentions': direct_mentions,
                        'source': 'contextual_cues'
                    }
                
                # PRIORITY 2: Group addressing from contextual cues
                elif group_addressing:
                    addressing_type = 'direct_group'
                    addressing_confidence = 0.85
                    print(f"   👥 GROUP ADDRESSING DETECTED from contextual cues")
                    
                    return {
                        'addressing_type': addressing_type,
                        'addressing_confidence': addressing_confidence,
                        'is_individual_address': False,
                        'is_contextual_mention': False,
                        'is_direct_group': True,
                        'source': 'contextual_cues'
                    }
            
            # FALLBACK: Use ai_emotion context sensitivity for edge cases
            from handlers.ai_emotion.context_sensitivity import distinguish_group_vs_contextual
            
            # Extract message
            current_message = getattr(contextual_cues, 'current_message', '')
            if not current_message:
                current_message = "No message content available"
            
            # Analyze addressing patterns (only for group vs contextual distinction)
            addressing_type, addressing_confidence = distinguish_group_vs_contextual(current_message)
            
            # Enhanced addressing analysis
            addressing_analysis = {
                'addressing_type': addressing_type,
                'addressing_confidence': addressing_confidence,
                'is_individual_address': False,
                'is_contextual_mention': addressing_type == 'contextual_mention',
                'is_direct_group': addressing_type == 'direct_group',
                'message_analyzed': current_message,
                'source': 'ai_emotion_fallback'
            }
            
            print(f"   👥 ADDRESSING ANALYSIS COMPLETE (fallback):")
            print(f"      - Type: {addressing_type}")
            print(f"      - Confidence: {addressing_confidence:.2f}")
            print(f"      - Source: ai_emotion fallback")
            
            return addressing_analysis
            
        except Exception as e:
            print(f"   ⚠️  ERROR in addressing analysis: {e}")
            return {
                'addressing_type': 'no_addressing',
                'addressing_confidence': 0.5,
                'is_individual_address': False,
                'is_contextual_mention': False,
                'is_direct_group': False,
                'error': str(e),
                'source': 'error_fallback'
            }
    
    def _resolve_decision_conflicts(self, emotional_context: Dict, addressing_analysis: Dict, contextual_cues) -> Dict:
        """
        Resolve conflicts between different response types using ai_emotion priority resolution.
        """
        try:
            # Check for conflicts between emotional support and group addressing
            needs_support = emotional_context.get('enhanced_support_needs', False)
            support_confidence = emotional_context.get('enhanced_support_confidence', 0.0)
            
            addressing_confidence = addressing_analysis.get('addressing_confidence', 0.0)
            is_group_addressing = addressing_analysis.get('addressing_type') == 'direct_group'
            
            # If both emotional support and group addressing detected, resolve conflict
            if needs_support and is_group_addressing and support_confidence > 0.4 and addressing_confidence > 0.4:
                
                try:
                    from handlers.ai_emotion.priority_resolution import resolve_emotional_vs_group_conflict
                    
                    # Extract message for context
                    current_message = getattr(contextual_cues, 'current_message', '')
                    if not current_message:
                        addressing_context = getattr(contextual_cues, 'addressing_context', None)
                        if addressing_context and hasattr(addressing_context, 'original_message'):
                            current_message = addressing_context.original_message
                    
                    # Build context for resolution
                    resolution_context = {
                        'message': current_message,
                        'vulnerability_level': emotional_context.get('vulnerability_level', 'low'),
                        'emotional_tone': emotional_context.get('emotional_tone', 'neutral')
                    }
                    
                    decision_type, reasoning, final_confidence = resolve_emotional_vs_group_conflict(
                        support_confidence,
                        addressing_confidence,
                        current_message,
                        resolution_context
                    )
                    
                    print(f"   ⚖️  PRIORITY CONFLICT RESOLVED:")
                    print(f"      - Decision: {decision_type}")
                    print(f"      - Reasoning: {reasoning}")
                    print(f"      - Final confidence: {final_confidence:.2f}")
                    
                    return {
                        'primary_decision': decision_type,
                        'confidence': final_confidence,
                        'reasoning': reasoning,
                        'conflict_resolved': True,
                        'original_support_confidence': support_confidence,
                        'original_addressing_confidence': addressing_confidence
                    }
                    
                except Exception as priority_error:
                    print(f"   ⚠️  Priority resolution error: {priority_error}")
                    # Fallback to emotional support if high confidence
                    if support_confidence > addressing_confidence:
                        return {
                            'primary_decision': 'emotional_support',
                            'confidence': support_confidence,
                            'reasoning': f"Fallback to emotional support due to priority resolution error: {priority_error}",
                            'conflict_resolved': False
                        }
            
            # No conflict or conflict resolution not needed
            # Check for individual addressing (highest priority)
            is_individual_addressing = addressing_analysis.get('is_individual_address', False)
            
            if is_individual_addressing:
                return {
                    'primary_decision': 'individual_addressing',
                    'confidence': addressing_confidence,
                    'reasoning': 'Individual addressing detected - Elsie is directly mentioned',
                    'conflict_resolved': False
                }
            elif needs_support and support_confidence >= 0.4:
                return {
                    'primary_decision': 'emotional_support',
                    'confidence': support_confidence,
                    'reasoning': emotional_context.get('enhanced_support_reasoning', 'Emotional support needed'),
                    'conflict_resolved': False
                }
            elif is_group_addressing and addressing_confidence >= 0.6:
                return {
                    'primary_decision': 'group_addressing',
                    'confidence': addressing_confidence,
                    'reasoning': 'Group addressing detected',
                    'conflict_resolved': False
                }
            else:
                return {
                    'primary_decision': 'standard_response',
                    'confidence': 0.7,
                    'reasoning': 'Standard response - no special conditions detected',
                    'conflict_resolved': False
                }
                
        except Exception as e:
            print(f"   ⚠️  ERROR in decision conflict resolution: {e}")
            return {
                'primary_decision': 'standard_response',
                'confidence': 0.5,
                'reasoning': f'Error in conflict resolution: {e}',
                'conflict_resolved': False
            }
    
    def _build_response_decision(self, decision_result: Dict, emotional_context: Dict, 
                               addressing_analysis: Dict, contextual_cues) -> 'ResponseDecision':
        """
        Build the final ResponseDecision object with all analysis integrated.
        """
        try:
            from handlers.ai_attention.contextual_cues import ResponseDecision, ResponseType, create_response_decision
            
            primary_decision = decision_result.get('primary_decision', 'standard_response')
            confidence = decision_result.get('confidence', 0.7)
            reasoning = decision_result.get('reasoning', 'Standard response')
            
            # Determine response type and whether to respond
            if primary_decision == 'individual_addressing':
                should_respond = True
                response_type = ResponseType.ACTIVE_DIALOGUE
                approach = "responsive"
                tone = "friendly"
                
            elif primary_decision == 'emotional_support':
                should_respond = True
                response_type = ResponseType.SUPPORTIVE_LISTEN
                approach = "empathetic"
                tone = "gentle"
                
            elif primary_decision == 'group_addressing':
                should_respond = True
                response_type = ResponseType.GROUP_ACKNOWLEDGMENT
                approach = "welcoming"
                tone = "friendly"
                
            else:
                # Standard response - check other conditions from contextual cues
                should_respond = self._should_respond_standard(contextual_cues)
                response_type = ResponseType.ACTIVE_DIALOGUE if should_respond else ResponseType.NONE
                approach = "responsive"
                tone = "natural"
            
            # Build comprehensive ResponseDecision
            response_decision = ResponseDecision(
                should_respond=should_respond,
                response_type=response_type,
                reasoning=reasoning,
                confidence=confidence,
                response_style=approach,
                tone=tone,
                approach=approach,
                address_character=getattr(contextual_cues, 'current_speaker', None),
                relationship_tone="friendly",
                knowledge_to_use=emotional_context.get('contextual_clues', []),
                suggested_themes=self._extract_themes_from_analysis(emotional_context, contextual_cues),
                continuation_cues=self._extract_continuation_cues(emotional_context, addressing_analysis),
                estimated_length="brief",
                urgency="normal",
                scene_impact="neutral"
            )
            
            return response_decision
            
        except Exception as e:
            print(f"   ❌ ERROR building ResponseDecision: {e}")
            # Safe fallback
            from handlers.ai_attention.contextual_cues import create_response_decision, ResponseType
            return create_response_decision(
                should_respond=False,
                response_type=ResponseType.NONE,
                reasoning=f"Error building decision: {e}"
            )
    
    def _should_respond_standard(self, contextual_cues) -> bool:
        """
        Determine if Elsie should respond in standard cases (non-emotional, non-group).
        """
        # Check addressing context
        addressing_context = getattr(contextual_cues, 'addressing_context', None)
        if addressing_context:
            # Check for direct mentions
            direct_mentions = getattr(addressing_context, 'direct_mentions', [])
            if direct_mentions and any('elsie' in mention.lower() for mention in direct_mentions):
                return True
            
            # Check for service requests
            service_requests = getattr(addressing_context, 'service_requests', [])
            if service_requests:
                return True
        
        # Check for implicit opportunities
        if hasattr(contextual_cues, 'last_addressed_by_elsie'):
            current_speaker = getattr(contextual_cues, 'current_speaker', None)
            last_addressed = getattr(contextual_cues, 'last_addressed_by_elsie', None)
            if current_speaker and last_addressed and current_speaker.lower() == last_addressed.lower():
                return True
        
        # Default to not responding in standard cases
        return False
    
    def _extract_themes_from_analysis(self, emotional_context: Dict, contextual_cues) -> List[str]:
        """Extract relevant themes for response generation."""
        themes = []
        
        # Add emotional themes
        if emotional_context.get('emotional_tone') != 'neutral':
            themes.append(f"emotional_support_{emotional_context.get('emotional_tone', 'general')}")
        
        # Add vulnerability themes
        vulnerability = emotional_context.get('vulnerability_level', 'low')
        if vulnerability in ['moderate', 'high']:
            themes.append(f"vulnerability_{vulnerability}")
        
        # Add conversation themes from contextual cues
        if hasattr(contextual_cues, 'conversation_dynamics'):
            dynamics = contextual_cues.conversation_dynamics
            if hasattr(dynamics, 'themes'):
                themes.extend(dynamics.themes[:2])  # Add up to 2 conversation themes
        
        return themes[:3]  # Limit to 3 themes
    
    def _extract_continuation_cues(self, emotional_context: Dict, addressing_analysis: Dict) -> List[str]:
        """Extract continuation cues for natural conversation flow."""
        cues = []
        
        # Emotional continuation cues
        if emotional_context.get('enhanced_support_needs'):
            cues.append("provide_emotional_support")
            cues.append("validate_feelings")
        
        # Addressing continuation cues
        if addressing_analysis.get('is_direct_group'):
            cues.append("acknowledge_group")
        elif addressing_analysis.get('is_contextual_mention'):
            cues.append("address_context_sensitively")
        
        return cues
    
    def get_last_analysis_debug(self) -> Optional[Dict]:
        """Get the last analysis for debugging purposes."""
        return self.last_analysis
    
    def get_last_analysis(self) -> Optional[Dict]:
        """Get the last analysis for testing and debugging purposes."""
        return self.get_last_analysis_debug()
    
    def _should_use_database_context(self, response_decision, contextual_cues) -> bool:
        """
        Determine if database context from AI wisdom is needed.
        """
        # Always use database context for technical expertise
        if response_decision.response_type.value == "technical_expertise":
            return True
            
        # Use database context if there are known characters to learn about
        if contextual_cues.known_characters and len(contextual_cues.known_characters) > 0:
            return True
            
        # Use database context if current themes suggest it
        themes = contextual_cues.conversation_dynamics.themes
        database_themes = ['stellar_cartography', 'navigation', 'exploration', 'technology', 'starfleet']
        if any(theme in database_themes for theme in themes):
            return True
            
        return False
    
    def _get_ai_wisdom_context(self, response_decision, contextual_cues) -> Dict:
        """
        Get database context from AI wisdom components.
        """
        try:
            # Import AI wisdom coordinator
            from handlers.ai_wisdom.context_coordinator import get_context_for_strategy
            
            # Build strategy dict for AI wisdom
            wisdom_strategy = {
                'approach': 'roleplay_active',
                'needs_database': True,
                'reasoning': response_decision.reasoning,
                'context_priority': 'roleplay',
                'response_type': response_decision.response_type.value,
                'current_speaker': contextual_cues.current_speaker,
                'known_characters': list(contextual_cues.known_characters.keys()),
                'conversation_themes': contextual_cues.conversation_dynamics.themes
            }
            
            # Extract message for AI wisdom
            current_message = getattr(contextual_cues, 'current_message', '')
            
            # Get wisdom context
            wisdom_context_str = get_context_for_strategy(wisdom_strategy, current_message)
            
            # Parse context into structured data
            parsed_context = self._parse_wisdom_context(wisdom_context_str)
            
            print(f"   🧠 AI WISDOM CONTEXT GENERATED:")
            print(f"      - Context length: {len(wisdom_context_str)} chars")
            print(f"      - Database facts: {len(parsed_context.get('database_facts', []))}")
            print(f"      - Context cues: {len(parsed_context.get('context_cues', []))}")
            
            return parsed_context
            
        except Exception as e:
            print(f"   ❌ ERROR getting AI wisdom context: {e}")
            return {'database_facts': [], 'context_cues': []}
    
    def _parse_wisdom_context(self, context_str: str) -> Dict:
        """
        Parse AI wisdom context string into structured data.
        """
        # For now, return basic structure
        # TODO: Enhance with actual parsing of context sections
        return {
            'database_facts': ['AI wisdom context available'],
            'context_cues': ['Database information integrated'],
            'full_context': context_str
        }


def create_response_decision_engine() -> ResponseDecisionEngine:
    """
    Factory function to create a ResponseDecisionEngine instance.
    
    This provides a clean interface for other modules to create
    the decision engine without directly instantiating the class.
    """
    return ResponseDecisionEngine() 