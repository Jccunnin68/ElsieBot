"""
Channel Restrictions
===================

Manages channel-based restrictions for roleplay activities.
Roleplay is only allowed in appropriate channels (threads, DMs) to prevent spam in general channels.
DGM posts can override these restrictions to start roleplay in any channel.
"""

from typing import Dict
import traceback

from .roleplay_types import ALLOWED_CHANNEL_TYPES, RESTRICTED_CHANNEL_TYPES
from .dgm_handler import check_dgm_post

def is_roleplay_allowed_channel(channel_context: Dict = None, user_message: str = None) -> bool:
    """
    Check if roleplay is allowed in the current channel.
    Only allowed in threads and DMs, not general channels.
    DGM posts can override restrictions and start roleplay anywhere.
    """
    try:
        print(f"\n🔍 CHANNEL RESTRICTION DEBUG:")
        print(f"   📦 Raw Context: {channel_context}")
        print(f"   📦 Context Type: {type(channel_context)}")
        
        # CHECK FOR DGM OVERRIDE FIRST
        if user_message:
            dgm_result = check_dgm_post(user_message)
            if dgm_result['is_dgm']:
                print(f"   🎬 DGM POST DETECTED - OVERRIDING ALL CHANNEL RESTRICTIONS")
                print(f"   🚀 DGM ACTION: {dgm_result['action']}")
                return True
        
        if not channel_context:
            print(f"   ⚠️  No channel context provided - allowing roleplay (testing fallback)")
            return True
        
        # Extract and validate channel info
        try:
            channel_type = channel_context.get('type', 'unknown')
            is_thread = channel_context.get('is_thread', False)
            is_dm = channel_context.get('is_dm', False)
            channel_name = channel_context.get('name', 'unknown')
            session_id = channel_context.get('session_id', '')
            
            print(f"   📋 Extracted Channel Info:")
            print(f"      - Type: {channel_type} (type: {type(channel_type)})")
            print(f"      - Is Thread: {is_thread} (type: {type(is_thread)})")
            print(f"      - Is DM: {is_dm} (type: {type(is_dm)})")
            print(f"      - Name: {channel_name} (type: {type(channel_name)})")
            print(f"      - Session ID: {session_id} (type: {type(session_id)})")
            
            # Validate channel type
            print(f"   🔍 Channel Type Validation:")
            print(f"      - ALLOWED types: {ALLOWED_CHANNEL_TYPES} (type: {type(ALLOWED_CHANNEL_TYPES)})")
            print(f"      - RESTRICTED types: {RESTRICTED_CHANNEL_TYPES} (type: {type(RESTRICTED_CHANNEL_TYPES)})")
            print(f"      - Is in ALLOWED_CHANNEL_TYPES: {channel_type in ALLOWED_CHANNEL_TYPES}")
            print(f"      - Is in RESTRICTED_CHANNEL_TYPES: {channel_type in RESTRICTED_CHANNEL_TYPES}")
            
            # Debug each comparison
            print(f"   🔍 Detailed Type Comparisons:")
            for allowed_type in ALLOWED_CHANNEL_TYPES:
                print(f"      - Comparing '{channel_type}' ({type(channel_type)}) with '{allowed_type}' ({type(allowed_type)})")
                print(f"        Equal? {channel_type == allowed_type}")
            
            for restricted_type in RESTRICTED_CHANNEL_TYPES:
                print(f"      - Comparing '{channel_type}' ({type(channel_type)}) with '{restricted_type}' ({type(restricted_type)})")
                print(f"        Equal? {channel_type == restricted_type}")
            
        except Exception as e:
            print(f"   ❌ Error extracting channel info: {str(e)}")
            print(f"   📚 Traceback: {traceback.format_exc()}")
            return True  # Fail open for safety
        
        # FALLBACK THREAD DETECTION
        fallback_thread_detected = False
        try:
            if channel_type == 'unknown' and not is_thread:
                if len(session_id) > 15:
                    fallback_thread_detected = True
                    print(f"      🔍 FALLBACK: Long session ID suggests thread")
                
                if channel_name == 'unknown' and not is_dm:
                    fallback_thread_detected = True
                    print(f"      🔍 FALLBACK: Unknown channel type, being permissive")
        except Exception as e:
            print(f"   ❌ Error in fallback detection: {str(e)}")
            print(f"   📚 Traceback: {traceback.format_exc()}")
        
        # Build allowed conditions
        allowed_conditions = []
        try:
            if is_dm:
                allowed_conditions.append("Direct Message")
            if is_thread:
                allowed_conditions.append("Thread")
            if fallback_thread_detected:
                allowed_conditions.append("Fallback Thread Detection")
            if channel_type in ALLOWED_CHANNEL_TYPES:
                allowed_conditions.append(f"Allowed channel type: {channel_type}")
            if 'thread' in channel_type.lower():
                allowed_conditions.append(f"Type contains 'thread': {channel_type}")
            if 'thread' in channel_name.lower():
                allowed_conditions.append(f"Name contains 'thread': {channel_name}")
            
            print(f"   ✅ Allowed Conditions: {allowed_conditions}")
            
        except Exception as e:
            print(f"   ❌ Error building allowed conditions: {str(e)}")
            print(f"   📚 Traceback: {traceback.format_exc()}")
        
        allowed = bool(allowed_conditions)
        
        # Check restrictions
        restricted_conditions = []
        try:
            if channel_type in RESTRICTED_CHANNEL_TYPES and not is_thread and not is_dm and not fallback_thread_detected:
                restricted_conditions.append(f"Restricted channel type: {channel_type}")
            
            print(f"   🚫 Restricted Conditions: {restricted_conditions}")
            
        except Exception as e:
            print(f"   ❌ Error checking restrictions: {str(e)}")
            print(f"   📚 Traceback: {traceback.format_exc()}")
        
        # Apply overrides
        try:
            if is_thread or is_dm or channel_type in ALLOWED_CHANNEL_TYPES or fallback_thread_detected or channel_type == 'unknown':
                restricted_conditions = []
                if not allowed_conditions:
                    allowed_conditions.append("Permissive override")
                    allowed = True
                
            print(f"   🔄 After Overrides:")
            print(f"      - Allowed Conditions: {allowed_conditions}")
            print(f"      - Restricted Conditions: {restricted_conditions}")
            
        except Exception as e:
            print(f"   ❌ Error applying overrides: {str(e)}")
            print(f"   📚 Traceback: {traceback.format_exc()}")
        
        # Final decision
        if restricted_conditions:
            allowed = False
            print(f"   🚫 BLOCKED by: {', '.join(restricted_conditions)}")
        elif allowed_conditions:
            print(f"   ✅ ALLOWED by: {', '.join(allowed_conditions)}")
        else:
            print(f"   ❓ NO SPECIFIC RULES - defaulting to ALLOWED")
            allowed = True
        
        print(f"   🎯 FINAL DECISION: {'ROLEPLAY ALLOWED' if allowed else 'ROLEPLAY BLOCKED'}")
        return allowed
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in is_roleplay_allowed_channel:")
        print(f"   Error: {str(e)}")
        print(f"   Type: {type(e).__name__}")
        print(f"   Traceback: {traceback.format_exc()}")
        print(f"   Channel Context: {channel_context}")
        return True  # Fail open for safety 