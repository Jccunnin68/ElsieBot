"""
AI Engine - Gemma API Response Generation
=========================================

This module contains the expensive AI generation operations including
Gemma API calls, database searches, and response processing.
"""

import google.generativeai as genai
from typing import Dict
import re

from config import GEMMA_API_KEY
from handlers.handlers_utils import estimate_token_count
from handlers.ai_logic import ResponseDecision, detect_general_personality_context, detect_who_elsie_addressed
from handlers.handlers_utils import (
    filter_meeting_info,
    convert_earth_date_to_star_trek,
    estimate_token_count
)
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_coordinator.conversation_utils import format_conversation_history_with_dgm_elsie
from handlers.ai_emotion import get_mock_response
from handlers.ai_wisdom.context_coordinator import get_context_for_strategy
from handlers.ai_emotion import should_trigger_poetic_circuit, get_poetic_response
from handlers.ai_coordinator.conversation_utils import detect_topic_change

def convert_to_third_person_emotes(response_text: str) -> str:
    """
    Convert first-person emotes to third-person for consistent roleplay perspective.
    Examples:
    - "*I glance*" -> "*glances*" 
    - "*shakes my head*" -> "*shakes her head*"
    - "*I smile*" -> "*smiles*"
    """
    import re
    
    # Find all emotes (text between asterisks)
    emote_pattern = r'\*([^*]+)\*'
    
    def convert_emote(match):
        emote_text = match.group(1).strip()
        original_emote = emote_text
        
        # Convert first-person pronouns to third-person
        conversions = [
            # "I" at the beginning of emotes
            (r'^I\s+', ''),  # "*I glance*" -> "*glance*"
            (r'\bI\s+', ''),  # "and I smile" -> "and smile"
            
            # "my" to "her"
            (r'\bmy\b', 'her'),  # "*shakes my head*" -> "*shakes her head*"
            (r'\bMy\b', 'Her'),  # "*My eyes widen*" -> "*Her eyes widen*"
            
            # "me" to "her" (when appropriate)
            (r'\bme\b', 'her'),  # "*looks at me*" -> "*looks at her*"
            (r'\bMe\b', 'Her'),  # "*Me too*" -> "*Her too*"
            
            # "myself" to "herself"
            (r'\bmyself\b', 'herself'),
            (r'\bMyself\b', 'Herself'),
        ]
        
        # Apply conversions
        for pattern, replacement in conversions:
            emote_text = re.sub(pattern, replacement, emote_text)
        
        # Handle verb conjugation for "I" removal
        # This is a simplified approach - catches common cases
        verb_fixes = [
            # Fix common verb forms after removing "I"
            (r'^am\b', 'is'),  # "*am walking*" -> "*is walking*"
            (r'^have\b', 'has'),  # "*have noticed*" -> "*has noticed*"
            (r'^do\b', 'does'),  # "*do think*" -> "*does think*"
            (r'^are\b', 'is'),  # "*are feeling*" -> "*is feeling*" (rare but possible)
        ]
        
        for pattern, replacement in verb_fixes:
            emote_text = re.sub(pattern, replacement, emote_text, flags=re.IGNORECASE)
        
        # Log the conversion if it changed
        if emote_text != original_emote:
            print(f"   🎭 EMOTE CONVERSION: '*{original_emote}*' -> '*{emote_text}*'")
        
        return f"*{emote_text}*"
    
    # Apply the conversion to all emotes
    converted_text = re.sub(emote_pattern, convert_emote, response_text)
    
    return converted_text

