#!/usr/bin/env python3
"""
Simple Emotional Support Test
============================

A direct test of the core functionality to validate the emotional support
vs group addressing conflict resolution.
"""

print("=" * 60)
print("🧪 SIMPLE EMOTIONAL SUPPORT TEST")
print("=" * 60)

# Test the core functionality directly
def test_context_sensitivity():
    """Test context sensitivity patterns directly"""
    
    print("Testing context sensitivity...")
    
    # Import and test distinguish_group_vs_contextual
    try:
        from context_sensitivity import distinguish_group_vs_contextual
        
        # Test the problematic case
        message = "I'm having trouble living up to everyone's expectations."
        result, confidence = distinguish_group_vs_contextual(message)
        
        print(f"Message: \"{message}\"")
        print(f"Result: {result} (confidence: {confidence:.2f})")
        
        if result == "contextual_mention":
            print("✅ PASS: Correctly identified as contextual mention")
            return True
        else:
            print("❌ FAIL: Should be contextual mention, not group addressing")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_priority_resolution():
    """Test priority resolution directly"""
    
    print("\nTesting priority resolution...")
    
    try:
        from priority_resolution import resolve_emotional_vs_group_conflict
        
        # Test the core conflict resolution
        message = "I'm having trouble living up to everyone's expectations."
        context = {
            'message': message,
            'vulnerability_level': 'high',
            'intimacy_level': 'personal',
            'relationship': 'close_friend',
            'current_speaker': 'Tavi'
        }
        
        result_type, confidence, reasoning = resolve_emotional_vs_group_conflict(
            emotional_confidence=0.75,
            group_confidence=0.85,
            message=message,
            context=context
        )
        
        print(f"Message: \"{message}\"")
        print(f"Result: {result_type} (confidence: {confidence:.2f})")
        print(f"Reasoning: {reasoning}")
        
        if result_type == "emotional_support":
            print("✅ PASS: Correctly prioritized emotional support")
            return True
        else:
            print("❌ FAIL: Should prioritize emotional support over group addressing")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_enhanced_emotional_detection():
    """Test enhanced emotional detection"""
    
    print("\nTesting enhanced emotional detection...")
    
    try:
        from conversation_emotions import ConversationEmotionalIntelligence
        
        ei = ConversationEmotionalIntelligence()
        
        message = "I'm having trouble living up to everyone's expectations."
        conversation_history = []
        
        needs_support, confidence, reasoning = ei.detect_emotional_support_opportunity_enhanced(
            message, conversation_history
        )
        
        print(f"Message: \"{message}\"")
        print(f"Needs support: {needs_support} (confidence: {confidence:.2f})")
        print(f"Reasoning: {reasoning}")
        
        if needs_support and confidence > 0.6:
            print("✅ PASS: Enhanced detection correctly identified emotional support need")
            return True
        else:
            print("❌ FAIL: Should detect emotional support need with high confidence")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


# Run tests
if __name__ == "__main__":
    test1 = test_context_sensitivity()
    test2 = test_priority_resolution()
    test3 = test_enhanced_emotional_detection()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    tests_passed = sum([test1, test2, test3])
    total_tests = 3
    
    print(f"✅ Passed: {tests_passed}/{total_tests}")
    print(f"❌ Failed: {total_tests - tests_passed}/{total_tests}")
    print(f"📈 Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("The emotional support enhancement is working correctly!")
    else:
        print(f"\n⚠️  {total_tests - tests_passed} test(s) failed.")
        print("The system needs debugging.")
        
    print("\n🔧 IMPLEMENTATION STATUS:")
    print("✅ Context sensitivity module created")
    print("✅ Priority resolution module created")
    print("✅ Conversation emotions module created")
    print("✅ Enhanced conversation_memory.py integration")
    print("✅ Test framework created")
    print("\n🎯 The core issue (everyone's expectations misclassification) should now be resolved!") 