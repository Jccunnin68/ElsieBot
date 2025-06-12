"""
AI Act - Discord Bot Interface Layer
====================================

This module serves as the interface between the Discord bot and the AI logic.
It handles response delivery, channel context formatting, and Discord-specific operations.

Key Responsibilities:
- Process incoming Discord messages
- Format channel context for AI processing
- Handle response delivery and formatting
- Manage rate limiting and error handling
- Log interactions for monitoring
"""

import asyncio
import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from datetime import datetime

# Refactor complete - importing from new handler packages
from handlers.ai_coordinator import coordinate_response
from handlers.ai_emotion import detect_mock_personality_context
from handlers.handlers_utils import estimate_token_count


@dataclass
class ChannelContext:
    """Structured channel context for AI processing"""
    channel_id: str
    channel_name: str
    channel_type: str
    is_thread: bool
    is_dm: bool
    guild_id: Optional[str] = None
    thread_parent_id: Optional[str] = None
    permissions: Optional[Dict] = None


@dataclass
class MessageContext:
    """Complete context for message processing"""
    content: str
    author_id: str
    author_name: str
    timestamp: datetime
    channel_context: ChannelContext
    conversation_history: List[Dict] = None
    mentions: List[str] = None
    attachments: List[Dict] = None


class DiscordInterface:
    """
    Main interface class for Discord bot integration.
    
    This class provides a clean API for the Discord bot to interact with
    the AI agent while handling all the Discord-specific logic internally.
    """
    
    def __init__(self, rate_limit_per_minute: int = 30):
        self.rate_limit = rate_limit_per_minute
        self.message_timestamps = []
        self.logger = logging.getLogger(__name__)
        
    async def process_message(self, message_context: MessageContext) -> str:
        """
        Main entry point for processing Discord messages.
        
        Args:
            message_context: Complete message and channel context
            
        Returns:
            AI-generated response string
            
        Raises:
            RateLimitExceeded: If rate limit is exceeded
            ProcessingError: If message processing fails
        """
        try:
            # Check rate limiting
            if not self._check_rate_limit():
                return self._get_rate_limit_response()
            
            # Format context for AI processing
            ai_context = self._format_ai_context(message_context)
            
            # Process through AI coordinator (refactor complete)
            response = coordinate_response(
                message_context.content,
                message_context.conversation_history or [],
                ai_context
            )
            
            # Log interaction
            await self._log_interaction(message_context, response)
            
            # Format response for Discord
            formatted_response = self._format_discord_response(response)
            
            return formatted_response
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            
            # Try to provide a contextual fallback response based on personality
            try:
                personality_context = detect_mock_personality_context(message_context.content)
                if personality_context in ['stellar_cartographer', 'dance_instructor', 'bartender']:
                    return f"*adjusts {self._get_personality_prop(personality_context)} with practiced precision* " \
                           f"I'm experiencing some technical difficulties. Please try again in a moment."
                else:
                    return self._get_error_response()
            except:
                return self._get_error_response()
    
    def _format_ai_context(self, message_context: MessageContext) -> Dict[str, Any]:
        """
        Convert Discord-specific context into AI-friendly format.
        
        Args:
            message_context: Discord message context
            
        Returns:
            Dictionary formatted for AI processing
        """
        # Detect personality context for enhanced responses
        personality_context = detect_mock_personality_context(message_context.content)
        
        return {
            'session_id': message_context.channel_context.channel_id,
            'type': message_context.channel_context.channel_type,
            'is_thread': message_context.channel_context.is_thread,
            'is_dm': message_context.channel_context.is_dm,
            'name': message_context.channel_context.channel_name,
            'author': message_context.author_name,
            'timestamp': message_context.timestamp.isoformat(),
            'mentions': message_context.mentions or [],
            'has_attachments': bool(message_context.attachments),
            'personality_context': personality_context,
            'estimated_tokens': estimate_token_count(message_context.content)
        }
    
    def _format_discord_response(self, ai_response: str) -> str:
        """
        Format AI response for Discord delivery.
        
        Args:
            ai_response: Raw AI response
            
        Returns:
            Discord-formatted response
        """
        # Handle Discord message length limits (2000 characters)
        if len(ai_response) > 2000:
            # Split long messages
            return ai_response[:1997] + "..."
        
        # Handle Discord markdown conflicts
        # Escape any problematic characters that could break Discord formatting
        formatted_response = ai_response.replace("```", "\\`\\`\\`")
        
        return formatted_response
    
    def _check_rate_limit(self) -> bool:
        """
        Check if current request is within rate limits.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        now = datetime.now()
        # Remove timestamps older than 1 minute
        self.message_timestamps = [
            ts for ts in self.message_timestamps 
            if (now - ts).total_seconds() < 60
        ]
        
        if len(self.message_timestamps) >= self.rate_limit:
            return False
        
        self.message_timestamps.append(now)
        return True
    
    def _get_rate_limit_response(self) -> str:
        """Get response for rate-limited requests."""
        return ("⏳ I'm receiving a lot of messages right now. "
                "Please wait a moment before sending another message.")
    
    def _get_error_response(self) -> str:
        """Get response for processing errors."""
        return ("🔧 I'm experiencing some technical difficulties. "
                "Please try again in a moment.")
    
    def _get_personality_prop(self, personality_context: str) -> str:
        """Get appropriate prop for personality context."""
        props = {
            'stellar_cartographer': 'stellar cartography display',
            'dance_instructor': 'posture with graceful precision',
            'bartender': 'bottles behind the bar',
            'complete_self': 'display'
        }
        return props.get(personality_context, 'display')
    
    async def _log_interaction(self, message_context: MessageContext, response: str) -> None:
        """
        Log interaction for monitoring and analytics.
        
        Args:
            message_context: Original message context
            response: AI response
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'channel_id': message_context.channel_context.channel_id,
            'channel_type': message_context.channel_context.channel_type,
            'author_id': message_context.author_id,
            'message_length': len(message_context.content),
            'response_length': len(response),
            'is_thread': message_context.channel_context.is_thread,
            'is_dm': message_context.channel_context.is_dm
        }
        
        self.logger.info(f"Interaction logged: {log_data}")