def strip_discord_emojis(response_text: str) -> str:
    """
    Remove Discord emoji codes from roleplay responses to maintain clean formatting.
    Discord converts :emoji: codes to actual emoji icons, which disrupts roleplay immersion.
    This function either removes them or converts them to appropriate text.
    """
    if not response_text:
        return response_text
    
    original_text = response_text
    
    # Define emoji conversions for common cases
    # Some emojis convert to descriptive text, others are removed entirely
    emoji_conversions = {
        # Facial expressions - convert to descriptive text when in emotes
        ':smile:': 'smiling',
        ':grin:': 'grinning', 
        ':laugh:': 'laughing',
        ':chuckle:': 'chuckling',
        ':wink:': 'winking',
        ':frown:': 'frowning',
        ':sad:': 'sadly',
        ':cry:': 'tearfully',
        ':sigh:': 'sighing',
        ':smirk:': 'smirking',
        ':blush:': 'blushing',
        ':surprised:': 'surprised',
        ':shock:': 'shocked',
        ':confused:': 'confused',
        ':thoughtful:': 'thoughtfully',
        ':pleased:': 'pleased',
        ':content:': 'contentedly',
        
        # Actions - convert to text descriptions
        ':wave:': 'waving',
        ':nod:': 'nodding',
        ':shrug:': 'shrugging',
        ':clap:': 'clapping',
        ':thumbsup:': 'approvingly',
        ':thumbsdown:': 'disapprovingly',
        ':point:': 'pointing',
        ':bow:': 'bowing',
        
        # Reactions/emotions - remove entirely or convert
        ':heart:': '',  # Remove - too emoji-like
        ':sparkles:': '',  # Remove - too emoji-like  
        ':fire:': '',  # Remove - too emoji-like
        ':eyes:': 'watching',
        ':thinking:': 'thoughtfully',
        ':sleepy:': 'tiredly',
        ':yawn:': 'yawning',
        
        # Common Discord emojis - remove entirely
        ':joy:': '',
        ':rofl:': '',
        ':sweat_smile:': '',
        ':kissing_heart:': '',
        ':winking_face:': 'winking',
        ':stuck_out_tongue:': '',
        ':sunglasses:': '',
        ':neutral_face:': '',
        ':expressionless:': '',
        ':unamused:': '',
        ':roll_eyes:': '',
        ':thinking_face:': 'thoughtfully',
        ':flushed:': 'flushed',
        ':disappointed:': 'disappointed',
        ':worried:': 'worried',
        ':angry:': 'angrily',
        ':rage:': 'furiously',
        ':triumph:': 'triumphantly',
        ':relieved:': 'relieved',
        ':tired_face:': 'tiredly',
        ':sleepy:': 'sleepily',
        ':sleeping:': 'sleeping',
        ':mask:': '',
        ':dizzy_face:': 'dizzily',
        ':cowboy:': '',
        ':partying_face:': 'cheerfully',
        ':star_struck:': 'admiringly',
        ':money_mouth:': '',
        ':shushing_face:': 'quietly',
        ':raised_eyebrow:': 'skeptically',
        ':monocle:': 'curiously',
    }
    
    # First pass: Handle emojis inside asterisk emotes
    def process_emote_emojis(match):
        emote_content = match.group(1)
        original_emote = emote_content
        
        # Replace emoji codes within emotes with text descriptions
        for emoji_code, replacement in emoji_conversions.items():
            if emoji_code in emote_content:
                if replacement:  # If we have a text replacement
                    emote_content = emote_content.replace(emoji_code, replacement)
                    print(f"   🎭 EMOJI IN EMOTE: '{emoji_code}' -> '{replacement}' in emote")
                else:  # If replacement is empty, remove the emoji
                    emote_content = emote_content.replace(emoji_code, '').strip()
                    print(f"   🎭 EMOJI REMOVED FROM EMOTE: '{emoji_code}' removed from emote")
        
        # Clean up any double spaces or trailing spaces
        emote_content = re.sub(r'\s+', ' ', emote_content).strip()
        
        return f"*{emote_content}*"
    
    # Process emojis inside emotes first
    emote_pattern = r'\*([^*]+)\*'
    response_text = re.sub(emote_pattern, process_emote_emojis, response_text)
    
    # Second pass: Remove any remaining emoji codes outside of emotes
    emoji_pattern = r':[a-zA-Z0-9_+-]+:'
    remaining_emojis = re.findall(emoji_pattern, response_text)
    
    for emoji in remaining_emojis:
        if emoji in emoji_conversions:
            replacement = emoji_conversions[emoji]
            if replacement:
                response_text = response_text.replace(emoji, replacement)
                print(f"   🎭 EMOJI OUTSIDE EMOTE: '{emoji}' -> '{replacement}'")
            else:
                response_text = response_text.replace(emoji, '')
                print(f"   🎭 EMOJI REMOVED: '{emoji}' removed from text")
        else:
            # Unknown emoji - remove it entirely
            response_text = response_text.replace(emoji, '')
            print(f"   🎭 UNKNOWN EMOJI REMOVED: '{emoji}' removed")
    
    # Clean up any double spaces that might result from emoji removal
    response_text = re.sub(r'\s+', ' ', response_text)
    response_text = re.sub(r'\s*\.\s*', '. ', response_text)  # Fix spacing around periods
    response_text = response_text.strip()
    
    # Log if any changes were made
    if response_text != original_text:
        print(f"   🎭 DISCORD EMOJI FILTERING APPLIED")
        print(f"      Original length: {len(original_text)} chars")
        print(f"      Filtered length: {len(response_text)} chars")
    
    return response_text

