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

def _is_narrative_content(content: str) -> bool:
    """
    Detects if content appears to be a narrative/story that should be relayed directly
    rather than analyzed or summarized.
    """
    # Indicators that content is a narrative/story
    narrative_indicators = [
        # Story structure markers
        "walked into", "entered the", "approached the", "turned to", 
        "looked at", "stared at", "glanced at", "noticed",
        # Dialogue markers
        '" said', '" asked', '" replied', '" whispered', '" shouted',
        # Action/movement verbs in past tense
        "moved", "stepped", "ran", "walked", "climbed", "descended",
        # Time progression markers
        "then", "next", "suddenly", "meanwhile", "later", "after",
        # Character interaction markers
        "spoke to", "addressed", "turned to face", "looked toward"
    ]
    
    # Count narrative indicators
    indicator_count = sum(1 for indicator in narrative_indicators if indicator.lower() in content.lower())
    
    # If content has multiple narrative indicators and is substantial, it's likely a story
    if indicator_count >= 3 and len(content) > 500:
        return True
    
    # Check for typical story paragraph structure (multiple sentences with past tense verbs)
    sentences = content.split('.')
    past_tense_verbs = ['walked', 'entered', 'approached', 'turned', 'looked', 'spoke', 'said', 'asked', 'replied', 'moved', 'stepped', 'ran', 'climbed', 'descended', 'noticed', 'stared', 'glanced']
    
    past_tense_count = 0
    for sentence in sentences:
        if any(verb in sentence.lower() for verb in past_tense_verbs):
            past_tense_count += 1
    
    # If many sentences contain past tense narrative verbs, likely a story
    if len(sentences) > 3 and past_tense_count >= len(sentences) * 0.4:
        return True
    
    return False

def _create_story_introduction(user_message: str, content_length: int) -> str:
    """
    Creates a simple, direct introduction when presenting story content,
    without personality overlay or elaborate storytelling language.
    """
    # Simple, direct introductions based on content type
    request_lower = user_message.lower()
    
    if 'log' in request_lower or 'mission' in request_lower:
        return "Here is the mission log content you requested:"
    
    elif ('who is' in request_lower or 'tell me about' in request_lower and 
          any(name in request_lower for name in ['captain', 'commander', 'lieutenant', 'ensign', 'blaine', 'sif', 'torres', 'kiryna']) or
          'character' in request_lower or 'person' in request_lower):
        return "Here is the information about the character you requested:"
    
    elif ('ship' in request_lower or 'vessel' in request_lower or 'uss' in request_lower or 
          any(ship in request_lower for ship in ['stardancer', 'adagio', 'pilgrim', 'sentinel', 'banshee', 'protector', 'manta', 'gigantes', 'caelian', 'enterprise'])):
        return "Here is the information about the ship you requested:"
    
    else:
        return "Here is the content you requested:"

def _extract_narrative_from_prompt(prompt: str) -> str:
    """
    Extracts narrative content from a prompt by looking for common patterns
    where the wisdom engine places processed story content.
    """
    # Look for content between various markers that the wisdom engine might use
    extraction_patterns = [
        ("**Cleaned and Reformatted Log:**", "**"),
        ("**Story Content:**", "**"),
        ("**Narrative:**", "**"),
        ("Here is the story:", "---"),
        ("Story content:", "---"),
        ("Narrative content:", "---"),
        ("---", "---"),  # Content between --- markers
    ]
    
    for start_marker, end_marker in extraction_patterns:
        if start_marker in prompt:
            parts = prompt.split(start_marker)
            if len(parts) > 1:
                content_part = parts[1]
                
                # If there's an end marker, extract content up to it
                if end_marker in content_part and end_marker != start_marker:
                    content_part = content_part.split(end_marker)[0]
                
                # Clean up the extracted content
                cleaned_content = content_part.strip()
                
                # Remove common prompt artifacts
                artifacts_to_remove = [
                    "Customer:", "Elsie:", "User:", "Assistant:",
                    "Present this", "Share this", "Tell the user"
                ]
                
                for artifact in artifacts_to_remove:
                    if cleaned_content.startswith(artifact):
                        cleaned_content = cleaned_content[len(artifact):].strip()
                
                if len(cleaned_content) > 100:  # Only return substantial content
                    return cleaned_content
    
    return ""

