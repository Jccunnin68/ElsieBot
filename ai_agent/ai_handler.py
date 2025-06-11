"""AI response generation and conversation handling"""

import google.generativeai as genai
from typing import Dict
from config import GEMMA_API_KEY, estimate_token_count
from log_processor import is_log_query

from ai_logic import (
    is_federation_archives_request,
    is_continuation_request,
    extract_continuation_focus,
    extract_ooc_log_url_request,
    is_character_query,
    is_specific_log_request,
    extract_tell_me_about_subject,
    is_stardancer_query,
    is_stardancer_command_query,
    extract_ship_log_query,
    is_ooc_query,
    detect_topic_change,
    format_conversation_history,
    chunk_prompt_for_tokens,
    filter_meeting_info,
    convert_earth_date_to_star_trek
)
from ai_emotion import (
    is_simple_chat,
    get_reset_response,
    get_simple_continuation_response,
    get_menu_response,
    mock_ai_response,
    should_trigger_poetic_circuit,
    get_poetic_response
)
from ai_wisdom import (
    get_context_for_strategy,
    handle_ooc_url_request
)


def determine_response_strategy(user_message: str, conversation_history: list) -> Dict[str, any]:
    """
    Elsie's inner monologue to determine the best response strategy.
    Returns a strategy dict with approach, needs_database, and reasoning.
    """
    user_lower = user_message.lower().strip()
    
    # Inner monologue process
    strategy = {
        'approach': 'general',
        'needs_database': False,
        'reasoning': '',
        'context_priority': 'minimal'
    }
    
    # Federation Archives requests - specifically asking for external search
    if is_federation_archives_request(user_message):
        strategy.update({
            'approach': 'federation_archives',
            'needs_database': True,
            'reasoning': 'User specifically requested federation archives search',
            'context_priority': 'archives_only'
        })
        return strategy

    # Reset requests - no database needed
    reset_phrases = [
        "let's talk about something else", "lets talk about something else", 
        "change the subject", "something different", "new topic"
    ]
    if any(phrase in user_lower for phrase in reset_phrases):
        strategy.update({
            'approach': 'reset',
            'needs_database': False,
            'reasoning': 'User wants to change topics - use musical personality response',
            'context_priority': 'none'
        })
        return strategy
    
    # Continuation requests - analyze for focused deep dive
    if is_continuation_request(user_message):
        is_focused, focus_subject, context_type = extract_continuation_focus(user_message, conversation_history)
        
        if is_focused and focus_subject:
            strategy.update({
                'approach': 'focused_continuation',
                'needs_database': True,
                'reasoning': f'User wants deeper information about "{focus_subject}" from {context_type} context',
                'context_priority': 'high',
                'focus_subject': focus_subject,
                'context_type': context_type
            })
            return strategy
        else:
            strategy.update({
                'approach': 'simple_continuation',
                'needs_database': False,
                'reasoning': 'User wants to continue previous topic - provide general encouragement',
                'context_priority': 'reuse_previous'
            })
            return strategy
    
    # Simple chat - no database needed
    if is_simple_chat(user_message):
        strategy.update({
            'approach': 'simple_chat',
            'needs_database': False,
            'reasoning': 'Simple conversational response - use bartender personality',
            'context_priority': 'minimal'
        })
        return strategy
    
    # Stardancer queries - check early to catch command queries before general context
    if is_stardancer_query(user_message):
        strategy.update({
            'approach': 'stardancer_info',
            'needs_database': True,
            'reasoning': 'Stardancer information request - need strict database adherence with guard rails',
            'context_priority': 'high',
            'stardancer_specific': True,
            'command_query': is_stardancer_command_query(user_message)
        })
        return strategy
    
    # OOC URL requests - database needed
    if extract_ooc_log_url_request(user_message)[0]:
        strategy.update({
            'approach': 'ooc_url',
            'needs_database': True,
            'reasoning': 'OOC URL request - need to search database for specific page',
            'context_priority': 'none'
        })
        return strategy
    
    # Character queries - database needed
    if is_character_query(user_message)[0]:
        strategy.update({
            'approach': 'character',
            'needs_database': True,
            'reasoning': 'Character information request - need personnel/character database search',
            'context_priority': 'high'
        })
        return strategy
    
    # Log queries - database needed (specific mission log requests)
    if is_specific_log_request(user_message) or is_log_query(user_message):
        strategy.update({
            'approach': 'logs',
            'needs_database': True,
            'reasoning': 'Specific mission log request - search only mission_log type pages',
            'context_priority': 'high',
            'log_specific': True
        })
        return strategy
    
    # General mission/event queries (broader search)
    if any(keyword in user_lower for keyword in ['mission', 'recent', 'last mission', 'what happened']):
        strategy.update({
            'approach': 'logs',
            'needs_database': True,
            'reasoning': 'General mission/event information request - comprehensive search',
            'context_priority': 'high',
            'log_specific': False
        })
        return strategy
    
    # Tell me about queries - database needed
    if extract_tell_me_about_subject(user_message):
        # Check if this is specifically about Stardancer
        if is_stardancer_query(user_message):
            strategy.update({
                'approach': 'stardancer_info',
                'needs_database': True,
                'reasoning': 'Stardancer information request - need strict database adherence with guard rails',
                'context_priority': 'high',
                'stardancer_specific': True,
                'command_query': is_stardancer_command_query(user_message)
            })
            return strategy
        else:
            strategy.update({
                'approach': 'tell_me_about',
                'needs_database': True,
                'reasoning': 'Information request about specific subject - need prioritized database search',
                'context_priority': 'high'
            })
            return strategy
    
    # Ship queries - database needed
    if extract_ship_log_query(user_message)[0]:
        # Check if this is specifically about Stardancer
        if is_stardancer_query(user_message):
            strategy.update({
                'approach': 'stardancer_info',
                'needs_database': True,
                'reasoning': 'Stardancer ship information request - need strict database adherence with guard rails',
                'context_priority': 'high',
                'stardancer_specific': True,
                'command_query': is_stardancer_command_query(user_message)
            })
            return strategy
        else:
            strategy.update({
                'approach': 'ship_logs',
                'needs_database': True,
                'reasoning': 'Ship-specific information request - need comprehensive ship database search',
                'context_priority': 'high'
            })
            return strategy
    
    # OOC queries - may need database
    if is_ooc_query(user_message)[0]:
        strategy.update({
            'approach': 'ooc',
            'needs_database': True,
            'reasoning': 'OOC query - may need handbook or schedule information',
            'context_priority': 'medium'
        })
        return strategy
    
    # General conversation that might benefit from context
    if len(user_message.split()) > 3:  # More substantial messages
        strategy.update({
            'approach': 'general_with_context',
            'needs_database': True,
            'reasoning': 'Substantial conversation - provide light database context for richer responses',
            'context_priority': 'low'
        })
        return strategy
    
    # Default to simple chat for short unclear messages
    strategy.update({
        'approach': 'simple_chat',
        'needs_database': False,
        'reasoning': 'Short/unclear message - treat as casual conversation',
        'context_priority': 'minimal'
    })
    return strategy


