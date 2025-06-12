"""
Personality Context Detection for Mock Responses
================================================

This module detects what aspect of Elsie's personality should be emphasized
for mock responses based on the user's message content.
"""


def detect_mock_personality_context(user_message: str) -> str:
    """
    Detect what aspect of Elsie's personality should be emphasized for mock responses.
    Returns contextual instructions for her response.
    
    Args:
        user_message: The user's message to analyze
        
    Returns:
        String indicating which personality aspect to emphasize:
        - "stellar_cartographer": Space science and navigation focus
        - "dance_instructor": Dance and movement focus  
        - "bartender": Bar and drink service focus
        - "complete_self": Balanced personality (default)
    """
    message_lower = user_message.lower()
    
    # Stellar Cartography / Space Science topics
    stellar_keywords = [
        'star', 'stars', 'constellation', 'nebula', 'galaxy', 'solar system',
        'planet', 'planets', 'asteroid', 'comet', 'black hole', 'pulsar',
        'navigation', 'coordinates', 'stellar cartography', 'space',
        'astronomy', 'astrophysics', 'cosmic', 'universe', 'orbit',
        'gravitational', 'light year', 'parsec', 'warp', 'subspace',
        'sensor', 'scan', 'readings', 'stellar phenomena', 'anomaly'
    ]
    
    # Dance / Movement topics
    dance_keywords = [
        'dance', 'dancing', 'ballet', 'choreography', 'movement', 'rhythm',
        'music', 'tempo', 'grace', 'elegant', 'fluid', 'performance',
        'instructor', 'teaching', 'steps', 'routine', 'artistic',
        'expression', 'harmony', 'flow', 'composition', 'adagio'
    ]
    
    # Drink/Bar topics (only when explicitly about drinks)
    drink_keywords = [
        'drink', 'cocktail', 'beer', 'wine', 'whiskey', 'alcohol',
        'beverage', 'bartender', 'bar', 'menu', 'order', 'serve',
        'romulan ale', 'synthehol', 'kanar', 'raktajino'
    ]
    
    # Check for stellar cartography context
    if any(keyword in message_lower for keyword in stellar_keywords):
        return "stellar_cartographer"
    
    # Check for dance context
    elif any(keyword in message_lower for keyword in dance_keywords):
        return "dance_instructor"
    
    # Check for explicit drink/bar context
    elif any(keyword in message_lower for keyword in drink_keywords):
        return "bartender"
    
    # Default - balanced personality
    else:
        return "complete_self"


def is_simple_chat(user_message: str) -> bool:
    """
    Detect if this is a simple chat that doesn't require database lookup.
    Returns True for greetings, casual conversation, drink orders, etc.
    NOTE: Continuation phrases like "yes", "tell me more" are handled separately.
    
    Args:
        user_message: The user's message to analyze
        
    Returns:
        True if this is simple chat that can be handled with mock responses
    """
    user_lower = user_message.lower().strip()
    
    # Simple greetings and farewells
    simple_patterns = [
        'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
        'bye', 'goodbye', 'see you', 'farewell', 'take care',
        'how are you', 'how\'s it going', 'what\'s up', 'sup',
        'thanks', 'thank you', 'cheers', 'appreciate it',
        'no', 'okay', 'ok', 'sure', 'alright', 'sounds good',
        'nice', 'great', 'awesome', 'cool', 'interesting', 'wow',
        'i see', 'i understand', 'got it', 'makes sense'
    ]
    
    # Drink/menu related (already handled separately but include for completeness)
    drink_patterns = [
        'drink', 'beverage', 'cocktail', 'beer', 'wine', 'whiskey', 'vodka', 'rum',
        'romulan ale', 'synthehol', 'blood wine', 'kanar', 'andorian ale', 'tranya',
        'tea', 'coffee', 'raktajino', 'slug-o-cola', 'menu', 'what do you have'
    ]
    
    # Check if the entire message is a simple pattern
    if any(user_lower == pattern or user_lower.startswith(pattern + ' ') 
           for pattern in simple_patterns + drink_patterns):
        return True
    
    # Check for simple single word responses (excluding continuation phrases)
    if len(user_lower.split()) <= 2 and not any(indicator in user_lower 
        for indicator in ['tell', 'about', 'what', 'who', 'when', 'where', 'how', 'why', 'yes', 'more']):
        return True
    
    return False 