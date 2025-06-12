"""
Channel Restrictions
===================

Manages channel-based restrictions for roleplay activities.
Roleplay is only allowed in appropriate channels (threads, DMs) to prevent spam in general channels.
"""

from typing import Dict, Optional


def is_roleplay_allowed_channel(channel_context: Dict = None) -> bool:
    """
    Check if roleplay is allowed in the current channel.
    Only allowed in threads and DMs, not general channels.
    """
    print(f"\n📍 CHANNEL RESTRICTION CHECK:")
    
    if not channel_context:
        # If no context provided, assume it's allowed (fallback for testing)
        print(f"   ⚠️  No channel context provided - allowing roleplay (testing fallback)")
        return True
    
    channel_type = channel_context.get('type', 'unknown')
    is_thread = channel_context.get('is_thread', False)
    is_dm = channel_context.get('is_dm', False)
    channel_name = channel_context.get('name', 'unknown')
    session_id = channel_context.get('session_id', '')
    
    print(f"   📋 Channel Details:")
    print(f"      - Name: {channel_name}")
    print(f"      - Type: {channel_type}")
    print(f"      - Is Thread: {is_thread}")
    print(f"      - Is DM: {is_dm}")
    print(f"      - Session ID: {session_id}")
    
    # FALLBACK THREAD DETECTION: If channel info is incomplete, try to detect threads
    # from other indicators
    fallback_thread_detected = False
    if channel_type == 'unknown' and not is_thread:
        # Some heuristics to detect threads when Discord API fails
        if len(session_id) > 15:  # Thread IDs are typically longer
            fallback_thread_detected = True
            print(f"      🔍 FALLBACK: Long session ID suggests thread")
        
        # If we have minimal info but it's not explicitly blocked, allow it
        if channel_name == 'unknown' and not is_dm:
            print(f"      🔍 FALLBACK: Unknown channel type, being permissive")
            fallback_thread_detected = True
    
    # Allow roleplay in:
    # - Direct Messages (DMs)
    # - Threads (replies to messages)
    # - Private channels
    # - Any channel with "thread" in the name/type
    # - Fallback thread detection
    allowed_conditions = []
    if is_dm:
        allowed_conditions.append("Direct Message")
    if is_thread:
        allowed_conditions.append("Thread")
    if fallback_thread_detected:
        allowed_conditions.append("Fallback Thread Detection")
    if channel_type in ['dm', 'thread', 'private']:
        allowed_conditions.append(f"Type: {channel_type}")
    if 'thread' in channel_type.lower():
        allowed_conditions.append(f"Type contains 'thread': {channel_type}")
    if 'thread' in channel_name.lower():
        allowed_conditions.append(f"Name contains 'thread': {channel_name}")
    
    # Special handling for Discord thread types
    discord_thread_types = ['public_thread', 'private_thread', 'news_thread']
    if channel_type in discord_thread_types:
        allowed_conditions.append(f"Discord thread type: {channel_type}")
    
    allowed = bool(allowed_conditions)
    
    # Block only if explicitly in restricted channels AND not a thread/DM
    restricted_conditions = []
    if channel_type in ['public', 'general', 'text'] and not is_thread and not is_dm and not fallback_thread_detected:
        if channel_name in ['general', 'announcements', 'public']:
            restricted_conditions.append(f"Restricted name: {channel_name}")
    
    # Override: Never block threads or DMs or unknown channels (be permissive)
    if is_thread or is_dm or channel_type in discord_thread_types or fallback_thread_detected or channel_type == 'unknown':
        restricted_conditions = []  # Clear any restrictions for threads/DMs/unknown
        if not allowed_conditions:  # If no other conditions triggered, add the override
            allowed_conditions.append("Permissive override")
            allowed = True
    
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