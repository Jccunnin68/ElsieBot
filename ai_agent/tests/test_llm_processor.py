#!/usr/bin/env python3
"""
Test LLM Query Processor Implementation
======================================

Tests the LLM Query Processor with various scenarios including:
- Large data processing
- Rate limiting simulation
- Fallback response generation
- Roleplay vs non-roleplay contexts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_agent.handlers.ai_wisdom.llm_query_processor import (
    get_llm_processor, 
    should_process_data, 
    ProcessingResult
)
from ai_agent.handlers.handlers_utils import is_fallback_response

def test_processor_initialization():
    """Test that the processor initializes correctly"""
    print("🧪 TEST 1: Processor Initialization")
    print("=" * 50)
    
    try:
        processor = get_llm_processor()
        print("✅ Processor initialized successfully")
        
        # Test metrics
        stats = processor.get_processing_stats()
        print(f"📊 Initial stats: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ Processor initialization failed: {e}")
        return False

def test_small_data_passthrough():
    """Test that small data passes through without processing"""
    print("\n🧪 TEST 2: Small Data Passthrough")
    print("=" * 50)
    
    processor = get_llm_processor()
    small_data = "This is a small piece of test data that should not be processed."
    
    result = processor.process_query_results(
        query_type="general",
        raw_data=small_data,
        user_query="test query",
        is_roleplay=False
    )
    
    print(f"📊 Result status: {result.processing_status}")
    print(f"📊 Was processed: {result.was_processed}")
    print(f"📊 Is fallback: {result.is_fallback_response}")
    print(f"📊 Content length: {len(result.content)}")
    
    if result.processing_status == "not_needed" and not result.was_processed:
        print("✅ Small data correctly passed through without processing")
        return True
    else:
        print("❌ Small data was incorrectly processed")
        return False

def test_large_data_detection():
    """Test that large data is detected for processing"""
    print("\n🧪 TEST 3: Large Data Detection")
    print("=" * 50)
    
    # Create large test data
    large_data = "This is test data. " * 300  # Should exceed 5000 char threshold
    
    should_process = should_process_data(large_data)
    print(f"📊 Data size: {len(large_data)} characters")
    print(f"📊 Should process: {should_process}")
    
    if should_process:
        print("✅ Large data correctly detected for processing")
        return True
    else:
        print("❌ Large data was not detected for processing")
        return False

def test_fallback_response_detection():
    """Test fallback response detection"""
    print("\n🧪 TEST 4: Fallback Response Detection")
    print("=" * 50)
    
    # Test roleplay fallback indicators
    roleplay_fallback = "I don't recall that information right now. My memory banks seem a bit foggy."
    system_fallback = "Deep data searches are currently rate limited. Please try again in 5 minutes."
    normal_response = "Here is the information you requested about the USS Enterprise."
    
    print(f"📊 Roleplay fallback detected: {is_fallback_response(roleplay_fallback)}")
    print(f"📊 System fallback detected: {is_fallback_response(system_fallback)}")
    print(f"📊 Normal response detected: {is_fallback_response(normal_response)}")
    
    if (is_fallback_response(roleplay_fallback) and 
        is_fallback_response(system_fallback) and 
        not is_fallback_response(normal_response)):
        print("✅ Fallback response detection working correctly")
        return True
    else:
        print("❌ Fallback response detection failed")
        return False

def test_rate_limiting_simulation():
    """Test rate limiting behavior"""
    print("\n🧪 TEST 5: Rate Limiting Simulation")
    print("=" * 50)
    
    processor = get_llm_processor()
    
    # Simulate rate limit by setting a very low limit
    processor.rate_limiter.daily_limit = 0  # Force rate limiting
    
    large_data = "Test data for rate limiting. " * 200
    
    result = processor.process_query_results(
        query_type="logs",
        raw_data=large_data,
        user_query="test rate limiting",
        is_roleplay=True
    )
    
    print(f"📊 Result status: {result.processing_status}")
    print(f"📊 Is fallback: {result.is_fallback_response}")
    print(f"📊 Retry after: {result.retry_after_minutes} minutes")
    print(f"📊 Fallback reason: {result.fallback_reason}")
    print(f"📊 Content preview: {result.content[:100]}...")
    
    if result.processing_status == "rate_limited" and result.is_fallback_response:
        print("✅ Rate limiting correctly triggered fallback response")
        return True
    else:
        print("❌ Rate limiting did not work as expected")
        return False

def test_roleplay_vs_nonroleplay_fallbacks():
    """Test different fallback responses for roleplay vs non-roleplay"""
    print("\n🧪 TEST 6: Roleplay vs Non-Roleplay Fallbacks")
    print("=" * 50)
    
    processor = get_llm_processor()
    
    # Force rate limiting for both tests
    processor.rate_limiter.daily_limit = 0
    
    # Test roleplay fallback (ensure data is over 5000 chars)
    roleplay_result = processor.process_query_results(
        query_type="character",
        raw_data="Large character data " * 250,  # ~5250 chars, over threshold
        user_query="tell me about Captain Kirk",
        is_roleplay=True
    )
    
    # Test non-roleplay fallback (ensure data is over 5000 chars)
    nonroleplay_result = processor.process_query_results(
        query_type="character", 
        raw_data="Large character data " * 250,  # ~5250 chars, over threshold
        user_query="tell me about Captain Kirk",
        is_roleplay=False
    )
    
    print("📊 ROLEPLAY FALLBACK:")
    print(f"   Content: {roleplay_result.content}")
    print("\n📊 NON-ROLEPLAY FALLBACK:")
    print(f"   Content: {nonroleplay_result.content}")
    
    # Check that they're different and appropriate
    roleplay_phrases = ["not recalling", "coming to mind", "having a quiet moment", 
                       "memory banks", "don't recall", "drawing a blank", "databases are being"]
    nonroleplay_phrases = ["rate limited", "try again", "minutes"]
    
    roleplay_has_character_language = any(phrase in roleplay_result.content.lower() 
                                        for phrase in roleplay_phrases)
    nonroleplay_has_system_language = any(phrase in nonroleplay_result.content.lower()
                                        for phrase in nonroleplay_phrases)
    

    
    if roleplay_has_character_language and nonroleplay_has_system_language:
        print("✅ Roleplay and non-roleplay fallbacks are appropriately different")
        return True
    else:
        print("❌ Fallback responses are not appropriately contextualized")
        return False

def test_processing_metrics():
    """Test that processing metrics are tracked correctly"""
    print("\n🧪 TEST 7: Processing Metrics")
    print("=" * 50)
    
    processor = get_llm_processor()
    
    # Reset metrics for clean test
    processor.metrics._reset_daily_counters()
    
    # Create a few test results
    test_result_1 = ProcessingResult(
        content="test content",
        was_processed=True,
        processing_status="success",
        is_fallback_response=False,
        original_data_size=1000,
        processed_data_size=500
    )
    
    test_result_2 = ProcessingResult(
        content="fallback content",
        was_processed=False,
        processing_status="rate_limited",
        is_fallback_response=True,
        original_data_size=1000,
        processed_data_size=100
    )
    
    # Log the results
    processor.metrics.log_processing_attempt(test_result_1)
    processor.metrics.log_processing_attempt(test_result_2)
    
    # Check metrics
    stats = processor.get_processing_stats()
    print(f"📊 Final stats: {stats}")
    
    expected_stats = {
        "total_requests": 2,
        "successful_processing": 1,
        "rate_limited_requests": 1,
        "fallback_responses": 1,
        "token_savings": 500
    }
    
    if all(stats[key] == expected_stats[key] for key in expected_stats):
        print("✅ Processing metrics tracked correctly")
        return True
    else:
        print("❌ Processing metrics not tracked correctly")
        print(f"   Expected: {expected_stats}")
        print(f"   Actual: {stats}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("🚀 STARTING LLM QUERY PROCESSOR TESTS")
    print("=" * 60)
    
    tests = [
        test_processor_initialization,
        test_small_data_passthrough,
        test_large_data_detection,
        test_fallback_response_detection,
        test_rate_limiting_simulation,
        test_roleplay_vs_nonroleplay_fallbacks,
        test_processing_metrics
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("🏁 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\n📊 OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! LLM Query Processor implementation is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 