#!/usr/bin/env python3
"""
Emotional Support Detection Test
===============================

This test script specifically validates the enhanced emotional support detection
system and its ability to correctly resolve conflicts with group addressing detection.

This addresses the core issue where "I'm having trouble living up to everyone's expectations"
was being misclassified as group addressing instead of emotional support.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_emotional_support_enhancement():
    """Test the enhanced emotional support detection system"""
    
    print("=" * 80)
    print("🧪 EMOTIONAL SUPPORT DETECTION TEST")
    print("=" * 80)
    print()
    
    # Import test modules
    try:
        from priority_resolution import resolve_emotional_vs_group_conflict
        from context_sensitivity import distinguish_group_vs_contextual
        from conversation_emotions import ConversationEmotionalIntelligence
        from emotional_analysis import detect_emotional_support_opportunity
        
        print("✅ All emotional intelligence modules imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import emotional intelligence modules: {e}")
        return False
    
    # Test scenarios focusing on the specific issue
    test_scenarios = [
        {
            "name": "THE PROBLEMATIC CASE: Everyone's Expectations",
            "message": "I'm having trouble living up to everyone's expectations.",
            "context": {
                "vulnerability_level": "high",
                "intimacy_level": "personal",
                "relationship": "close_friend",
                "current_speaker": "Tavi"
            },
            "expected_result": "emotional_support",
            "description": "This was the failing test case - should detect emotional support, not group addressing"
        },
        {
            "name": "Actual Group Addressing",
            "message": "Good morning everyone! How is everyone doing today?",
            "context": {
                "vulnerability_level": "low",
                "intimacy_level": "casual",
                "relationship": "colleague",
                "current_speaker": "Maeve"
            },
            "expected_result": "group_addressing",
            "description": "True group addressing - should be detected as such"
        },
        {
            "name": "Emotional with Everyone Context",
            "message": "I feel like everyone expects me to be perfect, but I'm struggling.",
            "context": {
                "vulnerability_level": "high",
                "intimacy_level": "personal",
                "relationship": "close_friend",
                "current_speaker": "Tavi"
            },
            "expected_result": "emotional_support",
            "description": "Emotional content mentioning 'everyone' - should prioritize emotional support"
        },
        {
            "name": "Group Question",
            "message": "Does everyone understand the mission parameters?",
            "context": {
                "vulnerability_level": "low",
                "intimacy_level": "professional",
                "relationship": "colleague",
                "current_speaker": "Commander"
            },
            "expected_result": "group_addressing",
            "description": "Direct question to group - should be group addressing"
        },
        {
            "name": "Contextual Everyone Mention",
            "message": "Everyone on the ship knows about stellar cartography except me.",
            "context": {
                "vulnerability_level": "moderate",
                "intimacy_level": "casual",
                "relationship": "colleague",
                "current_speaker": "NewCrew"
            },
            "expected_result": "emotional_support",
            "description": "Contextual mention with vulnerability - should detect emotional support"
        }
    ]
    
    print(f"🧪 Running {len(test_scenarios)} test scenarios...\n")
    
    # Initialize emotional intelligence
    emotional_intelligence = ConversationEmotionalIntelligence()
    
    # Track results
    passed_tests = 0
    total_tests = len(test_scenarios)
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"{'='*60}")
        print(f"TEST {i}: {scenario['name']}")
        print(f"{'='*60}")
        print(f"📝 Message: \"{scenario['message']}\"")
        print(f"🎯 Expected: {scenario['expected_result']}")
        print(f"💭 Description: {scenario['description']}")
        print()
        
        # Test individual components
        print("🔍 COMPONENT ANALYSIS:")
        
        # 1. Context sensitivity analysis
        addressing_type, addressing_confidence = distinguish_group_vs_contextual(scenario['message'])
        print(f"   Context Analysis: {addressing_type} (confidence: {addressing_confidence:.2f})")
        
        # 2. Emotional support detection
        needs_support, support_confidence = detect_emotional_support_opportunity(
            scenario['message'], scenario['context']
        )
        print(f"   Emotional Support: {needs_support} (confidence: {support_confidence:.2f})")
        
        # 3. Enhanced emotional support detection
        enhanced_needs_support, enhanced_confidence, reasoning = emotional_intelligence.detect_emotional_support_opportunity_enhanced(
            scenario['message'], []
        )
        print(f"   Enhanced Support: {enhanced_needs_support} (confidence: {enhanced_confidence:.2f})")
        print(f"   Enhancement reasoning: {reasoning}")
        
        # 4. Priority conflict resolution
        print(f"\n⚖️  PRIORITY CONFLICT RESOLUTION:")
        
        # Simulate both detections
        group_confidence = 0.8 if addressing_type == "direct_group" else 0.3
        emotional_confidence = enhanced_confidence
        
        context_with_message = {**scenario['context'], 'message': scenario['message']}
        
        decision_type, final_confidence, resolution_reasoning = resolve_emotional_vs_group_conflict(
            emotional_confidence=emotional_confidence,
            group_confidence=group_confidence,
            message=scenario['message'],
            context=context_with_message
        )
        
        # Check result
        test_passed = decision_type == scenario['expected_result']
        if test_passed:
            passed_tests += 1
            print(f"   ✅ RESULT: {decision_type} (confidence: {final_confidence:.2f})")
            print(f"   ✅ TEST PASSED!")
        else:
            print(f"   ❌ RESULT: {decision_type} (confidence: {final_confidence:.2f})")
            print(f"   ❌ TEST FAILED! Expected: {scenario['expected_result']}")
        
        print(f"   💭 Resolution reasoning: {resolution_reasoning}")
        print()
    
    # Summary
    print(f"{'='*80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Passed: {passed_tests}/{total_tests}")
    print(f"❌ Failed: {total_tests - passed_tests}/{total_tests}")
    print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"The emotional support detection enhancement successfully resolves")
        print(f"the conflict between group addressing and emotional support detection!")
        return True
    else:
        print(f"\n⚠️  Some tests failed. The system needs further refinement.")
        return False


def test_context_sensitivity_patterns():
    """Test specific context sensitivity patterns"""
    
    print(f"\n{'='*60}")
    print("🎯 CONTEXT SENSITIVITY PATTERN TESTS")
    print(f"{'='*60}")
    
    from context_sensitivity import distinguish_group_vs_contextual
    
    test_patterns = [
        ("Good morning everyone!", "direct_group"),
        ("Hello everyone in Ten Forward!", "direct_group"),
        ("You all need to hear this", "direct_group"),
        ("How is everyone doing?", "direct_group"),
        ("I'm struggling with everyone's expectations", "contextual_mention"),
        ("Everyone around here knows better", "contextual_mention"),
        ("What everyone thinks doesn't matter", "contextual_mention"),
        ("Everyone's opinion varies on this", "contextual_mention"),
        ("Everyone was talking about it", "contextual_mention"),
        ("I can't handle what everyone expects", "contextual_mention"),
    ]
    
    print("Testing context sensitivity patterns:")
    print()
    
    for message, expected in test_patterns:
        result, confidence = distinguish_group_vs_contextual(message)
        status = "✅" if result == expected else "❌"
        print(f"{status} \"{message}\"")
        print(f"   Expected: {expected}, Got: {result} (confidence: {confidence:.2f})")
        if result != expected:
            print(f"   ⚠️  Pattern recognition needs improvement")
        print()


def demonstrate_enhancement_benefits():
    """Demonstrate the benefits of the enhanced system"""
    
    print(f"\n{'='*60}")
    print("💡 ENHANCEMENT BENEFITS DEMONSTRATION")
    print(f"{'='*60}")
    
    print("BEFORE Enhancement (Original System):")
    print("• Group addressing had Priority 2 (higher than emotional support)")
    print("• \"everyone's expectations\" triggered group addressing detection")
    print("• Emotional support had Priority 6 (lower priority)")
    print("• No context sensitivity - all 'everyone' mentions treated as group addressing")
    print("• No conflict resolution between competing detections")
    print()
    
    print("AFTER Enhancement (New System):")
    print("• Context-sensitive pattern recognition distinguishes addressing types")
    print("• \"everyone's expectations\" correctly identified as contextual mention")
    print("• Emotional support elevated to Priority 2 when detected")
    print("• Sophisticated conflict resolution with confidence scoring")
    print("• Multi-factor analysis considers vulnerability, intimacy, relationships")
    print("• Enhanced emotional intelligence across conversation turns")
    print()
    
    print("KEY FIXES:")
    print("✅ Special case handling for \"everyone's expectations\" pattern")
    print("✅ Priority reordering - emotional support before group addressing")
    print("✅ Context-aware conflict resolution with detailed reasoning")
    print("✅ Enhanced confidence scoring with contextual bonuses")
    print("✅ Vulnerability and intimacy level considerations")
    print("✅ Relationship context integration")
    print()


if __name__ == "__main__":
    success = test_emotional_support_enhancement()
    test_context_sensitivity_patterns()
    demonstrate_enhancement_benefits()
    
    if success:
        print(f"\n🎉 EMOTIONAL SUPPORT ENHANCEMENT VALIDATION COMPLETE!")
        print(f"The system now correctly handles the problematic 'everyone's expectations' case.")
        sys.exit(0)
    else:
        print(f"\n❌ VALIDATION FAILED - Further work needed.")
        sys.exit(1) 