#!/usr/bin/env python3
"""
Phase 1: Enhanced Pathway Validation Test
=========================================

This test validates that the enhanced roleplay pathway works correctly
for all roleplay scenarios before we remove the deprecated functions.

This test is part of the Roleplay Deprecation Refactor Plan Phase 1.
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from handlers.ai_logic.response_router import route_message_to_handler
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_attention.contextual_cues import ResponseType

def run_enhanced_pathway_validation():
    """
    Run comprehensive validation of the enhanced roleplay pathway.
    This ensures all roleplay scenarios work through the enhanced system.
    """
    print("=" * 80)
    print("🧪 PHASE 1: ENHANCED PATHWAY VALIDATION")
    print("=" * 80)
    print()
    
    # Initialize test state
    rp_state = get_roleplay_state()
    test_results = {
        'passed': 0,
        'failed': 0,
        'scenarios': []
    }
    
    # Test scenarios covering all roleplay use cases
    scenarios = [
        {
            "name": "DGM Scene Setting",
            "setup": lambda: setup_fresh_state(rp_state),
            "message": '[DGM] *The USS Stardancer approaches Earth orbit as the evening crew reports for duty.*',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "dgm_scene_setting",
            "expected_ai_generation": False
        },
        {
            "name": "Direct Character Greeting to Elsie",
            "setup": lambda: setup_dgm_session(rp_state),
            "message": '[Tavi] *walks into Ten Forward* "Good evening, Elsie! How are you tonight?"',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "roleplay_active",
            "expected_ai_generation": True
        },
        {
            "name": "Group Greeting",
            "setup": lambda: setup_dgm_session(rp_state, ["Maeve", "Zarina"]),
            "message": '[Maeve] *enters Ten Forward with a smile* "Good evening everyone!"',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "roleplay_group_response",
            "expected_ai_generation": True
        },
        {
            "name": "Drink Service Request",
            "setup": lambda: setup_dgm_session(rp_state, ["Marcus"]),
            "message": '[Marcus] *approaches the bar* *signals for a drink*',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "roleplay_subtle_service",
            "expected_ai_generation": True
        },
        {
            "name": "Emotional Support Scenario",
            "setup": lambda: setup_dgm_session(rp_state, ["Tavi"]),
            "message": '[Tavi] *sits heavily at the bar* "I\'m having trouble living up to everyone\'s expectations."',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "roleplay_supportive",
            "expected_ai_generation": True
        },
        {
            "name": "Technical Expertise Query",
            "setup": lambda: setup_dgm_session(rp_state, ["Shay"]),
            "message": '[Shay] *studying star charts* "These stellar navigation calculations seem off for this sector."',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "roleplay_technical",
            "expected_ai_generation": True
        },
        {
            "name": "Character-to-Character Interaction",
            "setup": lambda: setup_dgm_session(rp_state, ["Maeve", "Zarina"]),
            "message": '[Maeve] "Zarina, what do you think about the new mission parameters?"',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "roleplay_listening",
            "expected_ai_generation": False
        },
        {
            "name": "Cross-Channel Busy Response",
            "setup": lambda: setup_dgm_session(rp_state),
            "message": 'Hello Elsie!',
            "channel": {"type": "DM", "is_dm": True, "channel_name": "dm"},
            "expected_approach": "cross_channel_busy",
            "expected_ai_generation": False
        },
        {
            "name": "DGM Scene End",
            "setup": lambda: setup_dgm_session(rp_state),
            "message": '[DGM] END',
            "channel": {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
            "expected_approach": "dgm_scene_end",
            "expected_ai_generation": False
        },
        {
            "name": "Non-Roleplay Query",
            "setup": lambda: setup_fresh_state(rp_state),
            "message": 'Tell me about USS Stardancer',
            "channel": {"type": "DM", "is_dm": True, "channel_name": "dm"},
            "expected_approach": "stardancer_info",
            "expected_ai_generation": True
        }
    ]
    
    # Run each test scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'=' * 60}")
        print(f"🎭 SCENARIO {i}: {scenario['name']}")
        print(f"{'=' * 60}")
        
        # Setup scenario
        scenario['setup']()
        
        # Test the enhanced pathway
        print(f"📝 Message: {scenario['message']}")
        print(f"📡 Channel: {scenario['channel']}")
        
        try:
            # Use the enhanced pathway
            response_decision = route_message_to_handler(
                scenario['message'], 
                [], 
                scenario['channel']
            )
            
            # Analyze results
            actual_approach = response_decision.strategy.get('approach', 'unknown')
            actual_ai_generation = response_decision.needs_ai_generation
            
            print(f"\n📊 RESULTS:")
            print(f"   Expected Approach: {scenario['expected_approach']}")
            print(f"   Actual Approach: {actual_approach}")
            print(f"   Expected AI Generation: {scenario['expected_ai_generation']}")
            print(f"   Actual AI Generation: {actual_ai_generation}")
            print(f"   Reasoning: {response_decision.strategy.get('reasoning', 'No reasoning')}")
            
            # Validate results
            approach_match = actual_approach == scenario['expected_approach']
            ai_generation_match = actual_ai_generation == scenario['expected_ai_generation']
            
            if approach_match and ai_generation_match:
                print(f"   ✅ PASSED")
                test_results['passed'] += 1
                test_results['scenarios'].append({
                    'name': scenario['name'], 
                    'status': 'PASSED',
                    'approach': actual_approach,
                    'ai_generation': actual_ai_generation
                })
            else:
                print(f"   ❌ FAILED")
                print(f"      - Approach match: {approach_match}")
                print(f"      - AI generation match: {ai_generation_match}")
                test_results['failed'] += 1
                test_results['scenarios'].append({
                    'name': scenario['name'], 
                    'status': 'FAILED',
                    'expected_approach': scenario['expected_approach'],
                    'actual_approach': actual_approach,
                    'expected_ai_generation': scenario['expected_ai_generation'],
                    'actual_ai_generation': actual_ai_generation,
                    'reason': f"Approach: {approach_match}, AI Gen: {ai_generation_match}"
                })
            
            # Show enhanced decision details
            strategy = response_decision.strategy
            if strategy.get('enhanced_decision'):
                print(f"   🧠 Enhanced Decision Features:")
                print(f"      - Emotional Intelligence: {strategy.get('emotional_intelligence_used', False)}")
                print(f"      - Priority Resolution: {strategy.get('priority_resolution_used', False)}")
                print(f"      - Fabrication Controls: {strategy.get('fabrication_controls_applied', False)}")
                if strategy.get('current_speaker'):
                    print(f"      - Current Speaker: {strategy.get('current_speaker')}")
                if strategy.get('known_characters'):
                    print(f"      - Known Characters: {strategy.get('known_characters')}")
        
        except Exception as e:
            print(f"   ❌ CRITICAL ERROR: {e}")
            import traceback
            print(f"   📋 Traceback: {traceback.format_exc()}")
            test_results['failed'] += 1
            test_results['scenarios'].append({
                'name': scenario['name'], 
                'status': 'ERROR',
                'error': str(e)
            })
    
    # Summary
    print(f"\n{'=' * 80}")
    print("📋 ENHANCED PATHWAY VALIDATION SUMMARY")
    print(f"{'=' * 80}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"📊 Total: {len(scenarios)}")
    print(f"📈 Success Rate: {(test_results['passed'] / len(scenarios)) * 100:.1f}%")
    
    # Detailed results
    print(f"\n📝 DETAILED RESULTS:")
    for scenario in test_results['scenarios']:
        status_emoji = "✅" if scenario['status'] == 'PASSED' else "❌"
        print(f"   {status_emoji} {scenario['name']}: {scenario['status']}")
        if scenario['status'] == 'FAILED':
            print(f"      Expected: {scenario.get('expected_approach', 'N/A')} | AI: {scenario.get('expected_ai_generation', 'N/A')}")
            print(f"      Actual: {scenario.get('actual_approach', 'N/A')} | AI: {scenario.get('actual_ai_generation', 'N/A')}")
    
    # Validation conclusion
    if test_results['failed'] == 0:
        print(f"\n🎉 ENHANCED PATHWAY VALIDATION: SUCCESS")
        print(f"   All roleplay scenarios work correctly through the enhanced system.")
        print(f"   ✅ Safe to proceed with deprecated function removal.")
    else:
        print(f"\n⚠️  ENHANCED PATHWAY VALIDATION: ISSUES FOUND")
        print(f"   {test_results['failed']} scenarios failed or had errors.")
        print(f"   ❌ Must fix issues before proceeding with refactor.")
    
    return test_results


def setup_fresh_state(rp_state):
    """Setup fresh state (no roleplay active)"""
    if rp_state.is_roleplaying:
        rp_state.end_roleplay_session("test_reset")


def setup_dgm_session(rp_state, participants=None):
    """Setup a DGM-initiated roleplay session"""
    if participants is None:
        participants = ["Tavi"]
    
    # End any existing session
    if rp_state.is_roleplaying:
        rp_state.end_roleplay_session("test_reset")
    
    # Start new DGM session
    rp_state.start_roleplay_session(
        turn_number=1,
        initial_triggers=['dgm_scene_setting'],
        channel_context={"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"},
        dgm_characters=participants
    )
    
    # Add participants
    for participant in participants:
        rp_state.add_participant(participant, "dgm_mentioned", 1)


def benchmark_enhanced_vs_legacy():
    """
    Performance benchmark: enhanced vs legacy pathway.
    NOTE: This is for documentation purposes as we'll remove legacy.
    """
    print(f"\n{'=' * 60}")
    print("⚡ PERFORMANCE BENCHMARK")
    print(f"{'=' * 60}")
    
    # Test message
    test_message = '[Tavi] "Hello Elsie, how are you today?"'
    test_channel = {"type": "GUILD_PUBLIC_THREAD", "is_thread": True, "channel_name": "rp-thread"}
    
    # Setup state
    rp_state = get_roleplay_state()
    setup_dgm_session(rp_state, ["Tavi"])
    
    # Benchmark enhanced pathway
    start_time = time.time()
    for _ in range(10):
        response_decision = route_message_to_handler(test_message, [], test_channel)
    enhanced_time = (time.time() - start_time) / 10
    
    print(f"📊 Enhanced Pathway Average: {enhanced_time:.4f} seconds")
    print(f"📈 Ready for production use")
    
    return enhanced_time


if __name__ == "__main__":
    try:
        # Run validation
        results = run_enhanced_pathway_validation()
        
        # Run benchmark
        benchmark_time = benchmark_enhanced_vs_legacy()
        
        # Final assessment
        print(f"\n{'=' * 80}")
        print("🏁 PHASE 1 VALIDATION COMPLETE")
        print(f"{'=' * 80}")
        
        if results['failed'] == 0:
            print("✅ Enhanced pathway validation: PASSED")
            print("✅ Performance benchmark: COMPLETED")
            print("🚀 Ready to proceed to Phase 2 of refactor plan")
        else:
            print("❌ Enhanced pathway validation: FAILED")
            print("⚠️  Must resolve issues before continuing refactor")
            
    except Exception as e:
        print(f"❌ CRITICAL ERROR in Phase 1 validation: {e}")
        import traceback
        traceback.print_exc() 