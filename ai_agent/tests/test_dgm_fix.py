#!/usr/bin/env python3
"""
DGM Bug Fix Test
================

Test script to verify that DGM scene setting now properly returns "NO_RESPONSE"
instead of None, which was causing the error message.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from handlers.ai_coordinator import coordinate_response
from handlers.ai_attention.state_manager import get_roleplay_state

def test_dgm_scene_setting_fix():
    """Test that DGM scene setting returns NO_RESPONSE instead of None"""
    
    print("🧪 DGM SCENE SETTING BUG FIX TEST")
    print("=" * 50)
    
    # Test message that should trigger DGM scene setting
    dgm_message = "[DGM] The doors to Ten Forward slide open as evening approaches. *Soft lighting casts a warm glow across the empty bar*"
    
    # Simulate conversation history
    conversation_history = []
    
    # Simulate channel context
    channel_context = {
        'channel_id': 'test_channel_123',
        'channel_name': 'test-roleplay',
        'type': 'GUILD_TEXT',
        'is_thread': False,
        'is_dm': False
    }
    
    print(f"📝 Test DGM Message: {dgm_message}")
    print(f"📍 Channel: {channel_context['channel_name']}")
    print()
    
    # Get roleplay state before
    rp_state = get_roleplay_state()
    was_roleplaying_before = rp_state.is_roleplaying
    
    print(f"📊 BEFORE TEST:")
    print(f"   - Roleplaying: {was_roleplaying_before}")
    print()
    
    try:
        # Process the DGM message
        print(f"🔄 PROCESSING DGM MESSAGE...")
        response = coordinate_response(dgm_message, conversation_history, channel_context)
        
        # Check the result
        print(f"\n📊 AFTER TEST:")
        print(f"   - Roleplaying: {rp_state.is_roleplaying}")
        print(f"   - Response: '{response}'")
        print(f"   - Response Type: {type(response)}")
        
        # Validate the fix
        print(f"\n✅ VALIDATION:")
        
        if response is None:
            print(f"   ❌ FAILED: Response is still None (bug not fixed)")
            return False
        elif response == "NO_RESPONSE":
            print(f"   ✅ SUCCESS: Response is 'NO_RESPONSE' (bug fixed)")
            
            # Verify roleplay state was updated correctly
            if rp_state.is_roleplaying:
                print(f"   ✅ SUCCESS: Roleplay session started correctly")
                
                # Check if it's a DGM session
                if rp_state.is_dgm_session():
                    print(f"   ✅ SUCCESS: DGM session detected correctly")
                else:
                    print(f"   ⚠️  WARNING: Not detected as DGM session")
                    
            else:
                print(f"   ❌ FAILED: Roleplay session not started")
                return False
                
        else:
            print(f"   ❌ FAILED: Unexpected response: '{response}'")
            return False
            
        return True
        
    except Exception as e:
        print(f"   ❌ ERROR: Exception occurred: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        # Clean up - end roleplay session if it was started
        if rp_state.is_roleplaying and not was_roleplaying_before:
            rp_state.end_roleplay_session("test_cleanup")
            print(f"   🧹 Cleaned up test roleplay session")


def test_dgm_scene_end_fix():
    """Test that DGM scene end also returns NO_RESPONSE instead of None"""
    
    print(f"\n🧪 DGM SCENE END BUG FIX TEST")
    print("=" * 50)
    
    # First start a roleplay session
    rp_state = get_roleplay_state()
    
    # Start session manually
    rp_state.start_roleplay_session(
        turn_number=1,
        initial_triggers=['dgm_scene_setting'],
        channel_context={'channel_id': 'test', 'channel_name': 'test'}
    )
    
    print(f"📊 SETUP: Started test roleplay session")
    print(f"   - Roleplaying: {rp_state.is_roleplaying}")
    
    # Test DGM scene end message
    dgm_end_message = "[DGM][END]"
    
    print(f"📝 Test DGM End Message: {dgm_end_message}")
    
    try:
        # Process the DGM end message
        response = coordinate_response(dgm_end_message, [], {})
        
        print(f"\n📊 AFTER TEST:")
        print(f"   - Roleplaying: {rp_state.is_roleplaying}")
        print(f"   - Response: '{response}'")
        
        # Validate the fix
        if response == "NO_RESPONSE":
            print(f"   ✅ SUCCESS: DGM scene end returns 'NO_RESPONSE'")
            
            if not rp_state.is_roleplaying:
                print(f"   ✅ SUCCESS: Roleplay session ended correctly")
                return True
            else:
                print(f"   ❌ FAILED: Roleplay session not ended")
                return False
        else:
            print(f"   ❌ FAILED: Expected 'NO_RESPONSE', got '{response}'")
            return False
            
    except Exception as e:
        print(f"   ❌ ERROR: Exception occurred: {e}")
        return False


def main():
    """Run all DGM bug fix tests"""
    
    print("🎯 DGM BUG FIX VERIFICATION")
    print("=" * 60)
    print()
    print("This test verifies that the bug where DGM scene commands")
    print("returned None (causing error messages) has been fixed.")
    print("DGM commands should now return 'NO_RESPONSE' properly.")
    print()
    
    # Run tests
    test1_passed = test_dgm_scene_setting_fix()
    test2_passed = test_dgm_scene_end_fix()
    
    # Summary
    print(f"\n🎯 SUMMARY:")
    print(f"   DGM Scene Setting: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   DGM Scene End: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 ALL TESTS PASSED - DGM bug fix verified!")
        print(f"   DGM commands now properly return 'NO_RESPONSE'")
        print(f"   No more 'holographic matrix flickers' error messages")
    else:
        print(f"\n❌ SOME TESTS FAILED - Bug may not be fully fixed")
    
    return test1_passed and test2_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 