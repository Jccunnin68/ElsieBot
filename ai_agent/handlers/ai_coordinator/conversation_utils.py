"""
Conversation Utilities 
=================================

This module contains utilities for managing conversation history and topic changes.
"""

from handlers.ai_logic.query_detection import (
    is_continuation_request,
    extract_tell_me_about_subject,
    get_query_type
)
from handlers.ai_attention import check_dgm_post

def detect_topic_change(user_message: str, conversation_history: list) -> bool:
    """
    Detect if the current message represents a topic change from previous conversation.
    Returns True if this is a new topic that should break continuity.
    Enhanced to allow follow-up questions and detect explicit reset requests.
    """
    if not conversation_history:
        return True  # First message is always a new topic
    
    current_message = user_message.lower().strip()
    
    # Check for explicit conversation reset phrases
    reset_phrases = [
        "let's talk about something else",
        "lets talk about something else", 
        "change the subject",
        "something different",
        "new topic",
        "talk about something different"
    ]
    
    if any(phrase in current_message for phrase in reset_phrases):
        print("🔄 Explicit topic reset detected")
        return True
    
    # Get the last user message for comparison
    last_user_messages = [msg for msg in conversation_history if msg["role"] == "user"]
    if not last_user_messages:
        return True
    
    last_user_message = last_user_messages[-1]["content"].lower().strip()
    
    # Follow-up question indicators that should NOT break continuity
    followup_indicators = [
        'what about', 'how about', 'what else', 'tell me more', 'more about',
        'and what', 'what other', 'any other', 'also', 'additionally',
        'what was', 'what were', 'when did', 'where did', 'how did',
        'can you elaborate', 'more details', 'more information',
        'what happened to', 'what about their', 'what about his', 'what about her'
    ]
    
    # Check if this is a follow-up question or continuation request
    is_followup = any(current_message.startswith(indicator) for indicator in followup_indicators)
    is_continuation = is_continuation_request(user_message)
    
    if is_followup or is_continuation:
        print("🔗 Follow-up question or continuation detected - maintaining context")
        return False
    
    # Question starters that might indicate a new topic (but not always)
    potential_new_topic_indicators = [
        'tell me about', 'what is', 'what are', 'who is', 'who are', 
        'how does', 'how do', 'why', 'when', 'where', 'show me',
        'explain', 'describe', 'ooc', 'summarize', 'what happened',
        'can you', 'could you', 'would you', 'retrieve'
    ]
    
    # Check if this is a different type of query
    current_query_type = get_query_type(user_message)
    last_query_type = get_query_type(last_user_messages[-1]["content"])
    
    # For "tell me about" queries, check if it's about the same subject
    if current_query_type == "tell_me_about" and last_query_type == "tell_me_about":
        current_subject = extract_tell_me_about_subject(user_message)
        last_subject = extract_tell_me_about_subject(last_user_messages[-1]["content"])
        
        if current_subject and last_subject:
            # Check if subjects are similar (allow for variations like "ship" vs "USS ship")
            if (current_subject in last_subject or last_subject in current_subject or
                any(word in current_subject.split() for word in last_subject.split() if len(word) > 3)):
                print(f"🔗 Same subject detected: '{current_subject}' similar to '{last_subject}' - maintaining context")
                return False
    
    # Check for keyword similarity to detect if it's about the same subject
    current_keywords = set(current_message.split())
    last_keywords = set(last_user_message.split())
    
    # Remove common words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'me', 'you', 'can', 'could', 'would', 'should', 'tell', 'about', 'what', 'who'}
    current_keywords -= common_words
    last_keywords -= common_words
    
    # If there's reasonable keyword overlap, it's likely the same topic
    if current_keywords and last_keywords:
        overlap = len(current_keywords.intersection(last_keywords))
        total_unique = len(current_keywords.union(last_keywords))
        similarity = overlap / total_unique if total_unique > 0 else 0
        
        # More lenient similarity check - 20% overlap suggests same topic
        if similarity >= 0.2:
            print(f"🔗 Topic similarity detected ({similarity:.2%}) - maintaining context")
            return False
    
    # Different query types usually indicate topic change (unless it's a follow-up)
    if current_query_type != last_query_type:
        print(f"🔄 Query type change: {last_query_type} -> {current_query_type}")
        return True
    
    # If current message starts with a strong new topic indicator and we haven't caught it yet
    current_starts_new_topic = any(current_message.startswith(indicator) for indicator in potential_new_topic_indicators)
    if current_starts_new_topic and similarity < 0.1:  # Very low similarity + new topic starter
        print("🔄 New topic starter with low similarity - breaking context")
        return True
    
    # For very short messages like "hello", "hi", "how are you", maintain context unless it's the first message
    if len(current_message.split()) <= 3 and not any(current_message.startswith(indicator) for indicator in potential_new_topic_indicators):
        print("🔗 Short casual message - maintaining context for natural conversation flow")
        return False
    
    # Default to maintaining context for ambiguous cases
    print("🔗 Ambiguous case - maintaining context")
    return False


def format_conversation_history(conversation_history: list, is_topic_change: bool) -> str:
    """Format conversation history, expanding context for follow-up questions"""
    if is_topic_change:
        # For topic changes, only include the last exchange to avoid confusion
        recent_messages = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
        print("🔄 Topic change detected - limiting conversation history to prevent continuity issues")
    else:
        # For continuing conversations, include more context to allow better follow-ups
        recent_messages = conversation_history[-6:]  # Increased from 4 to 6 for better follow-up support
        print("🔗 Maintaining conversation context - including extended history for follow-ups")
    
    chat_history = ""
    for msg in recent_messages:
        role = "Customer" if msg["role"] == "user" else "Elsie"
        chat_history += f"{role}: {msg['content']}\n"
    
    return chat_history


def format_conversation_history_with_dgm_elsie(conversation_history: list) -> str:
    """
    Format conversation history with special handling for DGM-controlled Elsie posts.
    DGM-controlled Elsie content ([DGM][Elsie] posts) should appear as if Elsie said them.
    """

    recent_messages = conversation_history[-6:]  # Increased from 4 to 6 for better follow-up support
    print("🔗 Maintaining conversation context - including extended history for follow-ups")
    
    chat_history = ""
    for msg in recent_messages:
        content = msg['content']
        
        # Check if this is a DGM-controlled Elsie post
        dgm_result = check_dgm_post(content)
        if dgm_result['dgm_controlled_elsie']:
            # Extract the Elsie content and present it as if Elsie said it
            elsie_content = dgm_result['elsie_content']
            chat_history += f"Elsie: {elsie_content}\n"
            print(f"   🎭 DGM-CONTROLLED ELSIE CONTENT ADDED TO HISTORY: '{elsie_content[:50]}{'...' if len(elsie_content) > 50 else ''}'")
        else:
            # Regular message formatting
            role = "Customer" if msg["role"] == "user" else "Elsie"
            chat_history += f"{role}: {content}\n"
    
    return chat_history