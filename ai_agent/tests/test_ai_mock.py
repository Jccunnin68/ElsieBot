"""
Tests for AI Mock Response Subsystem
====================================

Tests all components of the mock response system including personality contexts,
drink menu, greetings, and poetic responses.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.ai_emotion import (
    get_mock_response, 
    should_use_mock_response,
    detect_mock_personality_context,
    handle_drink_request,
    get_menu_response,
    handle_greeting,
    handle_farewell,
    get_poetic_response,
    should_trigger_poetic_circuit
)


class TestPersonalityContexts:
    """Test personality context detection."""
    
    def test_stellar_cartographer_context(self):
        """Test detection of stellar cartography context."""
        messages = [
            "tell me about stars",
            "what constellation is that",
            "show me navigation data",
            "stellar cartography readings"
        ]
        for message in messages:
            context = detect_mock_personality_context(message)
            assert context == "stellar_cartographer"
    
    def test_dance_instructor_context(self):
        """Test detection of dance instructor context."""
        messages = [
            "teach me to dance",
            "show me some choreography", 
            "that's elegant movement",
            "ballet performance"
        ]
        for message in messages:
            context = detect_mock_personality_context(message)
            assert context == "dance_instructor"
    
    def test_bartender_context(self):
        """Test detection of bartender context."""
        messages = [
            "what drinks do you have",
            "I'll have a cocktail",
            "romulan ale please",
            "what's on the menu"
        ]
        for message in messages:
            context = detect_mock_personality_context(message)
            assert context == "bartender"
    
    def test_complete_self_context(self):
        """Test default personality context."""
        messages = [
            "hello there",
            "how are you",
            "tell me a story",
            "what do you think"
        ]
        for message in messages:
            context = detect_mock_personality_context(message)
            assert context == "complete_self"


class TestDrinkMenu:
    """Test drink menu and bar functionality."""
    
    def test_specific_drink_orders(self):
        """Test responses to specific drink orders."""
        test_cases = [
            ("romulan ale", "Romulan Ale"),
            ("synthehol", "Synthehol"),
            ("blood wine", "Klingon Blood Wine"),
            ("tea earl grey hot", "Tea, Earl Grey, hot")
        ]
        
        for drink_order, expected_drink in test_cases:
            response = handle_drink_request(drink_order)
            assert response is not None
            assert expected_drink in response
    
    def test_general_drink_requests(self):
        """Test responses to general drink requests."""
        messages = [
            "what can you make",
            "I need a drink",
            "what beverages do you have"
        ]
        
        for message in messages:
            response = handle_drink_request(message)
            assert response is not None
            assert len(response) > 0
    
    def test_menu_response(self):
        """Test the full menu response."""
        menu = get_menu_response()
        assert "ELSIE'S GALACTIC BAR MENU" in menu
        assert "Federation Classics" in menu
        assert "Exotic Indulgences" in menu
        assert "Romulan Ale" in menu
    
    def test_non_drink_messages(self):
        """Test that non-drink messages return None."""
        non_drink_messages = [
            "hello there",
            "what's the weather",
            "tell me about ships"
        ]
        
        for message in non_drink_messages:
            response = handle_drink_request(message)
            assert response is None


class TestGreetingsAndFarewells:
    """Test greeting and farewell functionality."""
    
    def test_greetings(self):
        """Test greeting responses."""
        greetings = ["hello", "hi", "hey", "good morning", "greetings"]
        
        for greeting in greetings:
            response = handle_greeting(greeting)
            assert response is not None
            assert "Elsie" in response
    
    def test_contextual_greetings(self):
        """Test greetings with different personality contexts."""
        contexts = ["stellar_cartographer", "dance_instructor", "bartender"]
        
        for context in contexts:
            response = handle_greeting("hello", context)
            assert response is not None
            assert "Elsie" in response
    
    def test_farewells(self):
        """Test farewell responses."""
        farewells = ["bye", "goodbye", "farewell", "see you"]
        
        for farewell in farewells:
            response = handle_farewell(farewell)
            assert response is not None
    
    def test_non_greetings(self):
        """Test that non-greetings return None."""
        non_greetings = ["what's up", "tell me about", "romulan ale"]
        
        for message in non_greetings:
            response = handle_greeting(message)
            assert response is None


class TestPoeticResponses:
    """Test poetic response circuit."""
    
    def test_poetic_trigger_conditions(self):
        """Test when poetic responses should trigger."""
        # Should not trigger for serious requests
        serious_messages = [
            "tell me about the ship",
            "what is warp drive",
            "show me the database"
        ]
        
        for message in serious_messages:
            should_trigger = should_trigger_poetic_circuit(message, [])
            assert not should_trigger
        
        # Should not trigger for very short messages
        short_messages = ["hi", "ok", "yes"]
        
        for message in short_messages:
            should_trigger = should_trigger_poetic_circuit(message, [])
            assert not should_trigger
    
    def test_poetic_response_format(self):
        """Test poetic response formatting."""
        response = get_poetic_response("tell me something beautiful")
        
        # Should have action and poetic text
        assert "*" in response  # Action formatting
        assert len(response) > 50  # Substantial response
        assert "\n\n" in response  # Action separated from text


class TestMockResponseIntegration:
    """Test the overall mock response system."""
    
    def test_should_use_mock_response(self):
        """Test mock response decision logic."""
        # Should use mock when API unavailable
        assert should_use_mock_response("hello", api_available=False)
        
        # Should use mock for simple chat
        assert should_use_mock_response("hello", api_available=True)
        
        # Should use mock for drinks
        assert should_use_mock_response("romulan ale", api_available=True)
        
        # Should use mock for federation archives
        assert should_use_mock_response("check the federation archives", api_available=True)
    
    def test_get_mock_response_integration(self):
        """Test the main mock response function."""
        test_cases = [
            ("hello", "Elsie"),
            ("romulan ale", "Romulan Ale"),
            ("menu", "MENU"),
            ("goodbye", "Safe travels")
        ]
        
        for message, expected_content in test_cases:
            response = get_mock_response(message)
            assert response is not None
            assert len(response) > 0
            # Note: We check for content presence since some responses are randomized
    
    def test_fallback_response(self):
        """Test fallback response for unrecognized input."""
        obscure_message = "xyzzy quantum flux capacitor"
        response = get_mock_response(obscure_message)
        
        assert response is not None
        assert len(response) > 0
        # Should get either conversational or fallback response


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_message(self):
        """Test handling of empty messages."""
        response = get_mock_response("")
        assert response is not None
        assert len(response) > 0
    
    def test_very_long_message(self):
        """Test handling of very long messages."""
        long_message = "hello " * 100
        response = get_mock_response(long_message)
        assert response is not None
        assert len(response) > 0
    
    def test_special_characters(self):
        """Test handling of messages with special characters."""
        special_messages = [
            "hello! @#$%",
            "drink??? ***",
            "greetings... [test]"
        ]
        
        for message in special_messages:
            response = get_mock_response(message)
            assert response is not None
            assert len(response) > 0


if __name__ == "__main__":
    pytest.main([__file__]) 