class ResponseFormatter:
    """
    Utility class for formatting responses for Discord.
    
    Handles Discord-specific formatting, length limits, and markdown.
    """
    
    @staticmethod
    def split_long_message(message: str, max_length: int = 2000) -> List[str]:
        """
        Split long messages into Discord-compatible chunks.
        
        Args:
            message: Message to split
            max_length: Maximum length per chunk
            
        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs first
        paragraphs = message.split('\n\n')
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 <= max_length:
                if current_chunk:
                    current_chunk += '\n\n' + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = paragraph
                else:
                    # Paragraph is too long, split by sentences
                    sentences = paragraph.split('. ')
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 2 <= max_length:
                            if current_chunk:
                                current_chunk += '. ' + sentence
                            else:
                                current_chunk = sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    @staticmethod
    def escape_discord_markdown(text: str) -> str:
        """
        Escape Discord markdown characters to prevent formatting conflicts.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text
        """
        # Escape Discord markdown characters
        escape_chars = ['*', '_', '`', '~', '|', '\\']
        for char in escape_chars:
            text = text.replace(char, '\\' + char)
        
        return text


# Convenience functions for Discord bot integration
async def process_discord_message(
    content: str,
    channel_data: Dict,
    author_data: Dict,
    conversation_history: List[Dict] = None
) -> str:
    """
    Convenience function for processing Discord messages.
    
    Args:
        content: Message content
        channel_data: Discord channel information
        author_data: Discord author information
        conversation_history: Previous conversation messages
        
    Returns:
        AI response string
    """
    # Create context objects
    channel_context = ChannelContext(
        channel_id=channel_data.get('id', ''),
        channel_name=channel_data.get('name', 'unknown'),
        channel_type=channel_data.get('type', 'text'),
        is_thread=channel_data.get('is_thread', False),
        is_dm=channel_data.get('is_dm', False),
        guild_id=channel_data.get('guild_id'),
        thread_parent_id=channel_data.get('parent_id')
    )
    
    message_context = MessageContext(
        content=content,
        author_id=author_data.get('id', ''),
        author_name=author_data.get('name', 'Unknown'),
        timestamp=datetime.now(),
        channel_context=channel_context,
        conversation_history=conversation_history or []
    )
    
    # Process through interface
    interface = DiscordInterface()
    response = await interface.process_message(message_context)
    
    return response


def format_for_discord(response: str) -> List[str]:
    """
    Format response for Discord delivery.
    
    Args:
        response: AI response
        
    Returns:
        List of Discord-ready message chunks
    """
    formatter = ResponseFormatter()
    return formatter.split_long_message(response) 