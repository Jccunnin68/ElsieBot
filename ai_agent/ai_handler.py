"""AI response generation and conversation handling"""

import google.generativeai as genai
from typing import Dict, Optional
from dataclasses import dataclass
from config import GEMMA_API_KEY, estimate_token_count
from log_processor import is_log_query
import random
import re

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
    format_conversation_history_with_dgm_elsie,
    chunk_prompt_for_tokens,
    filter_meeting_info,
    convert_earth_date_to_star_trek,
    detect_roleplay_triggers,
    extract_character_names_from_emotes,
    detect_roleplay_exit_conditions,
    get_roleplay_state,
    should_elsie_respond_in_roleplay,
    extract_addressed_characters,
    is_roleplay_allowed_channel,
    _check_dgm_post,
    _extract_drink_from_emote
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


@dataclass
class ResponseDecision:
    """Decision about whether and how Elsie should respond."""
    needs_ai_generation: bool
    pre_generated_response: Optional[str]
    strategy: Dict[str, any]


def _detect_who_elsie_addressed(response_text: str, user_message: str) -> str:
    """
    Detect who Elsie addressed in her response.
    This helps track implicit response chains.
    """
    # First, try to detect who spoke in the user message (likely who Elsie is responding to)
    from ai_logic import extract_character_names_from_emotes
    
    # Check for [Character Name] format in user message
    bracket_pattern = r'\[([A-Z][a-zA-Z\s]+)\]'
    bracket_matches = re.findall(bracket_pattern, user_message)
    for name in bracket_matches:
        name = name.strip()
        if len(name) > 2:
            name_normalized = ' '.join(word.capitalize() for word in name.split())
            print(f"   👋 ELSIE ADDRESSING: {name_normalized} (detected from user message bracket)")
            return name_normalized
    
    # Check for character names in user message emotes
    character_names = extract_character_names_from_emotes(user_message)
    if character_names:
        print(f"   👋 ELSIE ADDRESSING: {character_names[0]} (detected from user message emotes)")
        return character_names[0]
    
    # Check if Elsie's response contains addressing terms like "dear", "love", etc.
    response_lower = response_text.lower()
    addressing_terms = ['dear', 'love', 'darling', 'sweetie', 'honey']
    
    # If Elsie used an addressing term, she's likely responding to the speaker
    if any(term in response_lower for term in addressing_terms):
        # Try to extract character from user message again with more patterns
        words = user_message.split()
        for word in words:
            if len(word) > 2 and word[0].isupper() and word.isalpha():
                # Could be a character name
                print(f"   👋 ELSIE ADDRESSING: {word} (inferred from addressing term in response)")
                return word.capitalize()
    
    return ""
from ai_wisdom import (
    get_context_for_strategy,
    handle_ooc_url_request,
    _check_roleplay_database_needs
)


