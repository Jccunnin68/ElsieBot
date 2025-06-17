"""
Channel Restrictions
===================

Manages channel-based restrictions for roleplay activities.
Roleplay is only allowed in appropriate channels (threads, DMs) to prevent spam in general channels.
DGM posts can override these restrictions to start roleplay in any channel.
"""

from typing import Dict
import traceback
import re

from .roleplay_types import ALLOWED_CHANNEL_TYPES, RESTRICTED_CHANNEL_TYPES
from .dgm_handler import check_dgm_post

def is_roleplay_allowed_channel(channel_context: Dict = None, user_message: str = None) -> bool:
    """
    Check if roleplay is allowed in the current channel.
    NOTE: Auto-roleplay initiation has been removed - only DGM posts can start roleplay.
    
    ALLOWED CHANNELS:
    - General text channels (GUILD_TEXT) - DGM posts only
    - All thread types (PUBLIC/PRIVATE)
    
    BLOCKED CHANNELS:
    - DMs and Group DMs (DGM posts blocked)
    - Voice channels, categories, directories (not applicable)
    
    All normal conversation is allowed in all text-based channels.
    """
    try:
        print(f"\n🔍 CHANNEL RESTRICTION DEBUG:")
        print(f"   📦 Raw Context: {channel_context}")
        print(f"   📦 Context Type: {type(channel_context)}")
        
        # CHECK FOR DGM POSTS - Block DGM posts in DMs before general override
        if user_message:
            dgm_result = check_dgm_post(user_message)
            if dgm_result['is_dgm']:
                # NEW: Block DGM posts specifically in DMs
                if channel_context:
                    channel_type = channel_context.get('type', 'unknown')
                    is_dm = channel_context.get('is_dm', False) or channel_type.lower() in ['dm', 'group_dm']
                    
                    if is_dm:
                        print(f"   🚫 DGM POST BLOCKED IN DM: DGM posts not allowed in private messages")
                        print(f"   🎬 DGM ACTION: {dgm_result['action']} (blocked)")
                        return False  # Block DGM posts in DMs
                
                # DGM posts override restrictions for appropriate channels (threads, etc.)
                print(f"   🎬 DGM POST DETECTED - OVERRIDING CHANNEL RESTRICTIONS")
                print(f"   🚀 DGM ACTION: {dgm_result['action']}")
                return True
        
        # SIMPLIFIED: DMs no longer block based on message patterns
        # All DM conversations are allowed - roleplay is only blocked from being INITIATED in DMs
        # (but DGM posts can still override this restriction)
        if channel_context:
            channel_type = channel_context.get('type', 'unknown')
            is_dm = channel_context.get('is_dm', False) or channel_type.lower() in ['dm', 'group_dm']
            
            if is_dm:
                print(f"   💬 DM INTERACTION: All patterns allowed in DMs (no auto-roleplay initiation)")
        
        if not channel_context:
            print(f"   ⚠️  No channel context provided - allowing roleplay (testing fallback)")
            return True
        
        # Extract and validate channel info
        try:
            channel_type = channel_context.get('type', 'unknown')
            is_thread = channel_context.get('is_thread', False)
            is_dm = channel_context.get('is_dm', False) or channel_type.lower() in ['dm', 'group_dm']
            channel_name = channel_context.get('name', 'unknown')
            session_id = channel_context.get('session_id', '')
            
            print(f"   📋 Extracted Channel Info:")
            print(f"      - Type: {channel_type} (type: {type(channel_type)})")
            print(f"      - Is Thread: {is_thread} (type: {type(is_thread)})")
            print(f"      - Is DM: {is_dm} (type: {type(is_dm)})")
            print(f"      - Name: {channel_name} (type: {type(channel_name)})")
            print(f"      - Session ID: {session_id} (type: {type(session_id)})")
            
            # DMs allow all normal conversation - no pattern-based restrictions
            # Roleplay can only be initiated by DGM posts (which override restrictions)
            if is_dm:
                print(f"   ✅ DM CONVERSATION ALLOWED: All normal interactions permitted")
                return True  # Changed from False - allow normal DM conversation
            
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
            # REMOVED: DM from allowed conditions
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
            if channel_type in RESTRICTED_CHANNEL_TYPES and not is_thread and not fallback_thread_detected:
                restricted_conditions.append(f"Restricted channel type: {channel_type}")
            
            print(f"   🚫 Restricted Conditions: {restricted_conditions}")
            
        except Exception as e:
            print(f"   ❌ Error checking restrictions: {str(e)}")
            print(f"   📚 Traceback: {traceback.format_exc()}")
        
        # Apply overrides
        try:
            if is_thread or channel_type in ALLOWED_CHANNEL_TYPES or fallback_thread_detected or channel_type == 'unknown':
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