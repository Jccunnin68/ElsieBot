"""
Tests for ai_logic.py functionality
==================================

Tests intent detection, guard rails, conversation flow management, and all utility functions.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_logic import (
    convert_earth_date_to_star_trek,
    is_continuation_request,
    is_federation_archives_request,
    extract_continuation_focus,
    is_specific_log_request,
    is_stardancer_query,
    is_stardancer_command_query,
    extract_tell_me_about_subject,
    is_ooc_query,
    extract_ooc_log_url_request,
    extract_ship_log_query,
    is_character_query,
    get_query_type,
    detect_topic_change,
    format_conversation_history,
    detect_roleplay_triggers,
    is_roleplay_allowed_channel,
    extract_addressed_characters,
    is_valid_character_name,
    extract_character_names_from_emotes,
    detect_roleplay_exit_conditions,
    RoleplayStateManager
)


class TestDateConversion:
    """Test Earth date to Star Trek date conversion"""
    
    def test_convert_year_before_2024(self):
        result = convert_earth_date_to_star_trek("2023")
        assert "2427" in result
        
    def test_convert_year_after_2024(self):
        result = convert_earth_date_to_star_trek("2025")
        assert "2455" in result
        
    def test_convert_full_date(self):
        result = convert_earth_date_to_star_trek("March 15, 2023")
        assert "2427" in result


class TestIntentDetection:
    """Test various intent detection functions"""
    
    def test_continuation_request(self):
        assert is_continuation_request("yes")
        assert is_continuation_request("tell me more")
        assert is_continuation_request("continue")
        assert not is_continuation_request("what is a ship")
        
    def test_federation_archives_request(self):
        assert is_federation_archives_request("check the federation archives")
        assert is_federation_archives_request("search federation archives")
        assert not is_federation_archives_request("tell me about ships")
        
    def test_specific_log_request(self):
        assert is_specific_log_request("show me the log")
        assert is_specific_log_request("mission log")
        assert not is_specific_log_request("tell me about ships")
        
    def test_stardancer_query(self):
        assert is_stardancer_query("tell me about the stardancer")
        assert is_stardancer_query("our ship")
        assert not is_stardancer_query("tell me about the enterprise")
        
    def test_character_query(self):
        is_char, name = is_character_query("tell me about Captain Smith")
        assert is_char
        assert name == "Captain Smith"
        
        is_char, name = is_character_query("what about the USS Enterprise")
        assert not is_char  # Should not detect ship names as characters


class TestOOCHandling:
    """Test Out-of-Character query handling"""
    
    def test_ooc_query_detection(self):
        is_ooc, query = is_ooc_query("OOC: link me the log")
        assert is_ooc
        assert "link me the log" in query
        
    def test_ooc_url_request(self):
        is_url, query = extract_ooc_log_url_request("OOC: link me the log page for the last stardancer")
        assert is_url
        assert "stardancer" in query.lower()


class TestRoleplayDetection:
    """Test roleplay detection and management"""
    
    def test_detect_roleplay_triggers(self):
        # Test emote detection
        is_rp, confidence, triggers = detect_roleplay_triggers("*walks into the bar*")
        assert is_rp
        assert "emotes" in triggers
        
        # Test character brackets
        is_rp, confidence, triggers = detect_roleplay_triggers("[John Smith] walks forward")
        assert is_rp
        assert "character_brackets" in triggers
        
    def test_channel_restrictions(self):
        # Thread should be allowed
        channel_context = {"is_thread": True, "type": "public_thread"}
        assert is_roleplay_allowed_channel(channel_context)
        
        # General channel should be blocked
        channel_context = {"is_thread": False, "type": "text", "name": "general"}
        assert not is_roleplay_allowed_channel(channel_context)


class TestCharacterExtraction:
    """Test character name extraction functions"""
    
    def test_extract_character_names_from_emotes(self):
        names = extract_character_names_from_emotes("*John walks over to Sarah*")
        assert "John" in names
        assert "Sarah" in names
        
    def test_extract_addressed_characters(self):
        names = extract_addressed_characters("Hey John, what do you think?")
        assert "John" in names
        
    def test_valid_character_name(self):
        assert is_valid_character_name("John")
        assert is_valid_character_name("Sarah Smith")
        assert not is_valid_character_name("the")
        assert not is_valid_character_name("and")


class TestConversationFlow:
    """Test conversation management functions"""
    
    def test_topic_change_detection(self):
        history = [
            {"role": "user", "content": "tell me about ships"},
            {"role": "assistant", "content": "Ships are vessels..."}
        ]
        
        # Same topic
        assert not detect_topic_change("what about starships", history)
        
        # Different topic
        assert detect_topic_change("tell me about characters", history)
        
    def test_format_conversation_history(self):
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"}
        ]
        
        formatted = format_conversation_history(history, False)
        assert "Customer: hello" in formatted
        assert "Elsie: hi there" in formatted


class TestRoleplayStateManager:
    """Test RoleplayStateManager functionality"""
    
    def setup_method(self):
        self.rp_state = RoleplayStateManager()
        
    def test_start_roleplay_session(self):
        self.rp_state.start_roleplay_session(1, ["emotes"], {"is_thread": True})
        assert self.rp_state.is_roleplaying
        assert self.rp_state.session_start_turn == 1
        
    def test_add_participant(self):
        self.rp_state.start_roleplay_session(1, ["emotes"])
        self.rp_state.add_participant("John", "emote", 2)
        
        participants = self.rp_state.get_participant_names()
        assert "John" in participants
        
    def test_listening_mode(self):
        self.rp_state.set_listening_mode(True, "multi-character scene")
        assert self.rp_state.listening_mode
        
    def test_implicit_response_tracking(self):
        self.rp_state.start_roleplay_session(1, ["emotes"])
        self.rp_state.set_last_character_addressed("John")
        
        # Mock a simple implicit response scenario
        self.rp_state.mark_response_turn(2)
        self.rp_state.mark_character_turn(3, "John")
        
        # Test if this would be detected as implicit response
        # (This is a simplified test - the actual logic is more complex)
        assert self.rp_state.last_character_elsie_addressed == "John"


class TestUtilityFunctions:
    """Test utility and helper functions"""
    
    def test_extract_tell_me_about_subject(self):
        subject = extract_tell_me_about_subject("tell me about ships")
        assert subject == "ships"
        
        subject = extract_tell_me_about_subject("hello")
        assert subject is None
        
    def test_get_query_type(self):
        assert get_query_type("yes") == "continuation"
        assert get_query_type("tell me about ships") == "tell_me_about"
        assert get_query_type("OOC: help") == "ooc"


if __name__ == "__main__":
    pytest.main([__file__]) 