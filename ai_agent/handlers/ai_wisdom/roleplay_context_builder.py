"""
Roleplay Context Builder - LLM-Powered Context Generation
=========================================================

This module builds roleplay context prompts using the content retriever and LLM processing.
"""

from typing import List, Dict, Any, Optional
from ..service_container import get_content_filter_service


class RoleplayContextBuilder:
    """
    Service class for building roleplay context prompts.
    
    This class provides a clean API for roleplay context generation while maintaining
    proper encapsulation and state management.
    """
    
    def __init__(self):
        """Initialize the roleplay context builder."""
        pass
    
    def build_context(self, user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
        """
        Build comprehensive roleplay context using the content retriever and LLM processing.
        
        Args:
            user_message: The user's message
            conversation_history: Recent conversation history
            character_context: Optional character context information
            
        Returns:
            Built roleplay context prompt
        """
        return build_roleplay_context(user_message, conversation_history, character_context)


def build_roleplay_context(user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
    """
    Build comprehensive roleplay context using the content retriever and LLM processing.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation history
        character_context: Optional character context information
        
    Returns:
        Built roleplay context prompt
    """
    # Get content filter service
    content_filter = get_content_filter_service()
    
    # Import content retriever to get relevant context
    from ..ai_wisdom.structured_content_retriever import get_structured_content_retriever
    content_retriever = get_structured_content_retriever()
    
    # Retrieve relevant content for roleplay
    retrieval_result = content_retriever.retrieve_content(user_message, "roleplay")
    
    # Check if this is a fallback response
    if content_filter.is_fallback_response(retrieval_result.get('content', '')):
        print("⚠️ ROLEPLAY CONTEXT: Fallback response detected from content retrieval")
        # Handle fallback scenario
        return _build_fallback_roleplay_context(user_message, conversation_history, character_context)
    
    # Build the full context prompt
    context_parts = []
    
    # Add character context if available
    if character_context:
        context_parts.append(f"Character Context: {character_context}")
    
    # Add retrieved content
    if retrieval_result.get('content'):
        context_parts.append(f"Relevant Content: {retrieval_result['content']}")
    
    # Add conversation history
    if conversation_history:
        recent_history = conversation_history[-5:]  # Last 5 messages
        context_parts.append(f"Recent Conversation: {' '.join(recent_history)}")
    
    # Add current message
    context_parts.append(f"Current Message: {user_message}")
    
    return "\n\n".join(context_parts)


def _build_fallback_roleplay_context(user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
    """
    Build a fallback roleplay context when content retrieval fails.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation history
        character_context: Optional character context information
        
    Returns:
        Fallback roleplay context
    """
    fallback_parts = []
    
    # Basic roleplay setup
    fallback_parts.append("Roleplay Context: Star Trek setting aboard the USS Stardancer")
    fallback_parts.append("Character: Elsie - Holographic bartender and stellar cartographer")
    
    # Add character context if available
    if character_context:
        fallback_parts.append(f"Additional Context: {character_context}")
    
    # Add recent conversation
    if conversation_history:
        recent_history = conversation_history[-3:]  # Last 3 messages for fallback
        fallback_parts.append(f"Recent Conversation: {' '.join(recent_history)}")
    
    # Add current message
    fallback_parts.append(f"Current Message: {user_message}")
    
    return "\n\n".join(fallback_parts)


# Legacy function for backward compatibility
def get_enhanced_roleplay_context(user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
    """
    Legacy function for backward compatibility.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation history
        character_context: Optional character context information
        
    Returns:
        Built roleplay context prompt
    """
    return build_roleplay_context(user_message, conversation_history, character_context) 