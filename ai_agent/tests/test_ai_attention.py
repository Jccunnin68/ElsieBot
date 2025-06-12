"""
Tests for AI Attention - Roleplay State Management
==================================================

Tests all components of the roleplay detection and state management system.
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from handlers.ai_attention import (
    detect_roleplay_triggers,
    check_dgm_post,
    is_roleplay_allowed_channel,
    extract_character_names_from_emotes,
    detect_roleplay_exit_conditions,
    is_valid_character_name
)


class TestRoleplayDetection:
    """Test roleplay trigger detection."""
    
    def test_character_brackets_detection(self):
        """Test detection of character name brackets."""
        message = "[Fallo] *walks into the room* Hello everyone."
        is_rp, confidence, triggers = detect_roleplay_triggers(message)
        
        assert is_rp == True
        assert confidence >= 0.7  # High confidence for character brackets
        assert "character_brackets" in triggers
    
    def test_emote_detection(self):
        """Test detection of emotes."""
        message = "*sits down at the bar* Can I get a drink?"
        is_rp, confidence, triggers = detect_roleplay_triggers(message)
        
        assert is_rp == True
        assert confidence >= 0.6  # High confidence for emotes
        assert "emotes" in triggers
    
    def test_quoted_dialogue_detection(self):
        """Test detection of quoted dialogue."""
        message = '"Hello there," she said with a smile.'
        is_rp, confidence, triggers = detect_roleplay_triggers(message)
        
        assert confidence > 0.0  # Should get some confidence
        assert "quoted_dialogue" in triggers
    
    def test_thread_context_bonus(self):
        """Test thread context gives confidence bonus."""
        message = "The character walks into the room"
        channel_context = {'is_thread': True, 'type': 'public_thread'}
        
        is_rp, confidence, triggers = detect_roleplay_triggers(message, channel_context)
        
        # Should get thread bonus
        assert "thread_context" in triggers or "thread_rp_pattern" in triggers
    
    def test_non_roleplay_message(self):
        """Test that non-roleplay messages aren't detected."""
        message = "What's the weather like today?"
        is_rp, confidence, triggers = detect_roleplay_triggers(message)
        
        assert is_rp == False
        assert confidence < 0.25  # Below threshold
    
    def test_channel_restrictions(self):
        """Test that roleplay is blocked in restricted channels."""
        message = "*does something roleplay-like*"
        channel_context = {'type': 'general', 'is_thread': False, 'is_dm': False}
        
        is_rp, confidence, triggers = detect_roleplay_triggers(message, channel_context)
        
        # Should be blocked due to channel restrictions
        assert "channel_restricted" in triggers


class TestDGMPosts:
    """Test DGM (Deputy Game Master) post detection."""
    
    def test_dgm_scene_setting(self):
        """Test DGM scene setting detection."""
        message = "[DGM] The ship's bridge is busy with activity. Fallo and Maeve are present."
        result = check_dgm_post(message)
        
        assert result['is_dgm'] == True
        assert result['action'] == 'set_scene'
        assert result['triggers_roleplay'] == True
        assert 'Fallo' in result['characters']
        assert 'Maeve' in result['characters']
    
    def test_dgm_controlled_elsie(self):
        """Test DGM-controlled Elsie post detection."""
        message = "[DGM][Elsie] *adjusts the lighting* The bar is ready for customers."
        result = check_dgm_post(message)
        
        assert result['is_dgm'] == True
        assert result['action'] == 'dgm_controlled_elsie'
        assert result['dgm_controlled_elsie'] == True
        assert result['elsie_content'] == "*adjusts the lighting* The bar is ready for customers."
    
    def test_dgm_scene_ending(self):
        """Test DGM scene ending detection."""
        message = "[DGM] *end scene*"
        result = check_dgm_post(message)
        
        assert result['is_dgm'] == True
        assert result['action'] == 'end_scene'
        assert result['triggers_roleplay'] == False
    
    def test_non_dgm_message(self):
        """Test that non-DGM messages aren't detected."""
        message = "Just a regular message"
        result = check_dgm_post(message)
        
        assert result['is_dgm'] == False


