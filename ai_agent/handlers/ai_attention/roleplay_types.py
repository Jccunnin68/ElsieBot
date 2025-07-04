"""
Roleplay Types - Shared Types and Constants
===========================================

This module contains shared types and constants used across roleplay-related modules.
This helps break circular dependencies by providing a central location for shared definitions.
"""

from typing import Dict, List, Tuple

# Roleplay state types
RoleplayState = Dict[str, any]
RoleplayTrigger = str
RoleplayConfidence = float
RoleplayDetection = Tuple[bool, RoleplayConfidence, List[RoleplayTrigger]]

# Roleplay strategy types
RoleplayStrategy = Dict[str, any]
RoleplayContext = Dict[str, any]
RoleplayResponse = Dict[str, any]

# Roleplay channel types
ChannelType = str
ChannelContext = Dict[str, any]
ChannelRestriction = bool

# Roleplay participant types
ParticipantType = str
ParticipantRole = str
ParticipantInfo = Dict[str, any]

# Roleplay session types
SessionState = Dict[str, any]
SessionType = str
SessionContext = Dict[str, any]

# Roleplay response types
ResponseType = str
ResponseReason = str
ResponseContext = Dict[str, any]

# Roleplay DGM types
DGMType = str
DGMContext = Dict[str, any]
DGMResponse = Dict[str, any]

# Roleplay exit types
ExitType = str
ExitReason = str
ExitContext = Dict[str, any]

# Discord Channel Types (from Discord API)
# 0: GUILD_TEXT - A text channel within a server
# 1: DM - A direct message between users
# 2: GUILD_VOICE - A voice channel within a server
# 3: GROUP_DM - A direct message between multiple users
# 4: GUILD_CATEGORY - An organizational category that contains up to 50 channels
# 5: GUILD_NEWS - A channel that users can follow and crosspost into their own server
# 6: GUILD_NEWS_THREAD - A temporary sub-channel within a GUILD_NEWS channel
# 7: GUILD_PUBLIC_THREAD - A temporary sub-channel within a GUILD_TEXT channel
# 8: GUILD_PRIVATE_THREAD - A temporary sub-channel within a GUILD_TEXT channel that is only viewable by those invited and those with the MANAGE_THREADS permission
# 9: GUILD_STAGE_VOICE - A voice channel for hosting events with an audience
# 10: GUILD_DIRECTORY - The channel in a hub containing the listed servers
# 11: GUILD_FORUM - A channel that can only contain threads
# 12: GUILD_MEDIA - A channel that can only contain threads, similar to GUILD_FORUM channels

# Roleplay channel restrictions
ALLOWED_CHANNEL_TYPES = [
    'GUILD_TEXT',  # 0 - General public channels (DGM-only roleplay)
    'GUILD_PUBLIC_THREAD',  # 7
    'GUILD_PRIVATE_THREAD',  # 8
    
]

RESTRICTED_CHANNEL_TYPES = [
    'GUILD_VOICE',  # 2 - Voice channels
    'GUILD_STAGE_VOICE',  # 9 - Stage voice channels
    'GUILD_CATEGORY',  # 4 - Category containers
    'GUILD_DIRECTORY',  # 10 - Directory channels
    'DM',  # 1 - Direct messages (DGM blocked)
    'GROUP_DM'  # 3 - Group direct messages (DGM blocked)
    'GUILD_FORUM',  # 11
    'GUILD_MEDIA'  # 12
]

# Roleplay response priorities
RESPONSE_PRIORITIES = {
    'mentioned_by_name': 1,
    'new_session': 2,
    'subtle_bar_service': 3,
    'ongoing_dialogue': 4,
    'passive_listening': 5
}

# Roleplay context priorities
CONTEXT_PRIORITIES = {
    'roleplay': 1,
    'roleplay_listening': 2,
    'dgm_elsie_context': 3,
    'none': 4
}

# Roleplay database needs
DATABASE_NEEDS = {
    'character_info': True,
    'ship_info': True,
    'log_info': True,
    'general_info': False
}

# Roleplay trigger types
TRIGGER_TYPES = {
    'dgm_scene_setting': 'dgm_scene_setting',
    'dgm_scene_end': 'dgm_scene_end',
    'dgm_controlled_elsie': 'dgm_controlled_elsie',
    'ongoing_session': 'ongoing_session',
    'dialogue_continuation': 'dialogue_continuation',
    'thread_channel_monitoring': 'thread_channel_monitoring'
}

# Roleplay approach types - ALL must be prefixed with roleplay_
ROLEPLAY_APPROACHES = {
    'roleplay_active': 'roleplay_active',
    'roleplay_listening': 'roleplay_listening',
    'roleplay_supportive': 'roleplay_supportive',
    'roleplay_group': 'roleplay_group',
    'roleplay_service': 'roleplay_service',
    'roleplay_technical': 'roleplay_technical',
    'roleplay_mock_enhanced': 'roleplay_mock_enhanced',
    'roleplay_fallback': 'roleplay_fallback',
    'roleplay_dgm_controlled': 'roleplay_dgm_controlled',
    'roleplay_cross_channel_busy': 'roleplay_cross_channel_busy',
    'roleplay_quick_database': 'roleplay_quick_database'
}

# Standard approach types - Clean, simple names only
STANDARD_APPROACHES = {
    'character_info': 'character_info',
    'ship_info': 'ship_info',
    'logs': 'logs',
    'tell_me_about': 'tell_me_about',
    'federation_archives': 'federation_archives',
    'url_request': 'url_request',
    'general': 'general',
    'comprehensive': 'comprehensive',
    'continuation': 'continuation',
    'simple_chat': 'simple_chat',
    'menu': 'menu',
    'reset': 'reset'
}

# DGM approach types (special system approaches)
DGM_APPROACHES = {
    'dgm_scene_setting': 'dgm_scene_setting',
    'dgm_scene_end': 'dgm_scene_end',
    'dgm_controlled_elsie': 'dgm_controlled_elsie'
}

# DEPRECATED: Combined approach types - Use specific categories above
APPROACH_TYPES = {
    # Roleplay approaches
    **ROLEPLAY_APPROACHES,
    # Standard approaches  
    **STANDARD_APPROACHES,
    # DGM approaches
    **DGM_APPROACHES
}

# Roleplay exit conditions
EXIT_CONDITIONS = {
    'sustained_topic_shift': 'sustained_topic_shift',
    'explicit_exit': 'explicit_exit',
    'dgm_scene_end': 'dgm_scene_end',
    'channel_restriction': 'channel_restriction',
    'auto_exit_20_minute_timeout': 'auto_exit_20_minute_timeout'
}

# Roleplay response reasons
RESPONSE_REASONS = {
    'mentioned_by_name': 'mentioned_by_name',
    'new_session': 'new_session',
    'subtle_bar_service': 'subtle_bar_service',
    'ongoing_dialogue': 'ongoing_dialogue',
    'passive_listening': 'passive_listening'
}

# Roleplay context types
CONTEXT_TYPES = {
    'roleplay': 'roleplay',
    'roleplay_listening': 'roleplay_listening',
    'dgm_elsie_context': 'dgm_elsie_context',
    'none': 'none'
}

# Roleplay database types
DATABASE_TYPES = {
    'character_info': 'character_info',
    'ship_info': 'ship_info',
    'log_info': 'log_info',
    'general_info': 'general_info'
} 