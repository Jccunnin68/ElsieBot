"""
Response Decision Engine - Core Decision Making with Emotional Intelligence
==========================================================================

This module contains the primary decision engine that integrates emotional intelligence
from ai_emotion with contextual intelligence from ai_attention to make holistic 
response decisions for roleplay scenarios.

This replaces the fragmented decision logic with a comprehensive AI-driven system.
"""

import re
from typing import Dict, List, Optional, Tuple
import traceback

from .response_decision import ResponseDecision
from ..ai_wisdom.llm_query_processor import is_fallback_response


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
        
        # PHASE 3A: Fabrication prevention controls
        self.fabrication_prevention_enabled = True
        self.accuracy_validation_enabled = True
        self.strict_mode = True  # Requires accurate information or admits lack of knowledge
        
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
            
            # PHASE 3A: Fabrication Prevention Validation
            if self.fabrication_prevention_enabled:
                response_decision = self._apply_fabrication_controls(
                    response_decision, 
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
            
            # Ensure emotional_context is a dictionary
            if not isinstance(emotional_context, dict):
                print(f"   ⚠️  WARNING: emotional_context is not a dict, got {type(emotional_context)}: {emotional_context}")
                emotional_context = {
                    'emotional_tone': 'neutral',
                    'emotional_confidence': 0.8,
                    'needs_support': False,
                    'support_confidence': 0.0,
                    'intensity': 'low',
                    'vulnerability_level': 'low',
                    'support_indicators': [],
                    'emotional_keywords': [],
                    'contextual_clues': []
                }
            
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
                'enhanced_support_needs': False,
                'enhanced_support_confidence': 0.0,
                'enhanced_support_reasoning': f'Error in analysis: {str(e)}',
                'conversation_emotional_analysis': False,
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
            
            # Check for character-to-character interactions (high priority)
            is_character_to_character = self._check_character_to_character_interaction(contextual_cues)
            
            # Check for service requests (high priority)
            service_requests = self._check_service_requests(contextual_cues)
            
            if is_individual_addressing:
                return {
                    'primary_decision': 'individual_addressing',
                    'confidence': addressing_confidence,
                    'reasoning': 'Individual addressing detected - Elsie is directly mentioned',
                    'conflict_resolved': False
                }
            elif service_requests:
                return {
                    'primary_decision': 'service_request',
                    'confidence': 0.9,
                    'reasoning': f"Service request detected: {', '.join(service_requests)}",
                    'conflict_resolved': False,
                    'service_types': service_requests
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
            elif is_character_to_character:
                return {
                    'primary_decision': 'character_to_character',
                    'confidence': 0.8,
                    'reasoning': 'Character-to-character interaction detected - Elsie should listen',
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
                
            elif primary_decision == 'service_request':
                should_respond = True
                response_type = ResponseType.SUBTLE_SERVICE
                approach = "service-oriented"
                tone = "professional"
                
            elif primary_decision == 'character_to_character':
                should_respond = False
                response_type = ResponseType.NONE
                approach = "roleplay_listening"
                tone = "observant"
                
            else:
                # Check for technical expertise opportunities before standard response
                technical_expertise_detected = self._check_technical_expertise(contextual_cues)
                
                if technical_expertise_detected:
                    should_respond = True
                    response_type = ResponseType.TECHNICAL_EXPERTISE
                    approach = "knowledgeable"
                    tone = "professional"
                    reasoning = "Technical expertise opportunity detected"
                    confidence = 0.8
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
    
    def _check_character_to_character_interaction(self, contextual_cues) -> bool:
        """
        Check if this is a character-to-character interaction where Elsie should listen.
        
        FIXED: Adds missing character-to-character detection with higher priority than technical expertise.
        ENHANCED: Now properly handles responses to Elsie's questions.
        CRITICAL FIX: Check for direct character addressing BEFORE general question patterns.
        """
        try:
            # Get addressing context
            addressing_context = getattr(contextual_cues, 'addressing_context', None)
            if not addressing_context:
                return False
            
            # Check if other characters are being addressed (not Elsie)
            other_interactions = getattr(addressing_context, 'other_interactions', [])
            if other_interactions:
                print(f"   👥 CHARACTER-TO-CHARACTER INTERACTION DETECTED: {other_interactions}")
                return True
            
            # Check current message for character names being addressed
            current_message = getattr(contextual_cues, 'current_message', '')
            if not current_message:
                return False
            
            # PRIORITY 1: Check for direct character addressing patterns FIRST
            # This must come before general question detection to catch "Zarina, what do you think"
            addressing_pattern = r'\[([^\]]+)\]\s*["\']([A-Z][a-z]+)[,\s]'
            match = re.search(addressing_pattern, current_message)
            
            if match:
                speaker = match.group(1).strip()
                addressed = match.group(2).strip()
                
                # ENHANCED VALIDATION: Make sure addressed isn't a question word
                question_words = ['can', 'could', 'would', 'will', 'do', 'did', 'does', 'what', 'where', 'when', 'why', 'who', 'how']
                if addressed.lower() in question_words:
                    print(f"   ❌ REJECTED CHARACTER-TO-CHARACTER: '{addressed}' is a question word, not a character name")
                    return False
                
                # Make sure it's not addressing Elsie
                if addressed.lower() not in ['elsie', 'el']:
                    print(f"   👥 CHARACTER-TO-CHARACTER DETECTED: {speaker} addressing {addressed}")
                    return True
            
            # PRIORITY 2: Check if this is a direct question to Elsie (only after checking for character addressing)
            elsie_question_patterns = [
                r'\bcan\s+you\s+(?:tell|show|explain|help|get|find)',
                r'\bwould\s+you\s+(?:mind|please|be\s+able)',
                r'\bcould\s+you\s+(?:tell|show|explain|help|get|find)',
                r'\bdo\s+you\s+(?:know|have|remember)',
                r'\bwhat\s+(?:do\s+you\s+)?(?:know|think|remember)',
                r'\bhow\s+(?:do\s+you|can\s+you)',
                r'\bwhere\s+(?:is|are|can\s+i\s+find)',
                r'\bwhen\s+(?:did|was|will)',
                r'\bwhy\s+(?:did|is|are)',
                r'\bwho\s+(?:is|was|are)',
            ]
            
            message_lower = current_message.lower()
            for pattern in elsie_question_patterns:
                if re.search(pattern, message_lower):
                    print(f"   🎯 DIRECT QUESTION TO ELSIE DETECTED: '{pattern}' - not character-to-character")
                    return False
            
            # PRIORITY 3: Check if this is a response to Elsie's previous question/statement
            # Get recent activity to see if Elsie was the last speaker
            recent_activity = getattr(contextual_cues, 'recent_activity', [])
            if recent_activity:
                # Check if the last activity was from Elsie
                last_activity = recent_activity[-1] if recent_activity else ""
                if 'elsie' in last_activity.lower():
                    # Check for response patterns that indicate answering Elsie's question
                    elsie_response_patterns = [
                        r'\b(?:yes|yeah|yep|yup|uh-huh|mhm),?\s',  # Affirmative responses
                        r'\b(?:no|nope|nah|uh-uh),?\s',  # Negative responses
                        r'\bthat\'?s\s+(?:right|correct|true|wrong|false|not\s+right)',  # Confirmation/denial
                        r'\bi\s+(?:think|believe|guess|suppose)',  # Opinion responses
                        r'\bmaybe|perhaps|possibly|probably',  # Uncertain responses
                        r'\bwell,?\s',  # Thoughtful responses
                        r'\bactually,?\s',  # Clarifying responses
                        r'\bof\s+course',  # Obvious responses
                        r'\babsolutely|definitely|certainly',  # Strong affirmatives
                        r'\bnot\s+really|not\s+exactly|not\s+quite',  # Qualified negatives
                    ]
                    
                    for pattern in elsie_response_patterns:
                        if re.search(pattern, message_lower):
                            print(f"   💬 RESPONSE TO ELSIE DETECTED: '{pattern}' - not character-to-character")
                            return False
            
            return False
            
        except Exception as e:
            print(f"   ⚠️  ERROR checking character-to-character interaction: {e}")
            return False

    def _check_service_requests(self, contextual_cues) -> List[str]:
        """
        Check if there are service requests in the contextual cues.
        """
        try:
            addressing_context = getattr(contextual_cues, 'addressing_context', None)
            if addressing_context:
                service_requests = getattr(addressing_context, 'service_requests', [])
                if service_requests:
                    print(f"   🍺 SERVICE REQUESTS DETECTED: {service_requests}")
                    return service_requests
            return []
        except Exception as e:
            print(f"   ⚠️  ERROR checking service requests: {e}")
            return []
    
    def _check_technical_expertise(self, contextual_cues) -> bool:
        """
        Check if this is a technical expertise opportunity (stellar cartography, etc.).
        
        FIXED: Implements the missing technical expertise detection from the original system.
        """
        try:
            # Check if both expertise and themes align for stellar cartography
            current_expertise = getattr(contextual_cues, 'current_expertise', [])
            conversation_themes = getattr(contextual_cues, 'conversation_dynamics', None)
            
            if conversation_themes:
                themes = getattr(conversation_themes, 'themes', [])
                
                # Check for stellar cartography expertise opportunity
                if 'stellar_cartography' in current_expertise and 'stellar_cartography' in themes:
                    print(f"   🔬 TECHNICAL EXPERTISE DETECTED: Stellar cartography")
                    return True
                
                # Check for other technical expertise areas
                if 'ship_operations' in current_expertise and 'ship_operations' in themes:
                    print(f"   🔬 TECHNICAL EXPERTISE DETECTED: Ship operations")
                    return True
            
            return False
            
        except Exception as e:
            print(f"   ⚠️  ERROR checking technical expertise: {e}")
            return False

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
            from ..ai_wisdom.context_coordinator import get_context_for_strategy
            
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
            
            # Check if this is a fallback response and handle appropriately
            if is_fallback_response(wisdom_context_str):
                print(f"   ⚠️  AI WISDOM FALLBACK DETECTED - adjusting response strategy")
                response_decision = self._handle_fallback_response(response_decision, wisdom_context_str, contextual_cues)
            
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
    
    def _handle_fallback_response(self, response_decision, fallback_content: str, contextual_cues):
        """
        Handle fallback responses from the LLM query processor.
        Adjusts response strategy to work with limited information.
        """
        print(f"   🔄 HANDLING FALLBACK RESPONSE")
        
        # Determine if this is a roleplay context
        session_mode = getattr(contextual_cues, 'session_mode', None)
        is_roleplay_context = session_mode and 'roleplay' in str(session_mode).lower()
        
        if is_roleplay_context:
            # For roleplay contexts, adjust to handle the fallback naturally
            response_decision.approach = "fallback_roleplay"
            response_decision.tone = "apologetic_but_natural"
            
            # Add fallback handling instructions
            fallback_instructions = [
                "FALLBACK SCENARIO: Database processing encountered limitations.",
                "Present the limitation naturally as Elsie having difficulty with her systems.",
                "Use the provided fallback response as guidance for your in-character response.",
                "Maintain roleplay immersion while acknowledging the limitation."
            ]
            
            if not response_decision.knowledge_to_use:
                response_decision.knowledge_to_use = []
            response_decision.knowledge_to_use.extend(fallback_instructions)
            
            # Add fallback theme
            if not response_decision.suggested_themes:
                response_decision.suggested_themes = []
            response_decision.suggested_themes.append("system_limitation_roleplay")
            
        else:
            # For non-roleplay contexts, be direct about the limitation
            response_decision.approach = "fallback_direct"
            response_decision.tone = "informative"
            
            # Add direct fallback instructions
            fallback_instructions = [
                "FALLBACK SCENARIO: Database processing is currently limited.",
                "Present the limitation directly and suggest alternatives.",
                "Use the provided fallback response as your primary response.",
                "Suggest the user try again later or rephrase their query."
            ]
            
            if not response_decision.knowledge_to_use:
                response_decision.knowledge_to_use = []
            response_decision.knowledge_to_use.extend(fallback_instructions)
            
            # Add fallback theme
            if not response_decision.suggested_themes:
                response_decision.suggested_themes = []
            response_decision.suggested_themes.append("system_limitation_direct")
        
        # Update reasoning to reflect fallback handling
        response_decision.reasoning += " | Fallback response handling activated"
        
        print(f"      - Fallback approach: {response_decision.approach}")
        print(f"      - Fallback tone: {response_decision.tone}")
        print(f"      - Roleplay context: {is_roleplay_context}")
        
        # For now, return basic structure
        # TODO: Enhance with actual parsing of context sections
        return {
            'database_facts': ['AI wisdom context available'],
            'context_cues': ['Database information integrated'],
            'full_context': fallback_content
        }

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

    def _apply_fabrication_controls(self, response_decision, contextual_cues):
        """
        PHASE 3A: Apply fabrication prevention controls to response decisions.
        
        This method validates that the response decision doesn't encourage fabrication
        and adds strict accuracy requirements where appropriate.
        """
        print(f"   🛡️ FABRICATION CONTROLS - Validating response decision")
        
        try:
            # Extract current message to analyze what's being asked
            current_message = self._extract_current_message(contextual_cues)
            
            # Detect if this is a factual query that could lead to fabrication
            fabrication_risk = self._assess_fabrication_risk(current_message, contextual_cues)
            
            if fabrication_risk['high_risk']:
                print(f"   ⚠️  HIGH FABRICATION RISK DETECTED:")
                print(f"      - Risk factors: {fabrication_risk['risk_factors']}")
                print(f"      - Original reasoning: {response_decision.reasoning}")
                
                # Add accuracy requirements to the response
                response_decision = self._add_accuracy_requirements(
                    response_decision, 
                    fabrication_risk,
                    contextual_cues
                )
                
                print(f"      - Enhanced reasoning: {response_decision.reasoning}")
            
            # Validate conversation history accuracy for context-based questions
            if self._is_context_based_question(current_message):
                response_decision = self._validate_conversation_accuracy(
                    response_decision, 
                    contextual_cues
                )
            
            return response_decision
            
        except Exception as e:
            print(f"   ❌ ERROR in fabrication controls: {e}")
            # Add safety reasoning as fallback
            response_decision.reasoning += f" | Fabrication control error: {e}"
            return response_decision
    
    def _extract_current_message(self, contextual_cues) -> str:
        """Extract the current message from contextual cues."""
        # Try multiple sources for the current message
        current_message = getattr(contextual_cues, 'current_message', '')
        
        if not current_message:
            # Try to get from addressing context
            addressing_context = getattr(contextual_cues, 'addressing_context', None)
            if addressing_context and hasattr(addressing_context, 'original_message'):
                current_message = addressing_context.original_message
        
        if not current_message:
            # Try to get from conversation dynamics
            dynamics = getattr(contextual_cues, 'conversation_dynamics', None)
            if dynamics and hasattr(dynamics, 'recent_events') and dynamics.recent_events:
                current_message = dynamics.recent_events[-1]
        
        return current_message or "No message content available"
    
    def _assess_fabrication_risk(self, current_message: str, contextual_cues) -> Dict:
        """
        PHASE 3B: Assess the risk of fabrication for the current message.
        
        Identifies patterns that historically led to fabrication issues.
        """
        risk_factors = []
        high_risk = False
        
        message_lower = current_message.lower()
        
        # HIGH RISK: Questions about what someone said/wanted when they said nothing specific
        factual_question_patterns = [
            r'what did \w+ (?:say|want|ask|request|tell)',
            r'what was \w+ (?:saying|wanting|asking|requesting)',
            r'tell me what \w+ (?:said|wanted|asked|requested)',
            r'what about \w+',
            r'hey \w+ what did \w+',
        ]
        
        for pattern in factual_question_patterns:
            if re.search(pattern, message_lower):
                risk_factors.append(f"factual_question_pattern: {pattern}")
                high_risk = True
        
        # HIGH RISK: Technical/scientific questions without clear database context
        technical_patterns = [
            r'stellar nurseries?',
            r'ngc \d+',
            r'constellation\s+\w+',
            r'nebula\s+\w+',
            r'galaxy\s+\w+',
            r'star system\s+\w+',
            r'coordinates? (?:for|of|to)',
        ]
        
        for pattern in technical_patterns:
            if re.search(pattern, message_lower):
                risk_factors.append(f"technical_pattern_without_context: {pattern}")
                high_risk = True
        
        # MEDIUM RISK: Requests for specific information
        specific_info_patterns = [
            r'tell me about',
            r'what is',
            r'who is',
            r'where is',
            r'how does',
            r'explain',
        ]
        
        for pattern in specific_info_patterns:
            if re.search(pattern, message_lower):
                risk_factors.append(f"specific_info_request: {pattern}")
        
        # Check if there's verifiable conversation history for context questions
        if self._is_context_based_question(current_message):
            conversation_history_available = self._has_reliable_conversation_history(contextual_cues)
            if not conversation_history_available:
                risk_factors.append("context_question_without_reliable_history")
                high_risk = True
        
        return {
            'high_risk': high_risk,
            'risk_factors': risk_factors,
            'requires_accuracy_validation': len(risk_factors) > 0
        }
    
    def _add_accuracy_requirements(self, response_decision, fabrication_risk, contextual_cues):
        """
        PHASE 3B: Add strict accuracy requirements to prevent fabrication.
        """
        # Enhance reasoning with accuracy requirements
        original_reasoning = response_decision.reasoning
        
        accuracy_instructions = []
        
        if 'factual_question_pattern' in str(fabrication_risk['risk_factors']):
            accuracy_instructions.append(
                "CRITICAL: This is a factual question about what someone said/wanted. "
                "You must base your response ONLY on verifiable conversation history. "
                "If the person said nothing specific or their request was vague, say so directly. "
                "DO NOT make up details, locations, or technical information."
            )
        
        if 'technical_pattern_without_context' in str(fabrication_risk['risk_factors']):
            accuracy_instructions.append(
                "CRITICAL: This involves technical/scientific information. "
                "Only provide information you have from reliable database sources. "
                "If you don't have specific information, admit you need to look it up "
                "or that you don't have that information available."
            )
        
        if 'context_question_without_reliable_history' in fabrication_risk['risk_factors']:
            accuracy_instructions.append(
                "CRITICAL: This question requires conversation context, but reliable history is not available. "
                "Admit that you weren't following the conversation closely enough to answer accurately."
            )
        
        # Add accuracy instructions to various response fields
        response_decision.reasoning = f"{original_reasoning} | ACCURACY REQUIRED: {' '.join(accuracy_instructions)}"
        
        # Add to knowledge_to_use for prompt inclusion
        if not response_decision.knowledge_to_use:
            response_decision.knowledge_to_use = []
        response_decision.knowledge_to_use.extend(accuracy_instructions)
        
        # Modify tone and approach for accuracy
        response_decision.tone = "honest_and_accurate"
        response_decision.approach = "fact_based"
        
        # Add accuracy themes
        if not response_decision.suggested_themes:
            response_decision.suggested_themes = []
        response_decision.suggested_themes.append("accuracy_required")
        response_decision.suggested_themes.append("no_fabrication")
        
        return response_decision
    
    def _is_context_based_question(self, current_message: str) -> bool:
        """Check if this question requires conversation context to answer."""
        context_patterns = [
            r'what did \w+ (?:say|want|ask|tell|request)',
            r'what was \w+ (?:saying|asking|wanting)',
            r'what about \w+',
            r'hey \w+ what did \w+',
            r'tell me what \w+ (?:said|wanted)',
        ]
        
        message_lower = current_message.lower()
        return any(re.search(pattern, message_lower) for pattern in context_patterns)
    
    def _has_reliable_conversation_history(self, contextual_cues) -> bool:
        """Check if there's reliable conversation history available."""
        # Check if we have conversation memory
        if hasattr(contextual_cues, 'recent_activity') and contextual_cues.recent_activity:
            return len(contextual_cues.recent_activity) >= 2
        
        # Check conversation dynamics for recent events
        if hasattr(contextual_cues, 'conversation_dynamics'):
            dynamics = contextual_cues.conversation_dynamics
            if hasattr(dynamics, 'recent_events') and dynamics.recent_events:
                return len(dynamics.recent_events) >= 2
        
        return False
    
    def _validate_conversation_accuracy(self, response_decision, contextual_cues):
        """
        PHASE 3C: Validate that conversation-based responses will be accurate.
        """
        print(f"   🔍 CONVERSATION ACCURACY VALIDATION")
        
        # Get available conversation history
        recent_activity = getattr(contextual_cues, 'recent_activity', [])
        
        if not recent_activity:
            print(f"      ❌ No conversation history available for context question")
            
            # Modify response to admit lack of context
            response_decision.reasoning += " | No conversation history available for accurate context"
            response_decision.knowledge_to_use.append(
                "IMPORTANT: You don't have reliable conversation history. "
                "Admit that you weren't following the conversation closely enough to answer accurately."
            )
        
        else:
            print(f"      ✅ Conversation history available: {len(recent_activity)} recent activities")
            
            # PHASE 3F: Enhanced conversation history validation
            validated_history = self._validate_conversation_history_accuracy(
                recent_activity, contextual_cues.current_message
            )
            
            if validated_history['is_sufficient']:
                # Add instruction to use only available history
                response_decision.knowledge_to_use.append(
                    "IMPORTANT: Base your response ONLY on the conversation history provided. "
                    "Do not add details that aren't explicitly mentioned."
                )
                response_decision.knowledge_to_use.append(
                    f"VERIFIED CONVERSATION CONTEXT: {validated_history['summary']}"
                )
            else:
                # History insufficient - modify response to admit limitation
                response_decision.reasoning += f" | Insufficient conversation history: {validated_history['limitation']}"
                response_decision.knowledge_to_use.append(
                    "CRITICAL: The conversation history is insufficient to answer this question accurately. "
                    "Admit that you need more context or weren't following closely enough."
                )
        
        return response_decision
    
    def _validate_conversation_history_accuracy(self, recent_activity: List[str], current_message: str) -> Dict:
        """
        PHASE 3F: Validate that conversation history is sufficient for the question being asked.
        """
        message_lower = current_message.lower()
        
        # Extract who the question is about
        question_about_patterns = [
            r'what did (\w+) (?:say|want|ask|request|tell)',
            r'what was (\w+) (?:saying|wanting|asking|requesting)',
            r'tell me what (\w+) (?:said|wanted|asked|requested)',
            r'hey \w+ what did (\w+)',
        ]
        
        target_character = None
        for pattern in question_about_patterns:
            match = re.search(pattern, message_lower)
            if match:
                target_character = match.group(1).title()
                break
        
        if not target_character:
            return {
                'is_sufficient': True,
                'summary': 'General question not requiring specific character context',
                'limitation': None
            }
        
        # Check if target character appears in recent activity
        character_mentioned_in_history = any(
            target_character.lower() in activity.lower() for activity in recent_activity
        )
        
        if not character_mentioned_in_history:
            return {
                'is_sufficient': False,
                'summary': f'No recent activity involving {target_character}',
                'limitation': f'{target_character} not mentioned in available conversation history'
            }
        
        # Extract what the character actually said/did
        character_activities = [
            activity for activity in recent_activity 
            if target_character.lower() in activity.lower()
        ]
        
        # Validate if there's enough context
        if len(character_activities) < 1:
            return {
                'is_sufficient': False,
                'summary': f'Minimal context for {target_character}',
                'limitation': f'Insufficient conversation context about {target_character}'
            }
        
        # Build summary of what character actually did/said
        summary_parts = []
        for activity in character_activities:
            if 'said' in activity.lower() or 'want' in activity.lower() or 'ask' in activity.lower():
                summary_parts.append(activity)
        
        if not summary_parts:
            return {
                'is_sufficient': False,
                'summary': f'{target_character} present but no clear statements/requests recorded',
                'limitation': f'No clear record of what {target_character} said or wanted'
            }
        
        return {
            'is_sufficient': True,
            'summary': f'Recent activity by {target_character}: {"; ".join(summary_parts)}',
            'limitation': None
        }


def create_response_decision_engine() -> ResponseDecisionEngine:
    """
    Factory function to create a ResponseDecisionEngine instance.
    
    This provides a clean interface for other modules to create
    the decision engine without directly instantiating the class.
    """
    return ResponseDecisionEngine() 