def _return_content_in_chunks(content: str, user_message: str) -> str:
    """
    Returns large content in chunks with simple introductions, without LLM processing.
    """
    print(f"   📦 Returning content in chunks directly without LLM processing")
    
    chunks = _split_content_into_chunks(content)
    result_parts = []
    
    # Add introduction for the first chunk
    intro = _create_story_introduction(user_message, len(content))
    if len(chunks) > 1:
        intro += f" (This content will be presented in {len(chunks)} parts due to length.)"
    
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

def _process_content_chunks(content: str, user_message: str, strategy: Dict) -> str:
    """
    Processes content in chunks when it's too large for a single response.
    """
    print(f"   📦 Processing content in chunks due to size ({len(content)} chars)")
    
    chunks = _split_content_into_chunks(content)
    processed_chunks = []
    
    for i, chunk in enumerate(chunks):
        print(f"   🔄 Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        
        # Create a chunk-specific prompt
        chunk_prompt = f"""You are Elsie, a holographic assistant. You are presenting story content to the user in multiple parts, maintaining the original sophistication and narrative structure.

This is part {i+1} of {len(chunks)} of the requested content. Present this section clearly and faithfully without adding personality commentary or simplifying the language.

User's request: {user_message}

Story content for this section:
---
{chunk}
---

Present this content section faithfully, preserving the original language and narrative style. {"This is the beginning of the story." if i == 0 else "This continues from the previous section." if i < len(chunks) - 1 else "This concludes the story."}"""

        try:
            model = genai.GenerativeModel('gemma-3-27b-it')
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.2  # Low temperature for faithful reproduction
            )

            response = model.generate_content(chunk_prompt, generation_config=generation_config)
            chunk_response = response.text.strip()
            
            if chunk_response:
                processed_chunks.append(chunk_response)
                print(f"   ✅ Chunk {i+1} processed ({len(chunk_response)} chars)")
            else:
                print(f"   ⚠️  Chunk {i+1} returned empty response, using original")
                processed_chunks.append(chunk)
                
        except Exception as e:
            print(f"   ❌ Error processing chunk {i+1}: {e}")
            processed_chunks.append(chunk)
    
    # Combine all processed chunks
    result = '\n\n'.join(processed_chunks)
    print(f"   ✅ Chunked processing complete: {len(result)} total chars")
    return result

