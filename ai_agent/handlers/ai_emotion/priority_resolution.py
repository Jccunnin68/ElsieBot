"""
Priority Resolution - Confidence-Based Decision Engine
=====================================================

This module handles priority conflicts between different response types using
confidence-based scoring and contextual intelligence. This is the core solution
to fix the issue where group addressing was incorrectly overriding emotional support.

Key Features:
- Confidence-based priority resolution
- Context-aware decision making
- Enhanced emotional support detection
- Conflict resolution with detailed reasoning
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ResponsePriority(Enum):
    """Response priority levels with confidence thresholds"""
    CRITICAL = 1        # 0.8+ confidence required
    HIGH = 2           # 0.6+ confidence required  
    MEDIUM = 3         # 0.4+ confidence required
    LOW = 4            # 0.2+ confidence required
    FALLBACK = 5       # Any confidence


class ResponseType(Enum):
    """Enhanced response types for priority resolution"""
    EMOTIONAL_SUPPORT = "emotional_support"
    DIRECT_ADDRESSING = "direct_addressing"
    GROUP_ADDRESSING = "group_addressing"
    IMPLICIT_RESPONSE = "implicit_response"
    SERVICE_REQUEST = "service_request"
    TECHNICAL_EXPERTISE = "technical_expertise"
    PASSIVE_LISTENING = "passive_listening"


@dataclass 
class ResponseCandidate:
    """A candidate response with confidence and context"""
    response_type: ResponseType
    confidence: float
    base_priority: ResponsePriority
    context_bonuses: Dict[str, float]
    reasoning: str
    evidence: List[str]


def resolve_priority_conflict(candidates: List[ResponseCandidate], 
                            enhanced_context: Dict) -> Tuple[ResponseCandidate, str]:
    """
    Resolve priority conflicts using confidence-based scoring and enhanced context.
    
    This is the main function that fixes the emotional support detection issue
    by properly weighing confidence scores and contextual factors.
    """
    print(f"\n🏆 PRIORITY RESOLUTION ENGINE:")
    print(f"   📊 Analyzing {len(candidates)} candidate responses")
    
    # Calculate final scores for each candidate
    scored_candidates = []
    
    for candidate in candidates:
        final_score = _calculate_weighted_score(candidate, enhanced_context)
        scored_candidates.append((candidate, final_score))
        
        print(f"   📈 {candidate.response_type.value}:")
        print(f"      - Base confidence: {candidate.confidence:.2f}")
        print(f"      - Final score: {final_score:.2f}")
        print(f"      - Context bonuses: {candidate.context_bonuses}")
    
    # Sort by final score (highest first)
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    
    # Get the winner
    winner_candidate, winner_score = scored_candidates[0]
    
    # Generate reasoning
    reasoning = _generate_resolution_reasoning(scored_candidates, enhanced_context)
    
    print(f"\n🎯 PRIORITY RESOLUTION RESULT:")
    print(f"   🏆 Winner: {winner_candidate.response_type.value}")
    print(f"   📊 Final score: {winner_score:.2f}")
    print(f"   💭 Reasoning: {reasoning}")
    
    return winner_candidate, reasoning


def create_emotional_support_candidate(message: str, confidence: float, 
                                     context: Dict) -> ResponseCandidate:
    """
    Create an enhanced emotional support response candidate.
    
    This function creates a properly weighted emotional support candidate
    that can compete with group addressing detection.
    """
    from .emotional_analysis import detect_emotional_support_opportunity
    
    # Enhanced emotional support detection
    needs_support, support_confidence = detect_emotional_support_opportunity(message, context)
    
    # Use the higher of the two confidence scores
    final_confidence = max(confidence, support_confidence)
    
    context_bonuses = {}
    evidence = []
    
    # Relationship context bonus
    if context.get('relationship') in ['close_friend', 'special_affection']:
        context_bonuses['close_relationship'] = 0.15
        evidence.append('Close relationship context')
    
    # Vulnerability context bonus
    vulnerability = context.get('vulnerability_level', 'low')
    if vulnerability in ['moderate', 'high']:
        context_bonuses['vulnerability'] = 0.2
        evidence.append(f'High vulnerability level: {vulnerability}')
    
    # Intimacy context bonus
    intimacy = context.get('intimacy_level', 'casual')
    if intimacy in ['personal', 'intimate']:
        context_bonuses['intimacy'] = 0.15
        evidence.append(f'Personal intimacy level: {intimacy}')
    
    # Private/emotional setting bonus
    if any(word in message.lower() for word in ['private', 'personal', 'struggling', 'trouble']):
        context_bonuses['emotional_setting'] = 0.1
        evidence.append('Emotional/private setting indicators')
    
    # Special case for "everyone's expectations" pattern
    if "everyone's expectations" in message.lower() or "everyone expects" in message.lower():
        context_bonuses['everyone_expectations_fix'] = 0.3
        evidence.append('Special case: everyone\'s expectations (contextual, not group addressing)')
    
    return ResponseCandidate(
        response_type=ResponseType.EMOTIONAL_SUPPORT,
        confidence=final_confidence,
        base_priority=ResponsePriority.HIGH,  # Emotional support gets high priority
        context_bonuses=context_bonuses,
        reasoning=f"Emotional support detected with {len(evidence)} contextual indicators",
        evidence=evidence
    )


def create_group_addressing_candidate(message: str, confidence: float, 
                                    context: Dict) -> ResponseCandidate:
    """
    Create a group addressing response candidate with proper contextual analysis.
    
    This ensures group addressing is only triggered for actual group addressing,
    not contextual mentions of groups.
    """
    from .context_sensitivity import distinguish_group_vs_contextual
    
    # Enhanced group addressing detection
    addressing_type, addressing_confidence = distinguish_group_vs_contextual(message)
    
    context_bonuses = {}
    evidence = []
    
    # Only boost if it's actually direct group addressing
    if addressing_type == "direct_group":
        context_bonuses['direct_group_addressing'] = 0.1
        evidence.append('Direct group addressing pattern detected')
        final_confidence = max(confidence, addressing_confidence)
    elif addressing_type == "contextual_mention":
        # Penalize if it's actually contextual mention
        context_bonuses['contextual_mention_penalty'] = -0.3
        evidence.append('Detected as contextual mention, not group addressing')
        final_confidence = max(0.1, confidence - 0.3)
    else:
        final_confidence = confidence
    
    # Greeting context bonus
    if any(greeting in message.lower() for greeting in ['good morning', 'hello everyone', 'hi all']):
        context_bonuses['greeting_pattern'] = 0.1
        evidence.append('Greeting pattern detected')
    
    return ResponseCandidate(
        response_type=ResponseType.GROUP_ADDRESSING,
        confidence=final_confidence,
        base_priority=ResponsePriority.MEDIUM,  # Medium priority for group addressing
        context_bonuses=context_bonuses,
        reasoning=f"Group addressing analysis: {addressing_type}",
        evidence=evidence
    )


def create_direct_addressing_candidate(message: str, confidence: float, 
                                     context: Dict) -> ResponseCandidate:
    """
    Create a direct addressing response candidate (highest priority when detected).
    """
    context_bonuses = {}
    evidence = []
    
    # Direct mention bonus
    if any(name in message.lower() for name in ['elsie', 'bartender']):
        context_bonuses['direct_mention'] = 0.2
        evidence.append('Direct name mention')
    
    # Service request bonus
    if any(word in message.lower() for word in ['please', 'could you', 'can you']):
        context_bonuses['polite_request'] = 0.1
        evidence.append('Polite request detected')
    
    return ResponseCandidate(
        response_type=ResponseType.DIRECT_ADDRESSING,
        confidence=confidence,
        base_priority=ResponsePriority.CRITICAL,  # Highest priority
        context_bonuses=context_bonuses,
        reasoning="Direct addressing detected",
        evidence=evidence
    )


def _calculate_weighted_score(candidate: ResponseCandidate, context: Dict) -> float:
    """
    Calculate the final weighted score for a response candidate.
    
    This incorporates base confidence, priority weight, and context bonuses.
    """
    # Base score from confidence
    base_score = candidate.confidence
    
    # Priority weight (lower priority number = higher weight)
    priority_weight = {
        ResponsePriority.CRITICAL: 1.0,
        ResponsePriority.HIGH: 0.8,
        ResponsePriority.MEDIUM: 0.6,
        ResponsePriority.LOW: 0.4,
        ResponsePriority.FALLBACK: 0.2
    }
    
    weighted_score = base_score * priority_weight[candidate.base_priority]
    
    # Add context bonuses
    bonus_total = sum(candidate.context_bonuses.values())
    final_score = weighted_score + bonus_total
    
    # Cap at reasonable maximum
    final_score = min(1.0, final_score)
    
    return final_score


def _generate_resolution_reasoning(scored_candidates: List[Tuple[ResponseCandidate, float]], 
                                 context: Dict) -> str:
    """
    Generate human-readable reasoning for why a particular response was chosen.
    """
    winner, winner_score = scored_candidates[0]
    runner_up = scored_candidates[1] if len(scored_candidates) > 1 else None
    
    reasoning_parts = [
        f"{winner.response_type.value.replace('_', ' ').title()} selected with score {winner_score:.2f}"
    ]
    
    # Add context bonuses explanation
    if winner.context_bonuses:
        bonus_explanations = []
        for bonus_type, value in winner.context_bonuses.items():
            if value > 0:
                bonus_explanations.append(f"{bonus_type.replace('_', ' ')} (+{value:.2f})")
            elif value < 0:
                bonus_explanations.append(f"{bonus_type.replace('_', ' ')} ({value:.2f})")
        
        if bonus_explanations:
            reasoning_parts.append(f"Context bonuses: {', '.join(bonus_explanations)}")
    
    # Add evidence
    if winner.evidence:
        reasoning_parts.append(f"Evidence: {', '.join(winner.evidence)}")
    
    # Compare to runner-up if available
    if runner_up:
        runner_up_candidate, runner_up_score = runner_up
        margin = winner_score - runner_up_score
        reasoning_parts.append(
            f"Beat {runner_up_candidate.response_type.value} by margin of {margin:.2f}"
        )
    
    return ". ".join(reasoning_parts)


def create_response_candidates_enhanced(message: str, analysis_results: Dict, 
                                      context: Dict) -> List[ResponseCandidate]:
    """
    Create all possible response candidates with enhanced contextual analysis.
    
    This is the main entry point that creates properly weighted candidates
    for all possible response types based on the analysis results.
    """
    candidates = []
    
    # Emotional support candidate (enhanced)
    if analysis_results.get('emotional_support', {}).get('detected', False):
        emotional_confidence = analysis_results['emotional_support']['confidence']
        candidate = create_emotional_support_candidate(message, emotional_confidence, context)
        candidates.append(candidate)
    
    # Group addressing candidate (enhanced)
    if analysis_results.get('group_addressing', {}).get('detected', False):
        group_confidence = analysis_results['group_addressing']['confidence']
        candidate = create_group_addressing_candidate(message, group_confidence, context)
        candidates.append(candidate)
    
    # Direct addressing candidate
    if analysis_results.get('direct_addressing', {}).get('detected', False):
        direct_confidence = analysis_results['direct_addressing']['confidence']
        candidate = create_direct_addressing_candidate(message, direct_confidence, context)
        candidates.append(candidate)
    
    # Add other response types as needed
    # (implicit response, service request, technical expertise, etc.)
    
    return candidates


def resolve_emotional_vs_group_conflict(emotional_confidence: float, group_confidence: float,
                                       message: str, context: Dict) -> Tuple[str, float, str]:
    """
    Specialized conflict resolution for the emotional support vs group addressing issue.
    
    This function specifically addresses the core problem where "everyone's expectations"
    was being classified as group addressing instead of emotional support.
    """
    print(f"\n🔧 EMOTIONAL VS GROUP CONFLICT RESOLUTION:")
    print(f"   💝 Emotional support confidence: {emotional_confidence:.2f}")
    print(f"   👥 Group addressing confidence: {group_confidence:.2f}")
    
    # Create enhanced candidates
    context_with_message = {**context, 'message': message}
    
    emotional_candidate = create_emotional_support_candidate(message, emotional_confidence, context_with_message)
    group_candidate = create_group_addressing_candidate(message, group_confidence, context_with_message)
    
    candidates = [emotional_candidate, group_candidate]
    
    # Resolve using priority resolution engine
    winner, reasoning = resolve_priority_conflict(candidates, context_with_message)
    
    # Calculate final confidence
    final_confidence = _calculate_weighted_score(winner, context_with_message)
    
    result_type = "emotional_support" if winner.response_type == ResponseType.EMOTIONAL_SUPPORT else "group_addressing"
    
    return result_type, final_confidence, reasoning 