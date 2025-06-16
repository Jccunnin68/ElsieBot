"""
Roleplay State Manager
=====================

Manages the state of ongoing roleplay sessions, including participant tracking,
turn management, and conversation flow logic.
Enhanced with conversation memory for better context continuity.
"""

import time
from typing import Dict, List, Optional
from .character_tracking import extract_current_speaker, is_valid_character_name
from .conversation_memory import ConversationMemory, getNextResponse, extract_conversation_metadata
from .contextual_cues import SessionMode


class RoleplayStateManager:
    """
    Context & State Manager for roleplay sessions.
    Maintains speaker permanence and roleplay context.
    Enhanced with passive listening and channel restrictions.
    Now supports DGM-initiated sessions with special behavior.
    Enhanced with 20-minute auto-exit functionality for abandoned sessions.
    """
    
    def __init__(self):
        self.is_roleplaying = False
        self.participants = []
        self.setting_description = ""
        self.session_start_turn = 0
        self.confidence_history = []
        self.exit_condition_count = 0
        self.channel_context = {}
        self.listening_mode = False
        self.last_response_turn = 0
        self.listening_turn_count = 0  # Track consecutive listening turns
        self.last_interjection_turn = 0  # Track when we last interjected
        self.dgm_initiated = False  # Track if session was started by DGM
        self.dgm_characters = []  # Characters mentioned in DGM post
        self.is_thread_session = False  # Track if this is a thread-based session
        
        # ENHANCED: Channel isolation tracking
        self.roleplay_channel_id = None  # Track which channel roleplay is happening in
        self.roleplay_channel_name = None  # Human-readable channel name
        self.roleplay_channel_type = None  # Channel type for validation
        
        # NEW: 20-minute auto-exit functionality
        self.last_roleplay_channel_activity_time = None  # Timestamp of last activity in RP channel
        
        # Simple implicit response tracking
        self.last_character_elsie_addressed = ""  # Who did Elsie last speak to
        self.last_character_spoke = ""  # Who spoke last (not Elsie)
        self.turn_history = []  # Simple turn tracking: [(turn_number, speaker)]
        
        # NEW: Conversation memory for enhanced context continuity
        self.conversation_memory = ConversationMemory(max_history=5)
        self.last_conversation_analysis = None  # Cache for last conversation analysis
        
        # PHASE 2C: DGM scene context storage
        self.dgm_scene_context = {}  # Store scene context from DGM posts
    
    def start_roleplay_session(self, turn_number: int, initial_triggers: List[str], channel_context: Dict = None, dgm_characters: List[str] = None):
        """Initialize a new roleplay session with channel isolation."""
        self.is_roleplaying = True
        self.session_start_turn = turn_number
        self.participants = []
        self.setting_description = ""
        self.confidence_history = []
        self.exit_condition_count = 0
        self.channel_context = channel_context or {}
        self.listening_mode = False
        self.last_response_turn = 0
        self.listening_turn_count = 0
        self.last_interjection_turn = 0
        
        # ENHANCED: Store channel information for isolation
        if channel_context:
            self.roleplay_channel_id = channel_context.get('channel_id')
            self.roleplay_channel_name = channel_context.get('channel_name', 'Unknown Channel')
            self.roleplay_channel_type = channel_context.get('type', 'unknown')
        else:
            self.roleplay_channel_id = None
            self.roleplay_channel_name = 'Unknown Channel'
            self.roleplay_channel_type = 'unknown'
        
        # NEW: Initialize activity timestamp for auto-exit functionality
        self.last_roleplay_channel_activity_time = time.time()
        
        # Reset simple tracking
        self.last_character_elsie_addressed = ""
        self.last_character_spoke = ""
        self.turn_history = []
        
        # Reset conversation memory
        self.conversation_memory.clear_memory()
        self.last_conversation_analysis = None
        
        # PHASE 2C: Reset DGM scene context
        self.dgm_scene_context = {}
        
        # Check if this is a DGM-initiated session
        self.dgm_initiated = 'dgm_scene_setting' in initial_triggers
        self.dgm_characters = dgm_characters or []
        
        # Check if this is a thread-based session
        self.is_thread_session = False
        if channel_context:
            is_thread = channel_context.get('is_thread', False)
            channel_type = channel_context.get('type', '')
            if is_thread or any(thread_type in channel_type.lower() for thread_type in ['thread', 'forum']):
                self.is_thread_session = True
        
        # Add DGM-mentioned characters to participants
        if self.dgm_characters:
            for character in self.dgm_characters:
                self.add_participant(character, "dgm_mentioned", turn_number)
        
        print(f"\n🎭 ROLEPLAY SESSION STARTED:")
        print(f"   📅 Turn: {turn_number}")
        print(f"   🎯 Triggers: {initial_triggers}")
        print(f"   📍 Channel: {self.roleplay_channel_name} (ID: {self.roleplay_channel_id})")
        print(f"   🔧 Channel Type: {self.roleplay_channel_type}")
        print(f"   🎬 DGM Initiated: {self.dgm_initiated}")
        print(f"   🧵 Thread Session: {self.is_thread_session}")
        if self.dgm_characters:
            print(f"   👥 DGM Characters: {self.dgm_characters}")
        print(f"   🎮 State: {'DGM PASSIVE MONITORING' if self.dgm_initiated else 'ACTIVE MONITORING'}")
        print(f"   🔒 CHANNEL LOCK: Messages from other channels will be rejected")
    
    def add_participant(self, name: str, source: str, turn_number: int):
        """Add a new participant to the roleplay session."""
        # Normalize the name for comparison (handle case variations)
        name_normalized = name.strip()
        
        # FILTER OUT ELSIE - She should never be a participant
        elsie_names = {'elsie', 'elise', 'elsy', 'els', 'bartender', 'barkeep', 'barmaid', 'server', 'waitress'}
        if name_normalized.lower() in elsie_names:
            print(f"   🚫 FILTERED OUT ELSIE: '{name_normalized}' - Elsie should not be a participant")
            return
        
        # Check if participant already exists (case-insensitive)
        for participant in self.participants:
            if participant['name'].lower() == name_normalized.lower():
                print(f"   👤 PARTICIPANT EXISTS: {name_normalized} (already tracked as '{participant['name']}')")
                # Update the turn number to show they're still active
                participant['last_mentioned_turn'] = turn_number
                return  # Already exists
        
        participant = {
            'name': name_normalized,
            'source': source,
            'mentioned_in_turn': turn_number,
            'last_mentioned_turn': turn_number
        }
        self.participants.append(participant)
        print(f"   👤 NEW PARTICIPANT ADDED:")
        print(f"      - Name: {name_normalized}")
        print(f"      - Source: {source}")
        print(f"      - Turn: {turn_number}")
        print(f"      - Total Tracked: {len(self.participants)}")
        print(f"      - All Participants: {[p['name'] for p in self.participants]}")
        print(f"      - DGM Session: {self.dgm_initiated}")
    
    def add_addressed_characters(self, character_names: List[str], turn_number: int):
        """Add characters that were addressed by others."""
        for name in character_names:
            self.add_participant(name, "addressed", turn_number)
    
    def set_listening_mode(self, listening: bool, reason: str = ""):
        """Set whether Elsie is in listening mode."""
        self.listening_mode = listening
        
        print(f"\n👂 LISTENING MODE UPDATE:")
        print(f"   🔄 Mode: {'LISTENING' if listening else 'ACTIVE'}")
        print(f"   📝 Reason: {reason}")
        
        if listening:
            self.listening_turn_count += 1
            print(f"   🔢 Listening Turn Count: {self.listening_turn_count}")
            print(f"   📊 Monitoring: {len(self.participants)} participants")
        else:
            self.listening_turn_count = 0  # Reset when not listening
            print(f"   🎬 Active response mode engaged")
    
    def should_interject_subtle_action(self, turn_number: int) -> bool:
        """
        Determine if Elsie should interject a subtle action to maintain presence.
        For DGM-initiated sessions: every 5-8 turns (more passive presence)
        For regular sessions: every 8-10 turns (less frequent)
        """
        if not self.listening_mode:
            return False
        
        # Different thresholds for DGM vs regular sessions
        if self.dgm_initiated:
            # DGM sessions: interject every 5-8 turns (more passive presence)
            min_turns = 5
            max_turns = 8
        else:
            # Regular sessions: interject every 8-10 turns (less frequent)
            min_turns = 8
            max_turns = 10
        
        # Check if we've reached the minimum threshold
        if self.listening_turn_count >= min_turns:
            return True
        
        # Also interject if it's been too long since last interjection
        turns_since_interjection = turn_number - self.last_interjection_turn
        max_silence = 15 if self.dgm_initiated else 20
        
        if turns_since_interjection >= max_silence:
            return True
        
        return False
    
    def mark_interjection(self, turn_number: int):
        """Mark that Elsie interjected a subtle action."""
        self.last_interjection_turn = turn_number
        self.listening_turn_count = 0  # Reset listening count after interjection
        print(f"   ✨ SUBTLE INTERJECTION MARKED - Turn {turn_number}")
    
    def mark_response_turn(self, turn_number: int):
        """Mark that Elsie responded on this turn."""
        self.last_response_turn = turn_number
        self.listening_turn_count = 0  # Reset listening count after active response
        
        # Track turn history
        self.turn_history.append((turn_number, "Elsie"))
        # Keep only last 10 turns
        if len(self.turn_history) > 10:
            self.turn_history.pop(0)
    
    def mark_character_turn(self, turn_number: int, character_name: str):
        """Mark that a character spoke on this turn."""
        self.last_character_spoke = character_name
        
        # Track turn history
        self.turn_history.append((turn_number, character_name))
        # Keep only last 10 turns
        if len(self.turn_history) > 10:
            self.turn_history.pop(0)
        
        print(f"   📝 CHARACTER TURN TRACKED: {character_name} (Turn {turn_number})")
    
    def get_last_turn_info(self) -> Dict:
        """Get information about the last turn in the conversation."""
        if not self.turn_history:
            return {}
        
        last_turn_number, last_speaker = self.turn_history[-1]
        return {
            'turn_number': last_turn_number,
            'speaker': last_speaker
        }
    
    def set_last_character_addressed(self, character_name: str):
        """Set who Elsie last addressed."""
        self.last_character_elsie_addressed = character_name
        print(f"   👤 ELSIE ADDRESSED: {character_name}")
    
    def is_simple_implicit_response(self, current_turn: int, user_message: str) -> bool:
        """
        ENHANCED implicit response logic:
        - Only trigger if the character was ACTUALLY talking TO Elsie previously
        - Check conversation flow to ensure they're not now talking to someone else
        - Prevent false positives when characters are having conversations with each other
        ENHANCED: Now works with conversation memory for better tracking
        """
        # Check if we have any turn history
        if not self.turn_history:
            print(f"   💭 IMPLICIT RESPONSE CHECK: No turn history available")
            return False
        
        # Extract character name from current message
        current_character = extract_current_speaker(user_message)
        if not current_character:
            print(f"   💭 IMPLICIT RESPONSE CHECK: No current character detected")
            return False
        
        print(f"   💭 IMPLICIT RESPONSE CHECK:")
        print(f"      - Current character: {current_character}")
        print(f"      - Elsie last addressed: {self.last_character_elsie_addressed}")
        print(f"      - DGM session: {self.is_dgm_session()}")
        print(f"      - Conversation memory available: {self.has_conversation_memory()}")
        
        # CRITICAL: Check if this character is the one Elsie last addressed
        # This ensures we only respond to characters who were talking TO Elsie
        if not (self.last_character_elsie_addressed and 
                current_character.lower() == self.last_character_elsie_addressed.lower()):
            print(f"   ❌ IMPLICIT RESPONSE REJECTED: Character '{current_character}' not last addressed by Elsie ('{self.last_character_elsie_addressed}')")
            return False
        
        # Find the most recent turn where Elsie spoke
        elsie_last_turn = None
        for turn_num, speaker in reversed(self.turn_history):
            if speaker == "Elsie":
                elsie_last_turn = turn_num
                break
        
        # Check if Elsie spoke recently (within 2 turns of current)
        if not elsie_last_turn or current_turn - elsie_last_turn > 2:
            print(f"   ❌ IMPLICIT RESPONSE REJECTED: Elsie last spoke {current_turn - (elsie_last_turn or 0)} turns ago (limit: 2)")
            return False
        
        # ENHANCED: Check if this message is actually directed at someone else
        # This prevents false positives when characters start talking to each other
        from .response_logic import check_if_other_character_addressed
        other_character = check_if_other_character_addressed(user_message, self)
        if other_character:
            print(f"   ❌ IMPLICIT RESPONSE REJECTED: '{current_character}' is addressing '{other_character}', not Elsie")
            return False
        
        # Check if the message contains other character names (redirecting conversation)
        if self._message_contains_other_character_names(user_message):
            print(f"   ❌ IMPLICIT RESPONSE REJECTED: Message contains other character names - conversation redirected")
            return False
        
        # ENHANCED: Cross-check with conversation memory if available
        if self.has_conversation_memory():
            recent_turns = self.conversation_memory.get_recent_history(3)
            print(f"   💭 CONVERSATION MEMORY CROSS-CHECK:")
            for turn in recent_turns:
                print(f"      - Turn {turn.turn_number}: [{turn.speaker}] addressed_to: {turn.addressed_to}")
            
            # Look for Elsie addressing this character in recent memory
            elsie_addressed_character = False
            for turn in reversed(recent_turns):
                if turn.speaker == "Elsie" and turn.addressed_to and turn.addressed_to.lower() == current_character.lower():
                    elsie_addressed_character = True
                    print(f"   ✅ CONVERSATION MEMORY CONFIRMS: Elsie addressed {current_character} in turn {turn.turn_number}")
                    break
            
            if not elsie_addressed_character:
                print(f"   ⚠️  CONVERSATION MEMORY WARNING: No record of Elsie addressing {current_character} recently")
        
        print(f"   ✅ SIMPLE IMPLICIT RESPONSE CONFIRMED (DGM Compatible):")
        print(f"      - Elsie last addressed: {self.last_character_elsie_addressed}")
        print(f"      - Current speaker: {current_character}")
        print(f"      - Elsie last spoke: Turn {elsie_last_turn} ({current_turn - elsie_last_turn} turns ago)")
        print(f"      - No other characters addressed")
        print(f"      - This is a genuine follow-up TO Elsie")
        print(f"      - DGM IMPLICIT RESPONSE: {'ALLOWED' if self.is_dgm_session() else 'N/A'}")
        
        return True
    
    def _message_contains_other_character_names(self, user_message: str) -> bool:
        """
        Check if the message contains character names that would indicate
        it's directed at someone other than Elsie.
        NOTE: Ignores speaker brackets [Character Name] since those indicate who is speaking, not being addressed.
        """
        print(f"      🔍 _message_contains_other_character_names DEBUG:")
        print(f"         - Message: '{user_message}'")
        
        # Import here to avoid circular imports
        from .character_tracking import extract_character_names_from_emotes, extract_addressed_characters
        
        # Extract speaker from bracket format [Character Name] - this should be ignored
        speaker_from_bracket = extract_current_speaker(user_message)
        print(f"         - Speaker from bracket: '{speaker_from_bracket}'")
        
        # Check for character names in emotes and addressing patterns
        character_names = extract_character_names_from_emotes(user_message)
        addressed_characters = extract_addressed_characters(user_message)
        
        print(f"         - Character names from emotes: {character_names}")
        print(f"         - Addressed characters: {addressed_characters}")
        
        # Combine all detected character names
        all_detected_names = set(character_names + addressed_characters)
        print(f"         - All detected names: {all_detected_names}")
        
        # Filter out Elsie's names (these are fine for implicit responses)
        elsie_names = {'elsie', 'elise', 'elsy', 'els', 'bartender', 'barkeep', 'barmaid', 'server', 'waitress'}
        
        # Filter out the speaker (from brackets) since that's who is talking, not being addressed
        other_character_names = [name for name in all_detected_names 
                               if (name.lower() not in elsie_names and 
                                   is_valid_character_name(name) and
                                   name.lower() != speaker_from_bracket.lower())]
        
        print(f"         - After filtering Elsie names: {[name for name in all_detected_names if name.lower() not in elsie_names]}")
        print(f"         - After filtering speaker '{speaker_from_bracket}': {other_character_names}")
        
        if other_character_names:
            print(f"      🎯 OTHER CHARACTER NAMES DETECTED: {other_character_names}")
            return True
        
        print(f"      ✅ No other character names detected")
        return False
    
    def get_participant_names(self) -> List[str]:
        """Get list of all participant names."""
        return [p['name'] for p in self.participants]
    
    def get_active_participants(self, current_turn: int, max_turns_inactive: int = 10) -> List[str]:
        """Get list of participants who have been mentioned recently."""
        active = []
        for participant in self.participants:
            turns_since_mention = current_turn - participant.get('last_mentioned_turn', participant['mentioned_in_turn'])
            if turns_since_mention <= max_turns_inactive:
                active.append(participant['name'])
        return active
    
    def update_confidence(self, confidence_score: float):
        """
        Track confidence scores for debugging/logging purposes.
        Note: Topic shift detection is DISABLED during roleplay mode to maintain conversation memory.
        """
        if not self.is_roleplaying:
            # Only track confidence for topic shift detection when NOT in roleplay
            self.confidence_history.append(confidence_score)
            # Keep only last 5 scores
            if len(self.confidence_history) > 5:
                self.confidence_history.pop(0)
        else:
            # In roleplay mode: log confidence but don't use for exit decisions
            print(f"   📊 ROLEPLAY CONFIDENCE: {confidence_score:.2f} (logging only - topic shifts disabled)")
    
    def check_sustained_topic_shift(self) -> bool:
        """
        Check if there's been a sustained shift away from roleplay.
        DISABLED during roleplay mode to maintain conversation memory.
        """
        if self.is_roleplaying:
            print(f"   🎭 TOPIC SHIFT CHECK DISABLED: In roleplay mode - maintaining conversation memory")
            return False
        
        if len(self.confidence_history) < 3:
            return False
        
        # If last 3 scores are all below threshold, it's a sustained shift
        recent_scores = self.confidence_history[-3:]
        return all(score < 0.15 for score in recent_scores)
    
    def increment_exit_condition(self):
        """
        Increment exit condition counter.
        DISABLED during roleplay mode to prevent topic-based exits.
        """
        if not self.is_roleplaying:
            self.exit_condition_count += 1
            print(f"   📈 EXIT CONDITION COUNT: {self.exit_condition_count}")
        else:
            print(f"   🎭 EXIT CONDITION IGNORED: In roleplay mode - topic changes don't trigger exits")
    
    def should_exit_from_sustained_shift(self) -> bool:
        """
        Determine if we should exit due to sustained non-RP behavior.
        ALWAYS returns False during roleplay mode to maintain conversation memory.
        """
        if self.is_roleplaying:
            print(f"   🎭 SUSTAINED SHIFT EXIT DISABLED: In roleplay mode - only DGM or timeout can end session")
            return False
        
        # Only check topic shifts when NOT in roleplay mode
        return (self.check_sustained_topic_shift() or 
                self.exit_condition_count >= 2)
    
    def end_roleplay_session(self, reason: str):
        """End the current roleplay session and reset all state."""
        print(f"   🎭 ROLEPLAY SESSION ENDED - Reason: {reason}")
        print(f"   📍 Was in channel: {self.roleplay_channel_name} (ID: {self.roleplay_channel_id})")
        
        self.is_roleplaying = False
        self.participants = []
        self.setting_description = ""
        self.confidence_history = []
        self.exit_condition_count = 0
        self.channel_context = {}
        self.listening_mode = False
        self.last_response_turn = 0
        self.dgm_initiated = False
        self.dgm_characters = []
        self.is_thread_session = False
        
        # ENHANCED: Reset channel tracking
        self.roleplay_channel_id = None
        self.roleplay_channel_name = None
        self.roleplay_channel_type = None
        
        # NEW: Reset activity timestamp
        self.last_roleplay_channel_activity_time = None
        
        # Reset turn tracking
        self.last_character_elsie_addressed = ""
        self.last_character_spoke = ""
        self.turn_history = []
        
        # Reset conversation memory
        self.conversation_memory.clear_memory()
        self.last_conversation_analysis = None
        
        print(f"   🔓 CHANNEL LOCK RELEASED - Now accepting messages from all channels")
    
    def is_dgm_session(self) -> bool:
        """Check if this is a DGM-initiated session."""
        return self.dgm_initiated
    
    def is_thread_based(self) -> bool:
        """Check if this is a thread-based session."""
        return self.is_thread_session
    
    def get_dgm_characters(self) -> List[str]:
        """Get characters that were mentioned in the DGM post."""
        return self.dgm_characters.copy()
    
    def add_speaking_character(self, character_name: str, turn_number: int):
        """
        Add a character who is speaking (even if not explicitly mentioned).
        This is for tracking characters as they participate in DGM sessions.
        """
        self.add_participant(character_name, "speaking", turn_number)
        print(f"   🗣️ SPEAKING CHARACTER ADDED: {character_name} (Turn {turn_number})")
    
    def store_dgm_scene_context(self, scene_context: Dict):
        """
        PHASE 2C: Store DGM scene context for use in future responses.
        This allows Elsie to understand and reference the scene setting.
        """
        if scene_context:
            self.dgm_scene_context.update(scene_context)
            print(f"   🎬 DGM SCENE CONTEXT STORED:")
            for key, value in scene_context.items():
                if key != 'raw_description':  # Don't log the full description
                    print(f"      - {key}: {value}")
    
    def get_dgm_scene_context(self) -> Dict:
        """Get the stored DGM scene context."""
        return self.dgm_scene_context.copy()
    
    def to_dict(self) -> Dict:
        """Convert state to dictionary for logging/debugging."""
        return {
            'is_roleplaying': self.is_roleplaying,
            'participants': self.participants,
            'setting_description': self.setting_description,
            'session_start_turn': self.session_start_turn,
            'confidence_history': self.confidence_history,
            'exit_condition_count': self.exit_condition_count,
            'channel_context': self.channel_context,
            'listening_mode': self.listening_mode,
            'last_response_turn': self.last_response_turn,
            'listening_turn_count': self.listening_turn_count,
            'last_interjection_turn': self.last_interjection_turn,
            'dgm_initiated': self.dgm_initiated,
            'dgm_characters': self.dgm_characters,
            'is_thread_session': self.is_thread_session,
            'roleplay_channel_id': self.roleplay_channel_id,
            'roleplay_channel_name': self.roleplay_channel_name,
            'roleplay_channel_type': self.roleplay_channel_type,
            'last_roleplay_channel_activity_time': self.last_roleplay_channel_activity_time
        }
    
    def is_message_from_roleplay_channel(self, message_channel_context: Dict = None) -> bool:
        """
        Check if a message is from the same channel where roleplay is happening.
        Returns True if message is from roleplay channel, False if from different channel.
        Enhanced to handle cases where channel_id might be missing.
        """
        if not self.is_roleplaying or not message_channel_context:
            return True  # No restriction when not roleplaying or no context
        
        # Primary comparison: channel_id
        message_channel_id = message_channel_context.get('channel_id')
        roleplay_channel_id = self.roleplay_channel_id
        
        if message_channel_id and roleplay_channel_id:
            is_same_channel = message_channel_id == roleplay_channel_id
            
            if not is_same_channel:
                message_channel_name = message_channel_context.get('channel_name', 'Unknown')
                print(f"   🚫 CROSS-CHANNEL REJECTED (ID): Message from '{message_channel_name}' (ID: {message_channel_id}) while roleplaying in '{self.roleplay_channel_name}' (ID: {roleplay_channel_id})")
            
            return is_same_channel
        
        # Fallback comparison: channel_name (when IDs are missing)
        message_channel_name = message_channel_context.get('channel_name', '')
        roleplay_channel_name = self.roleplay_channel_name or ''
        
        if message_channel_name and roleplay_channel_name:
            is_same_channel = message_channel_name == roleplay_channel_name
            
            if not is_same_channel:
                print(f"   🚫 CROSS-CHANNEL REJECTED (NAME): Message from '{message_channel_name}' while roleplaying in '{roleplay_channel_name}'")
                print(f"      - Warning: Using fallback name comparison due to missing channel IDs")
            
            return is_same_channel
        
        # Final fallback: if we can't determine, allow the message but log warning
        print(f"   ⚠️  CROSS-CHANNEL CHECK: Cannot determine channel match - allowing message")
        print(f"      - Message context: {message_channel_context}")
        print(f"      - Roleplay channel: ID={roleplay_channel_id}, Name={roleplay_channel_name}")
        
        return True  # Fail open for safety
    
    def get_roleplay_channel_info(self) -> Dict:
        """Get information about the current roleplay channel."""
        return {
            'channel_id': self.roleplay_channel_id,
            'channel_name': self.roleplay_channel_name,
            'channel_type': self.roleplay_channel_type,
            'is_thread': self.is_thread_session
        }
    
    def update_roleplay_channel_activity(self):
        """
        Update the timestamp for the last activity in the roleplay channel.
        Called for ANY message that occurs in the roleplay channel.
        """
        self.last_roleplay_channel_activity_time = time.time()
        print(f"   ⏰ ROLEPLAY CHANNEL ACTIVITY UPDATED: {time.strftime('%H:%M:%S', time.localtime(self.last_roleplay_channel_activity_time))}")
    
    def reset_activity_timer_for_dgm(self, reason: str = "dgm_scene_event"):
        """
        Reset the activity timer for DGM events (scene starts, etc).
        This prevents edge cases where DGM posts right after scene start might trigger timeout.
        """
        self.last_roleplay_channel_activity_time = time.time()
        print(f"   🎬 DGM TIMER RESET: Activity timer reset for {reason} at {time.strftime('%H:%M:%S', time.localtime(self.last_roleplay_channel_activity_time))}")
    
    def should_auto_exit_roleplay(self) -> bool:
        """
        Check if roleplay session should auto-exit due to 20 minutes of inactivity
        in the roleplay channel.
        """
        if not self.is_roleplaying or not self.last_roleplay_channel_activity_time:
            return False
        
        current_time = time.time()
        time_since_activity = current_time - self.last_roleplay_channel_activity_time
        timeout_minutes = time_since_activity / 60
        
        is_timeout = time_since_activity >= 1200  # 20 minutes = 1200 seconds
        
        if is_timeout:
            print(f"   ⏰ AUTO-EXIT CHECK: {timeout_minutes:.1f} minutes since last activity - TIMEOUT REACHED")
        else:
            print(f"   ⏰ AUTO-EXIT CHECK: {timeout_minutes:.1f} minutes since last activity - still active")
        
        return is_timeout
    
    def auto_exit_roleplay(self, reason: str = "20_minute_timeout"):
        """
        Automatically exit roleplay session due to timeout.
        Provides appropriate logging and cleanup.
        """
        if not self.is_roleplaying:
            return
        
        timeout_minutes = 0
        if self.last_roleplay_channel_activity_time:
            time_since_activity = time.time() - self.last_roleplay_channel_activity_time
            timeout_minutes = time_since_activity / 60
        
        print(f"   🕐 AUTO-EXIT TRIGGERED:")
        print(f"      - Reason: {reason}")
        print(f"      - Minutes since last activity: {timeout_minutes:.1f}")
        print(f"      - Channel: {self.roleplay_channel_name}")
        
        # Use existing end_roleplay_session but with auto-exit reason
        self.end_roleplay_session(f"auto_exit_{reason}")
    
    def add_conversation_turn(self, speaker: str, message: str, turn_number: int, addressed_to: Optional[str] = None):
        """
        Add a conversation turn to memory for enhanced context tracking.
        This supplements the existing turn tracking with detailed conversation memory.
        """
        if not self.is_roleplaying:
            return
        
        # Extract message metadata
        metadata = extract_conversation_metadata(message)
        message_type = metadata['message_type']
        
        # Add to conversation memory
        self.conversation_memory.add_turn(
            speaker=speaker,
            message=message,
            turn_number=turn_number,
            addressed_to=addressed_to,
            message_type=message_type
        )
        
        print(f"   💭 CONVERSATION TURN ADDED: {speaker} -> {message_type}")
        if addressed_to:
            print(f"      - Addressed to: {addressed_to}")
    
    def get_conversation_analysis(self, current_turn: int) -> Optional[Dict]:
        """
        Get conversation analysis for the current turn.
        This uses the getNextResponse subroutine to analyze conversation flow.
        """
        if not self.conversation_memory.has_sufficient_context():
            return None
        
        try:
            # Prepare conversation history for analysis
            conversation_history = []
            for turn in self.conversation_memory.get_recent_history():
                conversation_history.append({
                    'speaker': turn.speaker,
                    'message': turn.message,
                    'turn_number': turn.turn_number,
                    'message_type': turn.message_type,
                    'addressed_to': turn.addressed_to
                })
            
            # Get character context
            character_context = {
                'dgm_session': self.dgm_initiated,
                'thread_session': self.is_thread_session,
                'participants': self.get_participant_names(),
                'listening_mode': self.listening_mode
            }
            
            # Analyze conversation
            suggestion, analyzed = getNextResponse(
                conversation_history=conversation_history,
                memory_store=self.conversation_memory,
                character_context=character_context
            )
            
            if analyzed:
                self.last_conversation_analysis = {
                    'suggestion': suggestion,
                    'analysis_turn': current_turn,
                    'timestamp': time.time()
                }
            
            return {
                'suggestion': suggestion,
                'analyzed': analyzed,
                'conversation_themes': self.conversation_memory.conversation_themes,
                'active_dynamics': self.conversation_memory.active_dynamics
            }
            
        except Exception as e:
            print(f"   ❌ CONVERSATION ANALYSIS ERROR: {e}")
            return None
    
    def get_conversation_context_for_prompt(self) -> str:
        """
        Get formatted conversation context for inclusion in roleplay prompts.
        """
        from .conversation_memory import format_conversation_for_context
        return format_conversation_for_context(self.conversation_memory, include_analysis=True)
    
    def has_conversation_memory(self) -> bool:
        """Check if we have conversation memory available."""
        return self.conversation_memory.has_sufficient_context()
    
    @property
    def current_mode(self) -> SessionMode:
        """Get the current session mode based on roleplay state."""
        
        if not self.is_roleplaying:
            return SessionMode.LISTENING
        elif self.is_dgm_session():
            return SessionMode.DGM_ROLEPLAY
        elif self.is_thread_based():
            return SessionMode.THREAD_ROLEPLAY
        else:
            return SessionMode.REGULAR_ROLEPLAY


# Global roleplay state manager instance
_roleplay_state = RoleplayStateManager()


def get_roleplay_state() -> RoleplayStateManager:
    """Get the global roleplay state manager."""
    return _roleplay_state 