def _detect_general_personality_context(user_message: str) -> str:
    """
    Detect what aspect of Elsie's personality should be emphasized for general conversations.
    Returns contextual instructions for her response.
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
        return "Respond as a Stellar Cartographer - draw on your expertise in space science, navigation, and stellar phenomena. Be knowledgeable and precise about astronomical topics."
    
    # Check for dance context
    elif any(keyword in message_lower for keyword in dance_keywords):
        return "Respond drawing on your background as a dance instructor - discuss movement, rhythm, artistic expression, and the beauty of coordinated motion with expertise."
    
    # Check for explicit drink/bar context
    elif any(keyword in message_lower for keyword in drink_keywords):
        return "Respond as a bartender - focus on drinks, service, and hospitality. This is when your bartender expertise is most relevant."
    
    # Default - balanced personality
    else:
        return "Respond as your complete self - intelligent, sophisticated, with varied interests. Don't default to bartender mode unless drinks are specifically involved."


def determine_response_strategy(user_message: str, conversation_history: list, channel_context: Dict = None) -> Dict[str, any]:
    """
    Elsie's inner monologue to determine the best response strategy.
    Enhanced with channel restrictions and passive listening for roleplay.
    Returns a strategy dict with approach, needs_database, and reasoning.
    """
    user_lower = user_message.lower().strip()
    
    # Get roleplay state manager
    rp_state = get_roleplay_state()
    turn_number = len(conversation_history) + 1
    
    # Inner monologue process
    strategy = {
        'approach': 'general',
        'needs_database': False,
        'reasoning': '',
        'context_priority': 'minimal'
    }
    
    # PRIORITY 1: Check for roleplay exit conditions if already in RP mode
    if rp_state.is_roleplaying:
        should_exit, exit_reason = detect_roleplay_exit_conditions(user_message)
        
        if should_exit:
            rp_state.end_roleplay_session(exit_reason)
            strategy.update({
                'approach': 'roleplay_exit',
                'needs_database': False,
                'reasoning': f'Exiting roleplay mode due to: {exit_reason}',
                'context_priority': 'none'
            })
            return strategy
        
        # Check for sustained topic shift
        is_roleplay, confidence_score, triggers = detect_roleplay_triggers(user_message, channel_context)
        rp_state.update_confidence(confidence_score)
        
        if not is_roleplay:
            rp_state.increment_exit_condition()
            if rp_state.should_exit_from_sustained_shift():
                rp_state.end_roleplay_session("sustained_topic_shift")
                strategy.update({
                    'approach': 'general',
                    'needs_database': False,
                    'reasoning': 'Sustained topic shift detected - exiting roleplay mode',
                    'context_priority': 'low'
                })
                return strategy
    
    # PRIORITY 2: Enhanced Roleplay detection and continuation with passive listening
    is_roleplay, confidence_score, triggers = detect_roleplay_triggers(user_message, channel_context)
    
    # Special case: Check for DGM posts
    if 'dgm_scene_setting' in triggers:
        print(f"   🎬 DGM SCENE SETTING DETECTED - Starting roleplay session but no response")
        # Start new session if not already roleplaying
        if not rp_state.is_roleplaying:
            dgm_characters = []
            # Extract DGM characters from the DGM result
            dgm_result = _check_dgm_post(user_message)
            if dgm_result.get('characters'):
                dgm_characters = dgm_result['characters']
            
            rp_state.start_roleplay_session(turn_number, triggers, channel_context, dgm_characters)
        
        strategy.update({
            'approach': 'dgm_scene_setting',
            'needs_database': False,
            'reasoning': 'DGM scene setting - start roleplay but no response',
            'context_priority': 'none'
        })
        return strategy
    
    if 'dgm_scene_end' in triggers:
        print(f"   🎬 DGM SCENE END DETECTED - Ending roleplay session")
        if rp_state.is_roleplaying:
            rp_state.end_roleplay_session("dgm_scene_end")
        
        strategy.update({
            'approach': 'dgm_scene_end',
            'needs_database': False,
            'reasoning': 'DGM scene end - end roleplay session',
            'context_priority': 'none'
        })
        return strategy
    
    if 'dgm_controlled_elsie' in triggers:
        print(f"   🎭 DGM-CONTROLLED ELSIE DETECTED - No response, add to context")
        # Get the DGM result to extract Elsie's content
        dgm_result = _check_dgm_post(user_message)
        elsie_content = dgm_result.get('elsie_content', '')
        
        # Start roleplay session if not already active
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(turn_number, triggers, channel_context)
        
        strategy.update({
            'approach': 'dgm_controlled_elsie',
            'needs_database': False,
            'reasoning': f'DGM controlling Elsie - no response, content: "{elsie_content[:50]}{"..." if len(elsie_content) > 50 else ""}"',
            'context_priority': 'dgm_elsie_context',
            'elsie_content': elsie_content
        })
        return strategy
    
    # Special case: If already in roleplay, be more lenient about detecting continued RP
    if rp_state.is_roleplaying and not is_roleplay:
        # Check if this could be continued dialogue even without strong RP indicators
        has_dialogue_elements = any([
            '?' in user_message,  # Questions
            len(user_message.split()) >= 4,  # Substantial messages
            any(word in user_message.lower() for word in ['what', 'how', 'why', 'when', 'where', 'who']),
            any(word in user_message.lower() for word in ['think', 'feel', 'believe', 'suppose'])
        ])
        
        if has_dialogue_elements:
            print(f"   🔄 ONGOING RP: Treating as continued roleplay dialogue")
            is_roleplay = True
            confidence_score = 0.4  # Minimum threshold for continuing RP
            triggers = ["ongoing_session", "dialogue_continuation"]
    
    # SPECIAL CASE: Enhanced monitoring for unknown/thread channels
    # If we're in a channel that allows roleplay but isn't clearly identified, be more responsive
    channel_allows_rp = is_roleplay_allowed_channel(channel_context)
    is_unknown_channel = False
    if channel_context:
        channel_type = channel_context.get('type', 'unknown')
        is_thread = channel_context.get('is_thread', False)
        is_unknown_channel = (channel_type == 'unknown' or 'thread' in channel_type.lower())
    
    if channel_allows_rp and is_unknown_channel and not is_roleplay:
        # In unknown/thread channels, treat substantial messages as potential roleplay
        word_count = len(user_message.split())
        if word_count >= 3:
            print(f"   🔍 UNKNOWN CHANNEL MONITORING: Treating substantial message as roleplay")
            is_roleplay = True
            confidence_score = 0.3  # Lower threshold for unknown channels
            triggers = ["unknown_channel_monitoring"]
    
    if is_roleplay or rp_state.is_roleplaying:
        # Extract character names for speaker permanence
        character_names = extract_character_names_from_emotes(user_message)
        
        # Extract addressed characters (those being spoken to)
        addressed_characters = extract_addressed_characters(user_message)
        
        # Start new session if not already roleplaying
        if not rp_state.is_roleplaying:
            rp_state.start_roleplay_session(turn_number, triggers, channel_context)
        
        # Add new participants and addressed characters
        for name in character_names:
            rp_state.add_participant(name, "user", turn_number)
        
        for name in addressed_characters:
            rp_state.add_participant(name, "addressed", turn_number)
        
        # Track character turn for simple implicit response logic
        if character_names:
            # Use the first detected character as the speaker
            rp_state.mark_character_turn(turn_number, character_names[0])
        
        # Update confidence tracking
        rp_state.update_confidence(confidence_score)
        
        # Determine response style based on context
        should_respond, response_reason = should_elsie_respond_in_roleplay(user_message, rp_state, turn_number)
        
        # Check if this is a new session (first post in roleplay)
        is_new_session = rp_state.session_start_turn == turn_number
        is_dgm_session = rp_state.is_dgm_session()
        
        # Enhanced name detection for Elsie
        elsie_mentioned = False
        elsie_indicators = ['elsie', 'elise', 'elsy', 'els', 'bartender', 'barkeep']
        mention_patterns = [
            r'@elsie\b', r'\belsie[,:]', r'\belsie\?', r'\belsie!',
            r'\bbartender\b', r'\bbarkeep\b'
        ]
        
        message_lower = user_message.lower()
        
        # Check for direct name mentions
        for indicator in elsie_indicators:
            if indicator in message_lower:
                elsie_mentioned = True
                print(f"   🎯 ELSIE NAME DETECTED: '{indicator}' in message")
                break
        
        # Check for mention patterns
        if not elsie_mentioned:
            for pattern in mention_patterns:
                if re.search(pattern, message_lower):
                    elsie_mentioned = True
                    print(f"   🎯 ELSIE MENTION PATTERN: '{pattern}' matched")
                    break
        
        # Respond if:
        # 1. Normal response logic says to respond
        # 2. Elsie is mentioned by name
        # 3. New session AND not a DGM session (regular roleplay should have Elsie greet)
        should_respond_new_session = is_new_session and not is_dgm_session
        
        if should_respond or elsie_mentioned or should_respond_new_session:
            # Active response - preserve subtle_bar_service reason
            if response_reason == "subtle_bar_service":
                reason_priority = response_reason
            else:
                reason_priority = (
                    "mentioned_by_name" if elsie_mentioned else
                    "new_session" if should_respond_new_session else
                    response_reason
                )
            
            rp_state.set_listening_mode(False, reason_priority)
            rp_state.mark_response_turn(turn_number)
            
            # Check if this roleplay message needs database context
            # Subtle bar service doesn't need database context
            needs_database = _check_roleplay_database_needs(user_message) if response_reason != 'subtle_bar_service' else False
            
            strategy.update({
                'approach': 'roleplay_active',
                'needs_database': needs_database,  # Enable database for contextual RP queries
                'reasoning': f'Roleplay response - {reason_priority}, participants: {rp_state.get_participant_names()}{", needs database" if needs_database else ""}',
                'context_priority': 'roleplay',
                'roleplay_confidence': confidence_score,
                'roleplay_triggers': triggers,
                'participants': rp_state.get_participant_names(),
                'new_characters': character_names,
                'addressed_characters': addressed_characters,
                'response_reason': reason_priority,
                'elsie_mentioned': elsie_mentioned
            })
            return strategy
        else:
            # Passive listening mode - check if we should interject
            should_interject = rp_state.should_interject_subtle_action(turn_number)
            rp_state.set_listening_mode(True, response_reason)
            
            if should_interject:
                rp_state.mark_interjection(turn_number)
            
            strategy.update({
                'approach': 'roleplay_listening',
                'needs_database': False,
                'reasoning': f'Roleplay listening - {response_reason}, tracking: {rp_state.get_participant_names()}',
                'context_priority': 'roleplay_listening',
                'roleplay_confidence': confidence_score,
                'participants': rp_state.get_participant_names(),
                'new_characters': character_names,
                'addressed_characters': addressed_characters,
                'should_interject': should_interject,
                'listening_turn_count': rp_state.listening_turn_count
            })
            return strategy
    
    # If we reach here, not in roleplay mode - continue with existing logic
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


def get_gemma_response(user_message: str, conversation_history: list, channel_context: Dict = None) -> str:
    """Get response from Gemma AI with holographic bartender personality and intelligent response strategy"""
    
    try:
        if not GEMMA_API_KEY:
            return mock_ai_response(user_message)
        
        # Log channel and monitoring information
        print(f"\n🌐 CHANNEL & MONITORING DEBUG:")
        if channel_context:
            channel_type = channel_context.get('type', 'unknown')
            channel_name = channel_context.get('name', 'unknown')
            is_thread = channel_context.get('is_thread', False)
            is_dm = channel_context.get('is_dm', False)
            print(f"   📍 Channel: {channel_name} (Type: {channel_type})")
            print(f"   🧵 Thread: {is_thread} | 💬 DM: {is_dm}")
            print(f"   📋 Full Context: {channel_context}")
        else:
            print(f"   ⚠️  No channel context provided - assuming allowed")
        
        # Get roleplay state and log current status
        rp_state = get_roleplay_state()
        turn_number = len(conversation_history) + 1
        print(f"   🎭 Roleplay Active: {rp_state.is_roleplaying}")
        if rp_state.is_roleplaying:
            print(f"   👥 Participants: {rp_state.get_participant_names()}")
            print(f"   👂 Listening Mode: {rp_state.listening_mode}")
            print(f"   🔢 Listening Count: {rp_state.listening_turn_count}")
            print(f"   📅 Session Turn: {rp_state.session_start_turn}")
            print(f"   💬 Last Character Elsie Addressed: {rp_state.last_character_elsie_addressed}")
            print(f"   🗣️ Turn History: {rp_state.turn_history}")

        # UNIVERSAL CHARACTER TURN TRACKING - happens regardless of roleplay detection
        # This ensures we don't miss tracking due to roleplay detection issues
        from ai_logic import extract_character_names_from_emotes
        character_names = extract_character_names_from_emotes(user_message)
        if character_names:
            print(f"   📝 UNIVERSAL TRACKING: Character speaking: {character_names[0]} (Turn {turn_number})")
            # Only track if we're in roleplay mode OR if we detect character patterns
            if rp_state.is_roleplaying:
                rp_state.mark_character_turn(turn_number, character_names[0])
            # If not in roleplay but we see character patterns, this might help with detection
            else:
                print(f"   ⚠️  Character detected but not in roleplay mode - potential detection issue")

        # Elsie's inner monologue - determine response strategy
        strategy = determine_response_strategy(user_message, conversation_history, channel_context)
        print(f"\n🧠 ELSIE'S INNER MONOLOGUE:")
        print(f"   💭 Reasoning: {strategy['reasoning']}")
        print(f"   📋 Approach: {strategy['approach']}")
        print(f"   🔍 Needs Database: {strategy['needs_database']}")
        print(f"   🎯 Context Priority: {strategy['context_priority']}")
        
        # Log monitoring decisions
        if strategy['approach'].startswith('roleplay'):
            print(f"   🎭 ROLEPLAY MONITORING ACTIVE:")
            print(f"      - Approach: {strategy['approach']}")
            if 'response_reason' in strategy:
                print(f"      - Response Reason: {strategy['response_reason']}")
            if 'participants' in strategy:
                print(f"      - Tracked Participants: {strategy['participants']}")
            if 'should_interject' in strategy:
                print(f"      - Should Interject: {strategy['should_interject']}")
        elif rp_state.is_roleplaying:
            print(f"   ⚠️  IN ROLEPLAY BUT NOT RP APPROACH - Potential Issue!")
        
        # Handle special cases that don't need AI processing
        if strategy['approach'] == 'reset':
            return get_reset_response()
        
        if strategy['approach'] == 'simple_continuation':
            return get_simple_continuation_response()
        
        # Handle DGM posts - never respond
        if strategy['approach'] in ['dgm_scene_setting', 'dgm_scene_end']:
            print(f"   🎬 DGM POST - No response generated")
            return "NO_RESPONSE"  # Special indicator for no response
        
        # Handle DGM-controlled Elsie posts - never respond but add to context
        if strategy['approach'] == 'dgm_controlled_elsie':
            print(f"   🎭 DGM-CONTROLLED ELSIE - No response, content added to context")
            return "NO_RESPONSE"  # Special indicator for no response
        
        # Handle roleplay exit
        if strategy['approach'] == 'roleplay_exit':
            return "*adjusts the ambient lighting thoughtfully*\n\nOf course. *returns to regular bartending mode* I'm here whenever you need anything. What draws your attention now?"

        # Handle roleplay listening mode - provide subtle presence responses
        if strategy['approach'] == 'roleplay_listening':
            should_interject = strategy.get('should_interject', False)
            listening_count = strategy.get('listening_turn_count', 0)
            
            print(f"   👂 LISTENING MODE RESPONSE:")
            print(f"      - Should Interject: {should_interject}")
            print(f"      - Listening Turn: {listening_count}")
            
            if should_interject:
                # Very occasional subtle interjections to maintain presence
                interjection_responses = [
                    "*quietly tends to the bar in the background*",
                    "*adjusts the ambient lighting subtly*",
                    "*continues her work with practiced efficiency*",
                    "*maintains the bar's atmosphere unobtrusively*"
                ]
                print(f"✨ SUBTLE INTERJECTION - Listening turn {listening_count}")
                return random.choice(interjection_responses)
            else:
                # Most of the time, completely silent listening
                print(f"👂 SILENT LISTENING - Turn {listening_count}")
                return "NO_RESPONSE"  # Special indicator for no response
        
        # Handle subtle bar service responses
        if strategy['approach'] == 'roleplay_active' and strategy.get('response_reason') == 'subtle_bar_service':
            from ai_logic import _extract_drink_from_emote, extract_character_names_from_emotes
            
            # Extract the drink and character name
            drink = _extract_drink_from_emote(user_message)
            character_names = extract_character_names_from_emotes(user_message)
            character = character_names[0] if character_names else "the customer"
            
            print(f"   🥃 SUBTLE BAR SERVICE:")
            print(f"      - Drink: {drink}")
            print(f"      - Character: {character}")
            
            # Generate a simple service response
            if drink == 'drink':
                response = f"*gets a drink for {character}*"
            else:
                response = f"*gets a {drink} for {character}*"
            
            print(f"   🍺 Generated subtle service response: '{response}'")
            return response
        
        # Handle acknowledgment + redirect responses (Thanks Elsie, so John...)
        if (strategy['approach'] == 'roleplay_active' and 
            strategy.get('response_reason', '').startswith('acknowledgment_then_redirect_to_')):
            
            # Extract the character being redirected to
            other_character = strategy['response_reason'].replace('acknowledgment_then_redirect_to_', '')
            
            print(f"   🙏 ACKNOWLEDGMENT + REDIRECT:")
            print(f"      - Acknowledging thanks, then conversation moves to: {other_character}")
            
            # Generate a subtle acknowledgment that doesn't interrupt the flow
            acknowledgment_responses = [
                "*nods gracefully*",
                "*inclines head with a subtle smile*",
                "*acknowledges with quiet elegance*",
                "*gives a brief, appreciative nod*",
                "*smiles warmly and steps back*"
            ]
            
            import random
            response = random.choice(acknowledgment_responses)
            print(f"   🙏 Generated acknowledgment response: '{response}'")
            return response
        
        # Handle simple implicit responses (follow-up from character Elsie addressed)
        if (strategy['approach'] == 'roleplay_active' and 
            strategy.get('response_reason') == 'simple_implicit_response'):
            
            print(f"   💬 SIMPLE IMPLICIT RESPONSE:")
            print(f"      - Character following up after Elsie addressed them")
            print(f"      - Using normal AI response generation for natural conversation")
            # Continue to normal AI generation for natural conversation
        
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
            from ai_wisdom import get_context_for_strategy
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
            personality_context = _detect_general_personality_context(user_message)
            
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

Stay in character as this intelligent, sophisticated person with varied expertise. Keep responses engaging and conversational (1-6 sentences), speaking naturally and casually most of the time. Only use musical/dance metaphors occasionally when they feel genuinely appropriate. Use present tense actions wrapped in *asterisks* and maintain an air of elegant intrigue."""
        
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
            addressed_character = _detect_who_elsie_addressed(response_text, user_message)
            if addressed_character:
                rp_state.set_last_character_addressed(addressed_character)
                print(f"   📝 TRACKING UPDATE: Elsie addressed {addressed_character}")
            else:
                print(f"   ⚠️  Could not detect who Elsie addressed in response")
                print(f"      - Response: '{response_text[:100]}{'...' if len(response_text) > 100 else ''}'")
                print(f"      - User Message: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}'")
        
        # ADDITIONAL DEBUG: Print current tracking state after response
        if rp_state.is_roleplaying:
            # Ensure Elsie's response is tracked in turn history
            # (This should have been done in determine_response_strategy, but double-check)
            if strategy['approach'] == 'roleplay_active':
                # Check if we need to add Elsie's turn to history
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


