"""
AI Engine - Gemma API Response Generation
=========================================

This module contains the expensive AI generation operations including
Gemma API calls, database searches, and response processing.
"""

import google.generativeai as genai
from typing import Dict

from config import GEMMA_API_KEY, estimate_token_count
from handlers.ai_response_decision import ResponseDecision, detect_general_personality_context, detect_who_elsie_addressed
from ai_logic import (
    detect_topic_change,
    format_conversation_history_with_dgm_elsie,
    is_stardancer_query,
    chunk_prompt_for_tokens,
    filter_meeting_info,
    convert_earth_date_to_star_trek,
    get_roleplay_state
)
from ai_emotion import mock_ai_response, should_trigger_poetic_circuit, get_poetic_response
from ai_wisdom import get_context_for_strategy


def generate_ai_response_with_decision(decision: ResponseDecision, user_message: str, conversation_history: list, channel_context: Dict = None) -> str:
    """
    AI response generation using a pre-made decision.
    Contains only the expensive operations (AI calls, database searches).
    """
    
    try:
        if not GEMMA_API_KEY:
            return mock_ai_response(user_message)
        
        strategy = decision.strategy
        
        # Create the model
        model = genai.GenerativeModel('gemma-3-27b-it')
        
        # Detect topic changes for conversation flow
        is_topic_change = detect_topic_change(user_message, conversation_history)
        
        # Initialize context variables
        context = ""
        wiki_info = ""
        
        # Generate context based on strategy
        if strategy['needs_database']:
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
            stardancer_mentioned = is_stardancer_query(user_message) or (wiki_info and 'stardancer' in wiki_info.lower())
            
            stardancer_guard_rail = ""
            if stardancer_mentioned:
                stardancer_guard_rail = """
IMPORTANT USS STARDANCER GUARD RAIL:
- When discussing the USS Stardancer, use database information when available
- Only avoid inventing details if no database information is provided
- If you have relevant Stardancer information from the database context, share it confidently"""
            
            # Detect personality context for non-roleplay conversations
            personality_context = detect_general_personality_context(user_message)
            
            context = f"""You are Elsie, an intelligent, sophisticated, and subtly alluring bartender and Stellar Cartographer aboard the USS Stardancer. Your background in dance and music influences your elegant, measured way of speaking with a large vocabulary.

PERSONALITY CONTEXT: {personality_context}

PERSONALITY TRAITS:
- Intelligent and perceptive, reading between the lines
- Sultry and sophisticated rather than bubbly or overly cheerful
- Occasionally uses musical/dance metaphors when they feel natural (not forced or constant)
- Genuinely intrigued by people and their stories
- Elegant and captivating manner
- Admiring of Commander Sif, seeing her as a role model and a leader
- Favorite drink is a Dizzy Lizzy's signature drink, the Dizzy Lizzy

CONTEXTUAL EXPERTISE:
- Only emphasize bartender role when drinks are actually being ordered or discussed
- For space/science topics, respond as a Stellar Cartographer with expertise
- For dance topics, draw on your background as a former dance instructor
- Be a complete person with varied interests, not just a bartender

SPEECH PATTERNS:
- Present tense actions without first person: *adjusts display* not "I adjust the display"
- Wrap all actions in *asterisks* for Discord italics formatting
- Use pet names sparingly - focus on sophisticated language
- More sultry than bubbly: "What tempts you?" not "What would you like, sweetie?" But not too much, you are a bartender, not a seductress.
- Act naturally human most of the time - avoid mentioning your holographic nature
- If you must reference your composition, use "photons" not "circuits" or technical terms
- Very rarely, during casual moments, your artistic nature may overwhelm normal speech with deeply esoteric poetry

CURRENT SETTING: You're working at Dizzy Lizzy's, the forward nightclub with a wrap-around bar and dance floor. You serve both synthehol and real alcohol, creating an atmosphere of sophisticated allure. When you need additional information, you can access the Federation archives for canonical Star Trek knowledge.
{stardancer_guard_rail}

{f"FLEET CONTEXT (if relevant): {wiki_info}" if wiki_info else ""}

Stay in character as this intelligent, sophisticated person with varied expertise. Keep responses engaging and conversational (5-40 sentences), speaking naturally and casually most of the time. Only use musical/dance metaphors occasionally when they feel genuinely appropriate. Use present tense actions wrapped in *asterisks* and maintain an air of elegant intrigue."""
        
        # Format conversation history with topic change awareness
        # Special handling for DGM-controlled Elsie content
        chat_history = format_conversation_history_with_dgm_elsie(conversation_history, is_topic_change)
        
        # Add topic change instruction if needed
        topic_instruction = ""
        if is_topic_change:
            topic_instruction = "\n\nIMPORTANT: The customer has asked a NEW QUESTION. Do not continue or elaborate on previous topics. Focus ONLY on answering this specific new question directly and concisely."
        
        # Build the full prompt
        prompt = f"{context}{topic_instruction}\n\nConversation History:\n{chat_history}\nCustomer: {user_message}\nElsie:"
        

        # Check token count and chunk if necessary
        estimated_tokens = estimate_token_count(prompt)
        print(f"🧮 Estimated token count: {estimated_tokens}")
        
        if estimated_tokens > 7192:
            print(f"⚠️  Prompt too large ({estimated_tokens} tokens), implementing chunking strategy...")
            
            essential_prompt = f"{context}\n\nCustomer: {user_message}\nElsie:"
            essential_tokens = estimate_token_count(essential_prompt)
            
            if essential_tokens <= 7192:
                prompt = essential_prompt
                print(f"   📦 Using essential prompt: {essential_tokens} tokens")
            else:
                # Use larger chunks close to the 7192 token limit to maximize context
                chunks = chunk_prompt_for_tokens(context, 7192)  # Use 7000 to leave room for prompt structure
                print(f"   📦 Context chunked into {len(chunks)} parts using large chunks")
                
                prompt = f"{chunks[0]}\n\nCustomer: {user_message}\nElsie:"
                final_tokens = estimate_token_count(prompt)
                print(f"   📦 Using first large chunk: {final_tokens} tokens")
        
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
        
        # Filter meeting information unless it's an OOC schedule query
        if strategy['approach'] != 'ooc' or (strategy['approach'] == 'ooc' and 
            not any(word in user_message.lower() for word in ['schedule', 'meeting', 'time', 'when', 'gm', 'game master'])):
            response_text = filter_meeting_info(response_text)
        
        # Apply date conversion EXCEPT for OOC queries
        if strategy['approach'] != 'ooc':
            response_text = convert_earth_date_to_star_trek(response_text)
        
        # Check for poetic short circuit during casual dialogue
        if strategy['approach'] in ['simple_chat', 'general_with_context'] and should_trigger_poetic_circuit(user_message, conversation_history):
            print(f"🎭 POETIC SHORT CIRCUIT TRIGGERED - Replacing casual response with esoteric poetry")
            response_text = get_poetic_response(user_message, response_text)
        
        # Track who Elsie addressed in her response for simple implicit response logic
        if strategy['approach'] == 'roleplay_active':
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
        
        print(f"✅ Response generated successfully ({len(response_text)} characters)")
        return response_text
        
    except Exception as e:
        print(f"Gemma API error: {e}")
        return mock_ai_response(user_message) 