def generate_ai_response_with_decision(decision: ResponseDecision, user_message: str, conversation_history: list, channel_context: Dict = None) -> str:
    """
    AI response generation using a pre-made decision.
    Contains only the expensive operations (AI calls, database searches).
    """
    
    try:
        if not GEMMA_API_KEY:
            return get_mock_response(user_message)
        
        strategy = decision.strategy
        
        # Create the model
        model = genai.GenerativeModel('Gemma3-27B-it')
        
        # Detect topic changes for conversation flow
        is_topic_change = detect_topic_change(user_message, conversation_history)
        
        # Initialize context variables
        context = ""
        wiki_info = ""
        
        # Generate context based on strategy
        if strategy['approach'] == 'roleplay_active':
            # ALL roleplay_active responses should use enhanced roleplay context
            print(f"🎭 ROLEPLAY ACTIVE - Using enhanced roleplay context generation")
            from handlers.ai_wisdom.roleplay_context_builder import get_enhanced_roleplay_context
            context = get_enhanced_roleplay_context(strategy, user_message)
        
        elif strategy['approach'] == 'roleplay_mock_enhanced':
            # Roleplay mock enhanced responses also use enhanced roleplay context
            mock_type = strategy.get('mock_response_type', 'unknown')
            print(f"🎭 ROLEPLAY MOCK ENHANCED - {mock_type.upper()} using AI generation with enhanced roleplay context")
            from handlers.ai_wisdom.roleplay_context_builder import get_enhanced_roleplay_context
            context = get_enhanced_roleplay_context(strategy, user_message)
        
        elif strategy['needs_database']:
            print(f"🔍 PERFORMING DATABASE SEARCH for {strategy['approach']} strategy...")
            context = get_context_for_strategy(strategy, user_message)
            # general_with_context from get_context_for_strategy returns just the wiki info
            if strategy['approach'] == 'general_with_context':
                wiki_info = context 
                context = "" # Reset context to be built in the default block
        
        # Generate context for simple chat (no database search needed)
        else:
            print(f"💬 SIMPLE CHAT MODE - No database search needed")
        
        # Set default context for simple chats and cases without specific context
        if not context:
            # Detect personality context for non-roleplay conversations
            personality_context = detect_general_personality_context(user_message)
            
            context = f"""You are Elsie, an intelligent, knowledgeable AI assistant aboard the USS Stardancer. You have expertise in stellar cartography, ship operations, and access to comprehensive databases.

PERSONALITY CONTEXT: {personality_context}

PERSONALITY TRAITS:
- Matter-of-fact and informative when providing information
- Casual and conversational in your communication style
- Intelligent and perceptive, able to understand what users are really asking for
- Genuinely helpful and thorough in your responses
- Professional but approachable - not overly formal or stilted
- Draw on your expertise areas naturally when relevant

EXPERTISE AREAS:
- Stellar cartography and navigation
- Ship operations and fleet information
- Database research and information retrieval
- When drinks are specifically mentioned, you can discuss your bartending experience
- Access to Federation archives for canonical information

COMMUNICATION STYLE:
- Present tense actions without first person: *checks database* not "I check the database"
- Wrap actions in *asterisks* for formatting
- Speak naturally and conversationally
- Be thorough and informative, especially when providing database information
- Don't artificially limit your responses - provide comprehensive information when requested
- Use "I" naturally in conversation - you're not avoiding first person speech
- Keep the holographic bartender roleplay elements minimal unless specifically relevant

CURRENT SETTING: You're aboard the USS Stardancer with access to ship databases and Federation archives. When users ask for information, you can provide detailed, comprehensive responses without artificial length restrictions.

{f"AVAILABLE INFORMATION: {wiki_info}" if wiki_info else ""}

Stay helpful and informative. When providing database information, be thorough and comprehensive. Keep responses natural and conversational while being as detailed as needed to fully answer the user's question."""
        
        # Format conversation history with topic change awareness
        # Special handling for DGM-controlled Elsie content
        chat_history = format_conversation_history_with_dgm_elsie(conversation_history, is_topic_change)
        
        # Add topic change instruction if needed
        topic_instruction = ""
        if is_topic_change:
            topic_instruction = "\n\nIMPORTANT: The customer has asked a NEW QUESTION. Do not continue or elaborate on previous topics. Focus ONLY on answering this specific new question directly and concisely."
        
        # Build the full prompt
        prompt = f"{context}{topic_instruction}\n\nConversation History:\n{chat_history}\nCustomer: {user_message}\nElsie:"
        

        # With increased context window, use full context without chunking
        estimated_tokens = estimate_token_count(prompt)
        print(f"🧮 Estimated token count: {estimated_tokens} (using full context - no chunking)")
        
        # Generate response
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Filter out AI-generated conversation continuations (hallucinated customer dialogue)
        # Split by common conversation continuation patterns
        conversation_continuations = [
            '\nCustomer:', '\nElsie:', '\nUser:', '\nAssistant:', 
            '\n\nCustomer:', '\n\nElsie:', '\n\nUser:', '\n\nAssistant:'
        ]
        
        for continuation in conversation_continuations:
            if continuation in response_text:
                response_text = response_text.split(continuation)[0].strip()
                print(f"🛑 Filtered out AI-generated conversation continuation")
                break
        
        # Determine if this is a roleplay response (should use Star Trek dates)
        is_roleplay_response = strategy.get('approach', '').startswith('roleplay')
        
        # Filter meeting information unless it's a non-roleplay schedule query
        schedule_terms = ['schedule', 'meeting', 'time', 'when', 'gm', 'game master']
        is_schedule_query = any(word in user_message.lower() for word in schedule_terms)
        if is_roleplay_response or not is_schedule_query:
            response_text = filter_meeting_info(response_text)
        
        # Apply Star Trek date conversion ONLY for roleplay queries
        # Non-roleplay queries preserve real Earth dates for accuracy
        if is_roleplay_response:
            response_text = convert_earth_date_to_star_trek(response_text)
        
        # Check for poetic short circuit during casual dialogue
        if strategy['approach'] in ['simple_chat', 'general_with_context'] and should_trigger_poetic_circuit(user_message, conversation_history):
            print(f"🎭 POETIC SHORT CIRCUIT TRIGGERED - Replacing casual response with esoteric poetry")
            response_text = get_poetic_response(user_message, response_text)
        
        # Track who Elsie addressed in her response for simple implicit response logic
        if strategy['approach'] == 'roleplay_active':
            # Convert first-person emotes to third-person for consistent roleplay perspective
            response_text = convert_to_third_person_emotes(response_text)
            
            # Strip Discord emoji codes to maintain clean roleplay formatting
            response_text = strip_discord_emojis(response_text)
            
            rp_state = get_roleplay_state()
            turn_number = len(conversation_history) + 1
            
            addressed_character = detect_who_elsie_addressed(response_text, user_message)
            if addressed_character:
                rp_state.set_last_character_addressed(addressed_character)
                print(f"   📝 TRACKING UPDATE: Elsie addressed {addressed_character}")
            else:
                print(f"   ⚠️  Could not detect who Elsie addressed in response")
                print(f"      - Response: '{response_text[:100]}{'...' if len(response_text) > 100 else ''}'")
                print(f"      - User Message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
            
            # Ensure Elsie's response is tracked in turn history
            if not rp_state.turn_history or rp_state.turn_history[-1][1] != "Elsie":
                rp_state.mark_response_turn(turn_number)
                print(f"   📝 ENSURED: Elsie's response turn tracked")
            
            print(f"   📊 FINAL TRACKING STATE:")
            print(f"      - Last Character Elsie Addressed: {rp_state.last_character_elsie_addressed}")
            print(f"      - Turn History: {rp_state.turn_history}")
            print(f"      - Current Turn: {turn_number}")
        
        # Handle roleplay mock enhanced responses with same tracking
        elif strategy['approach'] == 'roleplay_mock_enhanced':
            # Convert first-person emotes to third-person for consistent roleplay perspective
            response_text = convert_to_third_person_emotes(response_text)
            
            # Strip Discord emoji codes to maintain clean roleplay formatting
            response_text = strip_discord_emojis(response_text)
            
            rp_state = get_roleplay_state()
            turn_number = len(conversation_history) + 1
            mock_type = strategy.get('mock_response_type', 'unknown')
            
            # For drink orders, try to detect who was served
            if mock_type == 'drink_order':
                from handlers.ai_attention.character_tracking import extract_character_names_from_emotes
                character_names = extract_character_names_from_emotes(user_message)
                if character_names:
                    rp_state.set_last_character_addressed(character_names[0])
                    print(f"   📝 TRACKING UPDATE: Elsie served {character_names[0]} (AI-enhanced drink service)")
            
            # For other mock types, try general addressing detection
            else:
                addressed_character = detect_who_elsie_addressed(response_text, user_message)
                if addressed_character:
                    rp_state.set_last_character_addressed(addressed_character)
                    print(f"   📝 TRACKING UPDATE: Elsie addressed {addressed_character} (AI-enhanced {mock_type})")
            
            # Ensure Elsie's response is tracked in turn history
            if not rp_state.turn_history or rp_state.turn_history[-1][1] != "Elsie":
                rp_state.mark_response_turn(turn_number)
                print(f"   📝 ENSURED: Elsie's response turn tracked (AI-enhanced {mock_type})")
        
        print(f"✅ Response generated successfully ({len(response_text)} characters)")
        return response_text
        
    except Exception as e:
        print(f"Gemma API error: {e}")
        return get_mock_response(user_message) 