def generate_ai_response_with_decision(decision: ResponseDecision, user_message: str, conversation_history: list) -> str:
    """
    AI response generation using a pre-made decision.
    Contains only the expensive operations (AI calls).
    """
    try:
        if not GEMMA_API_KEY:
            return get_mock_response(user_message)

        strategy = decision.strategy
        
        # The pre_generated_response from the decision is the full context prompt
        final_prompt = decision.pre_generated_response
        
        # DEBUG: Check if the prompt contains narrative content that should be relayed directly
        print(f"   🔍 Checking if content is narrative...")
        if _is_narrative_content(final_prompt):
            print(f"   📖 NARRATIVE DETECTED - Relaying story content directly")
            
            # Extract the actual story content from the prompt
            # Look for common patterns where story content appears
            story_content = final_prompt
            
            # If the content looks like a story prompt, extract just the story part
            if "Here is the story content:" in final_prompt:
                story_content = final_prompt.split("Here is the story content:")[1].strip()
            elif "**Story Content:**" in final_prompt:
                story_content = final_prompt.split("**Story Content:**")[1].strip()
            elif "---" in final_prompt and final_prompt.count("---") >= 2:
                # Content between --- markers is often the story
                parts = final_prompt.split("---")
                if len(parts) >= 3:
                    story_content = parts[1].strip()
            
            # Clean up any prompt artifacts
            story_content = story_content.replace("Customer:", "").replace("Elsie:", "").strip()
            
            # If we extracted story content, check if it needs chunking
            if story_content and story_content != final_prompt and len(story_content) > 100:
                print(f"   📖 Extracted story content ({len(story_content)} chars)")
                
                # Check if chunking is needed for large content
                if _should_use_chunking(story_content):
                    print(f"   📦 Story content requires chunking - returning directly without LLM processing")
                    return _return_content_in_chunks(story_content, user_message)
                else:
                    print(f"   📖 Returning story content directly without LLM processing")
                    # Add a brief Elsie introduction and return the content directly
                    elsie_intro = _create_story_introduction(user_message, len(story_content))
                    return f"{elsie_intro}\n\n{story_content}"
            
            # If extraction failed but we detected narrative, try to extract from the full prompt
            print(f"   📖 Attempting to extract narrative from full prompt...")
            extracted_narrative = _extract_narrative_from_prompt(final_prompt)
            if extracted_narrative and len(extracted_narrative) > 100:
                print(f"   📖 Extracted narrative from prompt ({len(extracted_narrative)} chars)")
                
                if _should_use_chunking(extracted_narrative):
                    print(f"   📦 Extracted narrative requires chunking - returning directly")
                    return _return_content_in_chunks(extracted_narrative, user_message)
                else:
                    elsie_intro = _create_story_introduction(user_message, len(extracted_narrative))
                    return f"{elsie_intro}\n\n{extracted_narrative}"
            
            # If we still can't extract clean narrative, fall back to the original processing
            print(f"   📖 Falling back to narrative processing...")
            narrative_result = _process_narrative_content(final_prompt, user_message, strategy)
            
            # Check if the narrative result needs chunking
            if _should_use_chunking(narrative_result):
                print(f"   📦 Narrative result requires chunking")
                return _process_content_chunks(narrative_result, user_message, strategy)
            
            return narrative_result
        
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
            print(f"   📦 Attempting chunked processing for complete content...")
            
            # Try to extract the full content and process in chunks
            if _is_narrative_content(final_prompt):
                return _process_content_chunks(final_prompt, user_message, strategy)
        
        # Post-processing and tracking logic...
        response_text = _post_process_response(response_text, strategy, user_message, conversation_history)

        # Cache the response
        response_cache[cache_key] = response_text
        return response_text
        
    except Exception as e:
        print(f"❌ Error in AI response generation: {e}")
        return get_mock_response(user_message)

def _process_narrative_content(content: str, user_message: str, strategy: Dict) -> str:
    """
    Processes narrative content to present it faithfully without personality overlay
    or language simplification, maintaining the sophistication from the wisdom module.
    """
    print(f"   📖 Processing narrative content with faithful presentation...")
    
    # Create a prompt that presents the content faithfully without personality overlay
    narrative_prompt = f"""You are Elsie, a holographic assistant. The user has requested story content, and you should present it faithfully as received, maintaining the original language sophistication and narrative structure.

Your task is to present the story content clearly and completely without adding personality commentary, analysis, or simplification. Preserve the original tone, language complexity, and narrative style.

User's request: {user_message}

Story content to present:
---
{content}
---

Present this story content faithfully, maintaining its original sophistication and narrative structure."""

    try:
        model = genai.GenerativeModel('gemma-3-27b-it')
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=8000,
            temperature=0.2  # Low temperature for faithful reproduction
        )

        response = model.generate_content(narrative_prompt, generation_config=generation_config)
        response_text = response.text.strip()
        
        print(f"   ✅ Narrative content processed faithfully ({len(response_text)} chars)")
        return response_text
        
    except Exception as e:
        print(f"   ❌ Error processing narrative content: {e}")
        # Fallback to returning the original content
        return content

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