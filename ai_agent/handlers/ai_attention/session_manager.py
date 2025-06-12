"""Session and conversation management"""

from handlers.ai_wisdom.models import Conversation

# Store conversations by session ID
conversations = {}

def get_or_create_conversation(session_id: str) -> Conversation:
    """Get existing conversation or create new one for session"""
    if session_id not in conversations:
        conversations[session_id] = Conversation()
    return conversations[session_id] 