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
MAX_PROMPT_CHARS = 48000  # Approx. 8000 tokens as a safe upper limit
SUMMARIZATION_TARGET_CHARS = 44000 # Give it some buffer
MAX_OUTPUT_TOKENS = 8000  # Maximum output tokens per chunk
CHUNK_SIZE_CHARS = 30000  # Approximate characters per chunk to stay under output limits
CHUNK_OVERLAP_CHARS = 2000  # Overlap between chunks to maintain context

# In-memory cache for generated responses
response_cache = {}

def _summarize_prompt_context(long_prompt: str, user_message: str) -> str:
    """Uses a fast LLM to summarize a long context prompt that exceeds token limits."""
    print(f"   🔄 SUMMARIZING long prompt ({len(long_prompt)} chars)...")
    try:
        # Use a fast, capable model for summarization
        summarizer_model = genai.GenerativeModel('gemini-2.0-flash-lite')

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
The following is a large context block for a conversation with an Holographic Bartender assistant named Elsie. It is too long to be processed.
Your task is to summarize this context. The summary must be less than {SUMMARIZATION_TARGET_CHARS} characters but use as much as possible.

CRITICAL INSTRUCTIONS:
-FORBIDDEN: You are not to commen and pretend you are a Narrative consultant.
-FORBIDDEN:- Doing anything other than delivering the information that has been presented to you.
1.  Preserve all essential entities like character names, ship names, locations, specific dates, and technical terms from the original context.
2.  Retain the key points and flow of the most recent conversation history.
3.  The goal is to create a condensed version of the original context that allows the AI to respond accurately to the user's final message.
4.  Your output must be only the summarized text. You must not add, invent, or speculate on any information that is not explicitly in the provided context.
5.  It should be in Narrative Style unless already a bullet point list.

CONTEXT TO SUMMARIZE:
---
{context_to_summarize}
---
END OF CONTEXT

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

def _return_content_in_chunks(content: str, user_message: str) -> str:
    """
    Returns large content in chunks without LLM processing.
    """
    print(f"   📦 Returning content in chunks directly without LLM processing")
    
    chunks = _split_content_into_chunks(content)
    result_parts = []
    
    # Add introduction for the first chunk
    if len(chunks) > 1:
        intro = f"Content will be presented in {len(chunks)} parts due to length."
        result_parts.append(intro)
    
    for i, chunk in enumerate(chunks):
        if len(chunks) > 1:
            part_header = f"\n--- Part {i+1} of {len(chunks)} ---\n"
            result_parts.append(part_header)
        
        result_parts.append(chunk)
    
    result = '\n\n'.join(result_parts)
    print(f"   ✅ Content returned in {len(chunks)} chunks directly ({len(result)} total chars)")
    return result

def _estimate_output_size(content: str) -> int:
    """
    Estimates the output size in tokens based on content length.
    Uses a rough approximation: 1 token ≈ 4 characters for output.
    """
    return len(content) // 4

def _should_use_chunking(content: str) -> bool:
    """
    Determines if content should be processed in chunks based on estimated output size.
    """
    estimated_tokens = _estimate_output_size(content)
    return estimated_tokens > MAX_OUTPUT_TOKENS * 0.8  # Use 80% threshold for safety

def _split_content_into_chunks(content: str) -> List[str]:
    """
    Splits large content into smaller chunks with overlap to maintain context.
    Tries to split at natural boundaries like paragraph breaks.
    """
    if len(content) <= CHUNK_SIZE_CHARS:
        return [content]
    
    chunks = []
    current_pos = 0
    
    while current_pos < len(content):
        # Calculate chunk end position
        chunk_end = min(current_pos + CHUNK_SIZE_CHARS, len(content))
        
        # Try to find a natural break point (paragraph, sentence, etc.)
        if chunk_end < len(content):
            # Look for paragraph breaks first
            last_paragraph = content.rfind('\n\n', current_pos, chunk_end)
            if last_paragraph > current_pos:
                chunk_end = last_paragraph + 2
            else:
                # Look for sentence breaks
                last_sentence = content.rfind('. ', current_pos, chunk_end)
                if last_sentence > current_pos:
                    chunk_end = last_sentence + 2
                else:
                    # Look for any line break
                    last_line = content.rfind('\n', current_pos, chunk_end)
                    if last_line > current_pos:
                        chunk_end = last_line + 1
        
        # Extract the chunk
        chunk = content[current_pos:chunk_end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move to next chunk with overlap
        if chunk_end >= len(content):
            break
        
        # Calculate next position with overlap
        current_pos = max(chunk_end - CHUNK_OVERLAP_CHARS, current_pos + 1)
    
    print(f"   📦 Split content into {len(chunks)} chunks")
    return chunks

def generate_ai_response_with_decision(decision: ResponseDecision, user_message: str, conversation_history: list) -> str:
    """
    AI response generation using a pre-made decision.
    For standard mode: directly relay wisdom engine content.
    For roleplay mode: use AI engine processing.
    """
    try:
        if not GEMMA_API_KEY:
            return get_mock_response(user_message)

        strategy = decision.strategy
        approach = strategy.get('approach', '')
        
        # The pre_generated_response from the decision is the wisdom engine content
        wisdom_content = decision.pre_generated_response
        
        # STANDARD QUERIES: Directly relay wisdom engine content without LLM processing
        # Only bypass AI engine for standard database/knowledge queries, not chat interactions
        if approach in ['logs', 'comprehensive', 'general', 'character', 'ship', 'location']:
            print(f"   📤 STANDARD QUERY MODE - Relaying wisdom engine content directly without LLM processing")
            print(f"   📊 Content length: {len(wisdom_content)} characters")
            
            # Check if content needs chunking due to size
            if _should_use_chunking(wisdom_content):
                print(f"   📦 Content requires chunking - returning in parts")
                return _return_content_in_chunks(wisdom_content, user_message)
            
            # Return wisdom engine content directly
            return wisdom_content
        
        # ALL OTHER MODES: Use AI engine processing (roleplay, simple_chat, general, etc.)
        print(f"   🤖 AI ENGINE MODE ({approach}) - Processing with AI engine")
        final_prompt = wisdom_content
        
        # If the prompt is too long, summarize it using an LLM
        if len(final_prompt) > MAX_PROMPT_CHARS:
            final_prompt = _summarize_prompt_context(final_prompt, user_message)

        print(f"   💬 Final prompt length: {len(final_prompt)} characters")

        # Check cache first
        cache_key = (final_prompt, user_message)
        if cache_key in response_cache:
            print("   ✅ CACHE HIT - Returning cached response.")
            return response_cache[cache_key]
        
        model = genai.GenerativeModel('gemma-3-27b-it')
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=8000,
            temperature=0.8
        )

        response = model.generate_content(final_prompt, generation_config=generation_config)
        response_text = response.text.strip()
        
        # Check if the response might be truncated and needs chunking
        estimated_full_size = _estimate_output_size(final_prompt)
        if estimated_full_size > MAX_OUTPUT_TOKENS and len(response_text) >= MAX_OUTPUT_TOKENS * 3:  # Rough char estimate
            print(f"   ⚠️  Response may be truncated ({len(response_text)} chars, estimated {estimated_full_size} tokens)")
            print(f"   📦 Content appears truncated - returning what we have")
            # For roleplay mode, return the partial response rather than trying to chunk
        
        # Post-processing and tracking logic for roleplay...
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