class TestChannelRestrictions:
    """Test channel restriction logic."""
    
    def test_dm_allowed(self):
        """Test that DMs allow roleplay."""
        channel_context = {'is_dm': True}
        assert is_roleplay_allowed_channel(channel_context) == True
    
    def test_thread_allowed(self):
        """Test that threads allow roleplay."""
        channel_context = {'is_thread': True}
        assert is_roleplay_allowed_channel(channel_context) == True
    
    def test_discord_thread_types_allowed(self):
        """Test that Discord thread types allow roleplay."""
        thread_types = ['public_thread', 'private_thread', 'news_thread']
        
        for thread_type in thread_types:
            channel_context = {'type': thread_type}
            assert is_roleplay_allowed_channel(channel_context) == True
    
    def test_no_context_fallback(self):
        """Test fallback when no context is provided."""
        assert is_roleplay_allowed_channel(None) == True


class TestCharacterNameExtraction:
    """Test character name extraction from messages."""
    
    def test_bracket_format_extraction(self):
        """Test extraction from [Character Name] format."""
        message = "[Fallo] *walks in* [Maeve] follows behind."
        names = extract_character_names_from_emotes(message)
        
        assert 'Fallo' in names
        assert 'Maeve' in names
    
    def test_emote_name_extraction(self):
        """Test extraction from emote content."""
        message = "*John approaches the bar* *Mary waves*"
        names = extract_character_names_from_emotes(message)
        
        assert 'John' in names
        assert 'Mary' in names
    
    def test_invalid_names_filtered(self):
        """Test that invalid names are filtered out."""
        message = "*the person walks* *and does something*"
        names = extract_character_names_from_emotes(message)
        
        # Should not include common words
        assert 'the' not in names
        assert 'and' not in names


class TestCharacterNameValidation:
    """Test character name validation."""
    
    def test_valid_names(self):
        """Test that valid names pass validation."""
        valid_names = ['Fallo', 'Maeve', 'Alexander', 'Commander']
        
        for name in valid_names:
            assert is_valid_character_name(name) == True
    
    def test_invalid_names(self):
        """Test that invalid names fail validation."""
        invalid_names = ['the', 'and', 'you', 'me', 'us', 'a']
        
        for name in invalid_names:
            assert is_valid_character_name(name) == False
    
    def test_short_names(self):
        """Test that very short names are rejected."""
        short_names = ['a', 'an', 'it']
        
        for name in short_names:
            assert is_valid_character_name(name) == False


class TestRoleplayExitConditions:
    """Test roleplay exit condition detection."""
    
    def test_explicit_exit_commands(self):
        """Test explicit roleplay exit commands."""
        exit_commands = [
            'stop roleplay',
            'exit character',
            'end roleplay',
            'break character'
        ]
        
        for command in exit_commands:
            should_exit, reason = detect_roleplay_exit_conditions(command)
            assert should_exit == True
            assert reason == "explicit_command"
    
    def test_ooc_brackets(self):
        """Test OOC (Out of Character) bracket detection."""
        ooc_messages = [
            '((This is out of character))',
            '// OOC comment',
            '[ooc: just checking something]',
            'ooc: quick question'
        ]
        
        for message in ooc_messages:
            should_exit, reason = detect_roleplay_exit_conditions(message)
            assert should_exit == True
            assert reason == "ooc_brackets"
    
    def test_technical_queries(self):
        """Test technical query detection."""
        technical_messages = [
            'write a python script',
            'how do I install this',
            'what is the definition of',
            'debug this error'
        ]
        
        for message in technical_messages:
            should_exit, reason = detect_roleplay_exit_conditions(message)
            assert should_exit == True
            assert reason == "technical_query"
    
    def test_normal_roleplay_continues(self):
        """Test that normal roleplay messages don't trigger exit."""
        normal_messages = [
            '*walks into the room*',
            '"Hello there," she said.',
            '[Fallo] approaches the bar.'
        ]
        
        for message in normal_messages:
            should_exit, reason = detect_roleplay_exit_conditions(message)
            assert should_exit == False


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_message(self):
        """Test handling of empty messages."""
        is_rp, confidence, triggers = detect_roleplay_triggers("")
        
        assert is_rp == False
        assert confidence == 0.0
    
    def test_very_long_message(self):
        """Test handling of very long messages."""
        long_message = "Hello " * 1000 + "*does something*"
        is_rp, confidence, triggers = detect_roleplay_triggers(long_message)
        
        # Should still detect roleplay patterns
        assert "emotes" in triggers
    
    def test_special_characters(self):
        """Test handling of messages with special characters."""
        special_message = "*walks @#$% into the room!!! 🎭*"
        is_rp, confidence, triggers = detect_roleplay_triggers(special_message)
        
        assert "emotes" in triggers


if __name__ == "__main__":
    pytest.main([__file__]) 