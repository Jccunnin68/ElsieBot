"""
AI Engine - Gemma API Response Generation
=========================================

This module contains the expensive AI generation operations including
Gemma API calls, database searches, and response processing.
"""

import google.generativeai as genai
from typing import Dict, List
import re

from config import GEMMA_API_KEY
from handlers.handlers_utils import estimate_token_count, filter_meeting_info, convert_earth_date_to_star_trek
from handlers.ai_logic.response_decision import ResponseDecision
from handlers.ai_attention.state_manager import get_roleplay_state
from handlers.ai_logic.context_detection import detect_who_elsie_addressed
from handlers.ai_emotion import get_mock_response, should_trigger_poetic_circuit, get_poetic_response
from handlers.ai_coordinator.conversation_utils import convert_to_third_person_emotes, strip_discord_emojis

# Constants
MAX_PROMPT_CHARS = 26000  # Approx. 8000 tokens as a safe upper limit
SUMMARIZATION_TARGET_CHARS = 24000 # Give it some buffer

# In-memory cache for generated responses
response_cache = {}

def _summarize_prompt_context(long_prompt: str, user_message: str) -> str:
    """Uses a fast LLM to summarize a long context prompt that exceeds token limits."""
    print(f"   🔄 SUMMARIZING long prompt ({len(long_prompt)} chars)...")
    try:
        # Use a fast, capable model for summarization
        summarizer_model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # The user's most recent message is the most important part.
        # We find it, separate it, summarize the rest of the context, and append it back.
        suffix_to_preserve = f"\\nCustomer: {user_message}\\nElsie:"
        if long_prompt.endswith(suffix_to_preserve):
            context_to_summarize = long_prompt[:-len(suffix_to_preserve)]
        else:
            # Fallback if the prompt structure is unexpected. Summarize everything.
            context_to_summarize = long_prompt
            suffix_to_preserve = "" # Nothing to append

        summarization_prompt = f"""
The following is a large context block for a conversation with an AI assistant named Elsie. It is too long to be processed.
Your task is to summarize this context. The summary must be less than {SUMMARIZATION_TARGET_CHARS} characters.

CRITICAL INSTRUCTIONS:
1.  Preserve all essential entities like character names, ship names, locations, specific dates, and technical terms from the original context.
2.  Retain the key points and flow of the most recent conversation history.
3.  The goal is to create a condensed version of the original context that allows the AI to respond accurately to the user's final message.
4.  Do NOT add any new information or dialogue. Your output should be only the summarized text.

CONTEXT TO SUMMARIZE:
---
{context_to_summarize}
---
END OF CONTEXT

Provide only the summarized context, ready to be passed to the main AI.
"""
        
        # Use a simple generation config for summarization
        summary_response = summarizer_model.generate_content(summarization_prompt)
        summarized_context = summary_response.text.strip()
        
        # Re-assemble the final prompt
        final_prompt = summarized_context + suffix_to_preserve

        print(f"   ✅ Summarization complete. New length: {len(final_prompt)} chars")
        return final_prompt
        
    except Exception as e:
        print(f"   ❌ ERROR during prompt summarization: {e}")
        print(f"   ⚠️  Falling back to simple truncation as a last resort.")
        # Truncate from the beginning to preserve the most recent history
        start_index = len(long_prompt) - SUMMARIZATION_TARGET_CHARS
        return "[... context truncated due to length ...]\\n" + long_prompt[start_index:]


def generate_ai_response_with_decision(decision: ResponseDecision, user_message: str, conversation_history: list) -> str:
    """
    AI response generation using a pre-made decision.
    Contains only the expensive operations (AI calls).
    """
    try:
        if not GEMMA_API_KEY:
            return get_mock_response(user_message)

        strategy = decision.strategy
        model = genai.GenerativeModel('gemma-3-27b-it')
        
        # The pre_generated_response from the decision is the full context prompt
        final_prompt = decision.pre_generated_response
        
        # If the prompt is too long, summarize it using an LLM
        if len(final_prompt) > MAX_PROMPT_CHARS:
            final_prompt = _summarize_prompt_context(final_prompt, user_message)

        print(f"   💬 Final prompt length: {len(final_prompt)} characters")

        # Check cache first
        cache_key = (final_prompt, user_message)
        if cache_key in response_cache:
            print("   ✅ CACHE HIT - Returning cached response.")
            return response_cache[cache_key]
        
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=6000,
            temperature=0.7
        )

        response = model.generate_content(final_prompt, generation_config=generation_config)
        response_text = response.text.strip()
        
        # Post-processing and tracking logic...
        response_text = _post_process_response(response_text, strategy, user_message, conversation_history)

        # Cache the response
        response_cache[cache_key] = response_text
        return response_text
        
    except Exception as e:
        print(f"❌ Error in AI response generation: {e}")
        return get_mock_response(user_message)


def _post_process_response(response_text: str, strategy: Dict, user_message: str, conversation_history: List[str]) -> str:
    """Helper function to apply all post-processing to the generated text."""
    
    # Filter out AI-generated conversation continuations
    conversation_continuations = ['\\nCustomer:', '\\nElsie:', '\\nUser:', '\\nAssistant:']
    for continuation in conversation_continuations:
        if continuation in response_text:
            response_text = response_text.split(continuation)[0].strip()
            print(f"🛑 Filtered out AI-generated conversation continuation")
            break
            
    # Determine if this is a roleplay response
    is_roleplay_response = strategy.get('approach', '').startswith('roleplay_')
    
    # Filter meeting information unless it's a non-roleplay schedule query
    schedule_terms = ['schedule', 'meeting', 'time', 'when', 'gm', 'game master']
    is_schedule_query = any(word in user_message.lower() for word in schedule_terms)
    if is_roleplay_response or not is_schedule_query:
        response_text = filter_meeting_info(response_text)
    
    # Apply Star Trek date conversion ONLY for roleplay queries
    if is_roleplay_response:
        response_text = convert_earth_date_to_star_trek(response_text)
    
    # Poetic circuit for casual dialogue
    if strategy.get('approach') in ['simple_chat', 'general'] and should_trigger_poetic_circuit(user_message, conversation_history):
        print(f"🎭 POETIC SHORT CIRCUIT TRIGGERED")
        response_text = get_poetic_response(user_message, response_text)
        
    # Roleplay-specific processing
    if is_roleplay_response:
        response_text = convert_to_third_person_emotes(response_text)
        response_text = strip_discord_emojis(response_text)
        
        # Track who Elsie addressed in her response
        rp_state = get_roleplay_state()
        turn_number = len(conversation_history) + 1
        addressed_character = detect_who_elsie_addressed(response_text, user_message)
        if addressed_character:
            rp_state.set_last_character_addressed(addressed_character)
            print(f"   📝 TRACKING UPDATE: Elsie addressed {addressed_character}")

        if not rp_state.turn_history or rp_state.turn_history[-1][1] != "Elsie":
            rp_state.mark_response_turn(turn_number)

    return response_text 