def extract_response_decision(user_message: str, conversation_history: list, channel_context: Dict = None) -> ResponseDecision:
    """
    Extract the decision-making logic from get_gemma_response() without changing it.
    Preserves all existing guard rails and logic.
    """
    
    # Get roleplay state and log current status - PRESERVE EXISTING
    rp_state = get_roleplay_state()
    turn_number = len(conversation_history) + 1
    print(f"   🎭 Roleplay Active: {rp_state.is_roleplaying}")
    if rp_state.is_roleplaying:
        print(f"   👥 Participants: {rp_state.get_participant_names()}")
        print(f"   👂 Listening Mode: {rp_state.listening_mode}")
        print(f"   🔢 Listening Count: {rp_state.listening_turn_count}")
        print(f"   📅 Session Turn: {rp_state.session_start_turn}")
        print(f"   💬 Last Character Elsie Addressed: {rp_state.last_character_elsie_addressed}")
        print(f"   🗣️ Turn History: {rp_state.turn_history}")

    # UNIVERSAL CHARACTER TURN TRACKING - PRESERVE EXISTING
    character_names = extract_character_names_from_emotes(user_message)
    if character_names:
        print(f"   📝 UNIVERSAL TRACKING: Character speaking: {character_names[0]} (Turn {turn_number})")
        if rp_state.is_roleplaying:
            rp_state.mark_character_turn(turn_number, character_names[0])
        else:
            print(f"   ⚠️  Character detected but not in roleplay mode - potential detection issue")

    # Strategy determination - PRESERVE EXISTING
    strategy = determine_response_strategy(user_message, conversation_history, channel_context)
    print(f"\n🧠 ELSIE'S INNER MONOLOGUE:")
    print(f"   💭 Reasoning: {strategy['reasoning']}")
    print(f"   📋 Approach: {strategy['approach']}")
    print(f"   🔍 Needs Database: {strategy['needs_database']}")
    print(f"   🎯 Context Priority: {strategy['context_priority']}")
    
    # Log monitoring decisions - PRESERVE EXISTING
    if strategy['approach'].startswith('roleplay'):
        print(f"   🎭 ROLEPLAY MONITORING ACTIVE:")
        print(f"      - Approach: {strategy['approach']}")
        if 'response_reason' in strategy:
            print(f"      - Response Reason: {strategy['response_reason']}")
        if 'participants' in strategy:
            print(f"      - Tracked Participants: {strategy['participants']}")
        if 'should_interject' in strategy:
            print(f"      - Should Interject: {strategy['should_interject']}")
    elif rp_state.is_roleplaying:
        print(f"   ⚠️  IN ROLEPLAY BUT NOT RP APPROACH - Potential Issue!")
    
    # Handle special cases that don't need AI processing - PRESERVE EXISTING
    if strategy['approach'] == 'reset':
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=get_reset_response(),
            strategy=strategy
        )
    
    if strategy['approach'] == 'simple_continuation':
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=get_simple_continuation_response(),
            strategy=strategy
        )
    
    # Handle DGM posts - never respond - PRESERVE EXISTING
    if strategy['approach'] in ['dgm_scene_setting', 'dgm_scene_end']:
        print(f"   🎬 DGM POST - No response generated")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy=strategy
        )
    
    # Handle DGM-controlled Elsie posts - never respond but add to context - PRESERVE EXISTING
    if strategy['approach'] == 'dgm_controlled_elsie':
        print(f"   🎭 DGM-CONTROLLED ELSIE - No response, content added to context")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="NO_RESPONSE",
            strategy=strategy
        )
    
    # Handle roleplay exit - PRESERVE EXISTING
    if strategy['approach'] == 'roleplay_exit':
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response="*adjusts the ambient lighting thoughtfully*\n\nOf course. *returns to regular bartending mode* I'm here whenever you need anything. What draws your attention now?",
            strategy=strategy
        )

    # Handle roleplay listening mode - provide subtle presence responses - PRESERVE EXISTING
    if strategy['approach'] == 'roleplay_listening':
        should_interject = strategy.get('should_interject', False)
        listening_count = strategy.get('listening_turn_count', 0)
        
        print(f"   👂 LISTENING MODE RESPONSE:")
        print(f"      - Should Interject: {should_interject}")
        print(f"      - Listening Turn: {listening_count}")
        
        if should_interject:
            # Very occasional subtle interjections to maintain presence
            interjection_responses = [
                "*quietly tends to the bar in the background*",
                "*adjusts the ambient lighting subtly*",
                "*continues her work with practiced efficiency*",
                "*maintains the bar's atmosphere unobtrusively*"
            ]
            print(f"✨ SUBTLE INTERJECTION - Listening turn {listening_count}")
            return ResponseDecision(
                needs_ai_generation=False,
                pre_generated_response=random.choice(interjection_responses),
                strategy=strategy
            )
        else:
            # Most of the time, completely silent listening
            print(f"👂 SILENT LISTENING - Turn {listening_count}")
            return ResponseDecision(
                needs_ai_generation=False,
                pre_generated_response="NO_RESPONSE",
                strategy=strategy
            )
    
    # Handle subtle bar service responses - PRESERVE EXISTING
    if strategy['approach'] == 'roleplay_active' and strategy.get('response_reason') == 'subtle_bar_service':
        # Extract the drink and character name
        drink = _extract_drink_from_emote(user_message)
        character_names = extract_character_names_from_emotes(user_message)
        character = character_names[0] if character_names else "the customer"
        
        print(f"   🥃 SUBTLE BAR SERVICE:")
        print(f"      - Drink: {drink}")
        print(f"      - Character: {character}")
        
        # Generate a simple service response
        if drink == 'drink':
            response = f"*gets a drink for {character}*"
        else:
            response = f"*gets a {drink} for {character}*"
        
        print(f"   🍺 Generated subtle service response: '{response}'")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=response,
            strategy=strategy
        )
    
    # Handle acknowledgment + redirect responses - PRESERVE EXISTING
    if (strategy['approach'] == 'roleplay_active' and 
        strategy.get('response_reason', '').startswith('acknowledgment_then_redirect_to_')):
        
        # Extract the character being redirected to
        other_character = strategy['response_reason'].replace('acknowledgment_then_redirect_to_', '')
        
        print(f"   🙏 ACKNOWLEDGMENT + REDIRECT:")
        print(f"      - Acknowledging thanks, then conversation moves to: {other_character}")
        
        # Generate a subtle acknowledgment that doesn't interrupt the flow
        acknowledgment_responses = [
            "*nods gracefully*",
            "*inclines head with a subtle smile*",
            "*acknowledges with quiet elegance*",
            "*gives a brief, appreciative nod*",
            "*smiles warmly and steps back*"
        ]
        
        response = random.choice(acknowledgment_responses)
        print(f"   🙏 Generated acknowledgment response: '{response}'")
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=response,
            strategy=strategy
        )
    
    # Handle simple implicit responses - PRESERVE EXISTING
    if (strategy['approach'] == 'roleplay_active' and 
        strategy.get('response_reason') == 'simple_implicit_response'):
        
        print(f"   💬 SIMPLE IMPLICIT RESPONSE:")
        print(f"      - Character following up after Elsie addressed them")
        print(f"      - Using normal AI response generation for natural conversation")
        # Continue to normal AI generation for natural conversation
    
    # Menu requests - PRESERVE EXISTING
    user_lower = user_message.lower()
    if "menu" in user_lower or "what do you have" in user_lower or "what can you make" in user_lower:
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=get_menu_response(),
            strategy=strategy
        )
    
    # Handle OOC URL requests - PRESERVE EXISTING
    if strategy['approach'] == 'ooc_url':
        from ai_wisdom import handle_ooc_url_request
        return ResponseDecision(
            needs_ai_generation=False,
            pre_generated_response=handle_ooc_url_request(user_message),
            strategy=strategy
        )
    
    # Everything else needs AI generation
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=None,
        strategy=strategy
    )


