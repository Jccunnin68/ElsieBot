"""
Roleplay State Manager
=====================

Manages the state of ongoing roleplay sessions, including participant tracking,
turn management, and conversation flow logic.
"""

from typing import Dict, List, Optional
from .character_tracking import extract_current_speaker, is_valid_character_name


class RoleplayStateManager:
    """
    Context & State Manager for roleplay sessions.
    Maintains speaker permanence and roleplay context.
    Enhanced with passive listening and channel restrictions.
    Now supports DGM-initiated sessions with special behavior.
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
        
        # Simple implicit response tracking
        self.last_character_elsie_addressed = ""  # Who did Elsie last speak to
        self.last_character_spoke = ""  # Who spoke last (not Elsie)
        self.turn_history = []  # Simple turn tracking: [(turn_number, speaker)]
    
    def start_roleplay_session(self, turn_number: int, initial_triggers: List[str], channel_context: Dict = None, dgm_characters: List[str] = None):
        """Initialize a new roleplay session."""
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
        
        # Reset simple tracking
        self.last_character_elsie_addressed = ""
        self.last_character_spoke = ""
        self.turn_history = []
        
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
        print(f"   📍 Channel: {channel_context}")
        print(f"   🎬 DGM Initiated: {self.dgm_initiated}")
        print(f"   🧵 Thread Session: {self.is_thread_session}")
        if self.dgm_characters:
            print(f"   👥 DGM Characters: {self.dgm_characters}")
        print(f"   🎮 State: {'DGM PASSIVE MONITORING' if self.dgm_initiated else 'ACTIVE MONITORING'}")
    
    def add_participant(self, name: str, source: str, turn_number: int):
        """Add a new participant to the roleplay session."""
        # Normalize the name for comparison (handle case variations)
        name_normalized = name.strip()
        
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
    
    def set_last_character_addressed(self, character_name: str):
        """Set who Elsie last addressed."""
        self.last_character_elsie_addressed = character_name
        print(f"   👋 ELSIE ADDRESSED: {character_name}")
    
    def is_simple_implicit_response(self, current_turn: int, user_message: str) -> bool:
        """
        SIMPLE implicit response logic:
        - If the response comes from the last character Elsie addressed
        - AND Elsie spoke on the previous turn (not necessarily the last in history)
        - UNLESS the message contains other character names (redirecting conversation)
        """
        # Check if we have any turn history
        if not self.turn_history:
            return False
        
        # Find the most recent turn where Elsie spoke
        elsie_last_turn = None
        for turn_num, speaker in reversed(self.turn_history):
            if speaker == "Elsie":
                elsie_last_turn = turn_num
                break
        
        # Check if Elsie spoke recently (within 2 turns of current)
        if not elsie_last_turn or current_turn - elsie_last_turn > 2:
            return False
        
        # Extract character name from current message
        current_character = extract_current_speaker(user_message)
        if not current_character:
            return False
        
        # Check if this character is the one Elsie last addressed
        if (self.last_character_elsie_addressed and 
            current_character.lower() == self.last_character_elsie_addressed.lower()):
            
            # Check if the message contains other character names (redirecting)
            if self._message_contains_other_character_names(user_message):
                print(f"   🎯 Message contains other character names - not an implicit response")
                return False
            
            print(f"   💬 SIMPLE IMPLICIT RESPONSE DETECTED:")
            print(f"      - Elsie last addressed: {self.last_character_elsie_addressed}")
            print(f"      - Current speaker: {current_character}")
            print(f"      - Turn history: {self.turn_history[-3:] if len(self.turn_history) >= 3 else self.turn_history}")
            print(f"      - This is a follow-up from the character Elsie was addressing")
            
            return True
        
        return False
    
    def _message_contains_other_character_names(self, user_message: str) -> bool:
        """
        Check if the message contains character names that would indicate
        it's directed at someone other than Elsie.
        NOTE: Ignores speaker brackets [Character Name] since those indicate who is speaking, not being addressed.
        """
        # Import here to avoid circular imports
        from .character_tracking import extract_character_names_from_emotes, extract_addressed_characters
        
        # Extract speaker from bracket format [Character Name] - this should be ignored
        speaker_from_bracket = extract_current_speaker(user_message)
        
        # Check for character names in emotes and addressing patterns
        character_names = extract_character_names_from_emotes(user_message)
        addressed_characters = extract_addressed_characters(user_message)
        
        # Combine all detected character names
        all_detected_names = set(character_names + addressed_characters)
        
        # Filter out Elsie's names (these are fine for implicit responses)
        elsie_names = {'elsie', 'elise', 'elsy', 'els', 'bartender', 'barkeep', 'barmaid', 'server', 'waitress'}
        
        # Filter out the speaker (from brackets) since that's who is talking, not being addressed
        other_character_names = [name for name in all_detected_names 
                               if (name.lower() not in elsie_names and 
                                   is_valid_character_name(name) and
                                   name.lower() != speaker_from_bracket.lower())]
        
        if other_character_names:
            print(f"      🎯 Other character names detected (excluding speaker '{speaker_from_bracket}'): {other_character_names}")
            return True
        
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
        """Track confidence scores to detect sustained topic shifts."""
        self.confidence_history.append(confidence_score)
        # Keep only last 5 scores
        if len(self.confidence_history) > 5:
            self.confidence_history.pop(0)
    
    def check_sustained_topic_shift(self) -> bool:
        """Check if there's been a sustained shift away from roleplay."""
        if len(self.confidence_history) < 3:
            return False
        
        # If last 3 scores are all below threshold, it's a sustained shift
        recent_scores = self.confidence_history[-3:]
        return all(score < 0.15 for score in recent_scores)
    
    def increment_exit_condition(self):
        """Increment exit condition counter."""
        self.exit_condition_count += 1
    
    def should_exit_from_sustained_shift(self) -> bool:
        """Determine if we should exit due to sustained non-RP behavior."""
        return (self.check_sustained_topic_shift() or 
                self.exit_condition_count >= 2)
    
    def end_roleplay_session(self, reason: str):
        """End the current roleplay session."""
        print(f"   🎭 ROLEPLAY SESSION ENDED - Reason: {reason}")
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
            'is_thread_session': self.is_thread_session
        }


# Global roleplay state manager instance
_roleplay_state = RoleplayStateManager()


def get_roleplay_state() -> RoleplayStateManager:
    """Get the global roleplay state manager."""
    return _roleplay_state 