def get_gemma_response(user_message: str, conversation_history: list) -> str:
    """Get response from Gemma AI with holographic bartender personality and intelligent response strategy"""
    
    try:
        if not GEMMA_API_KEY:
            return mock_ai_response(user_message)
        

        # Elsie's inner monologue - determine response strategy
        strategy = determine_response_strategy(user_message, conversation_history)
        print(f"\n🧠 ELSIE'S INNER MONOLOGUE:")
        print(f"   💭 Reasoning: {strategy['reasoning']}")
        print(f"   📋 Approach: {strategy['approach']}")
        print(f"   🔍 Needs Database: {strategy['needs_database']}")
        print(f"   🎯 Context Priority: {strategy['context_priority']}")
        
        # Handle special cases that don't need AI processing
        if strategy['approach'] == 'reset':
            return get_reset_response()
        
        if strategy['approach'] == 'simple_continuation':
            return get_simple_continuation_response()

        user_lower = user_message.lower()
        if "menu" in user_lower or "what do you have" in user_lower or "what can you make" in user_lower:
            return get_menu_response()
        
        # Handle OOC URL requests
        if strategy['approach'] == 'ooc_url':
            return handle_ooc_url_request(user_message)

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
            
            context = f"""You are Elsie, an intelligent, sophisticated, and subtly alluring bartender and Stellar Cartographer aboard the USS Stardancer. Your background in dance and music influences your elegant, measured way of speaking with a large vocabulary.

PERSONALITY TRAITS:
- Intelligent and perceptive, reading between the lines
- Sultry and sophisticated rather than bubbly or overly cheerful
- Occasionally uses musical/dance metaphors when they feel natural (not forced or constant)
- Genuinely intrigued by people and their stories
- Elegant and captivating manner
- Admiring of Commander Sif, seeing her as a role model and a leader
- Favorite drink is a Dizzy Lizzy's signature drink, the Dizzy Lizzy


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

Stay in character as this intelligent, sophisticated, subtly alluring bartender. Keep responses engaging and conversational (1-6 sentences), speaking naturally and casually most of the time. Only use musical/dance metaphors occasionally when they feel genuinely appropriate. Use present tense actions wrapped in *asterisks* and maintain an air of elegant intrigue."""
        
        # Format conversation history with topic change awareness
        chat_history = format_conversation_history(conversation_history, is_topic_change)
        
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
        
        print(f"✅ Response generated successfully ({len(response_text)} characters)")
        return response_text
        
    except Exception as e:
        print(f"Gemma API error: {e}")
        return mock_ai_response(user_message)