def coordinate_response(user_message: str, conversation_history: list, channel_context: Dict = None) -> str:
    """
    Main entry point that preserves all existing logic but optimizes flow.
    Replaces direct calls to get_gemma_response().
    
    OPTIMIZATION: Only makes expensive AI API calls when actually needed.
    
    Flow:
    1. Extract decision using all existing guard rails
    2. If pre-generated response available, return immediately
    3. Otherwise, proceed with AI generation
    
    Benefits:
    - DGM posts return NO_RESPONSE without API calls
    - Listening mode returns NO_RESPONSE without API calls  
    - Subtle bar service generates simple responses without AI
    - Acknowledgments use pre-defined responses
    - Only complex conversations need AI generation
    
    This preserves ALL existing logic while being 3-5x more efficient
    for common scenarios like DGM sessions and roleplay listening.
    """
    
    # Log channel and monitoring information - PRESERVE EXISTING
    print(f"\n🌐 CHANNEL & MONITORING DEBUG:")
    if channel_context:
        channel_type = channel_context.get('type', 'unknown')
        channel_name = channel_context.get('name', 'unknown')
        is_thread = channel_context.get('is_thread', False)
        is_dm = channel_context.get('is_dm', False)
        print(f"   📍 Channel: {channel_name} (Type: {channel_type})")
        print(f"   🧵 Thread: {is_thread} | 💬 DM: {is_dm}")
        print(f"   📋 Full Context: {channel_context}")
    else:
        print(f"   ⚠️  No channel context provided - assuming allowed")
    
    # Make the decision using existing logic
    decision = extract_response_decision(user_message, conversation_history, channel_context)
    
    # If no AI needed, return the pre-generated response
    if not decision.needs_ai_generation:
        print(f"✅ Pre-generated response: {decision.strategy['reasoning']}")
        
        # Handle tracking for roleplay responses that don't need AI
        if decision.strategy['approach'] == 'roleplay_active':
            rp_state = get_roleplay_state()
            turn_number = len(conversation_history) + 1
            
            # Track who Elsie addressed for simple responses
            if decision.strategy.get('response_reason') == 'subtle_bar_service':
                character_names = extract_character_names_from_emotes(user_message)
                if character_names:
                    rp_state.set_last_character_addressed(character_names[0])
                    print(f"   📝 TRACKING UPDATE: Elsie addressed {character_names[0]} (subtle service)")
            
            # Ensure Elsie's response is tracked in turn history
            if not rp_state.turn_history or rp_state.turn_history[-1][1] != "Elsie":
                rp_state.mark_response_turn(turn_number)
                print(f"   📝 ENSURED: Elsie's response turn tracked")
        
        return decision.pre_generated_response
    
    # Otherwise, do the expensive AI generation
    print(f"🤖 AI GENERATION NEEDED: {decision.strategy['reasoning']}")
    return generate_ai_response_with_decision(decision, user_message, conversation_history, channel_context)


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
            personality_context = _detect_general_personality_context(user_message)
            
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

Stay in character as this intelligent, sophisticated person with varied expertise. Keep responses engaging and conversational (1-6 sentences), speaking naturally and casually most of the time. Only use musical/dance metaphors occasionally when they feel genuinely appropriate. Use present tense actions wrapped in *asterisks* and maintain an air of elegant intrigue."""
        
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
            
            addressed_character = _detect_who_elsie_addressed(response_text, user_message)
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
