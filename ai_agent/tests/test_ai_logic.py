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

from handlers.ai_logic.query_detection import (
    is_continuation_request,
    is_federation_archives_request,
    extract_url_request,
    extract_tell_me_about_subject,
    is_character_query,
    get_query_type
)
from handlers.handlers_utils import convert_earth_date_to_star_trek
from handlers.ai_attention import (
    
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
        

        
    def test_character_query(self):
        is_char, name = is_character_query("tell me about Captain Smith")
        assert is_char
        assert name == "Smith"  # Character detection extracts the last name
        
        is_char, name = is_character_query("what about the USS Enterprise")
        assert not is_char  # Should not detect ship names as characters


class TestURLHandling:
    """Test URL request handling (formerly OOC URL requests)"""
    
    def test_url_request_detection(self):
        is_url, query = extract_url_request("link me the log page for the last stardancer")
        assert is_url
        assert "stardancer" in query.lower()
        
    def test_url_request_various_patterns(self):
        is_url, query = extract_url_request("get me the URL for enterprise logs")
        assert is_url
        assert "enterprise" in query.lower()


class TestQueryTypeDetection:
    """Test query type detection after OOC refactor"""
    
    def test_url_request_detection(self):
        """Test that URL requests are properly detected as url_request type"""
        assert get_query_type("link me the log page") == "url_request"
        assert get_query_type("get me the URL for something") == "url_request"
        
    def test_other_query_types(self):
        """Test that other query types still work correctly"""
        assert get_query_type("yes") == "continuation"
        assert get_query_type("tell me about ships") == "tell_me_about"
        assert get_query_type("tell me about Captain Smith") == "character"


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


if __name__ == "__main__":
    pytest.main([__file__]) 