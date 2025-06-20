"""
AI Engine for Response Generation
=================================

This module handles the actual generation of AI responses, including chunking for large content,
caching, and response post-processing. Updated to use pythonic service classes with dependency injection.
"""

import google.generativeai as genai
from typing import List, Dict, Optional, TYPE_CHECKING, Any
from config import GEMMA_API_KEY

from ..ai_logic.response_decision import ResponseDecision

if TYPE_CHECKING:
    
    from ..ai_emotion.poetic_service import PoeticResponseService
    from ..ai_logic.context_analysis_service import ContextAnalysisService
    from ..utilities.content_filter_service import ContentFilterService
    from ..utilities.date_conversion_service import DateConversionService
    from ..utilities.text_utility_service import TextUtilityService


class AIEngine:
    """
    AI Engine for response generation with proper instance state management and service injection.
    """
    
    # Constants
    MAX_PROMPT_CHARS = 32000  # Approx. 8000 tokens as a safe upper limit
    SUMMARIZATION_TARGET_CHARS = 30000  # Give it some buffer
    MAX_OUTPUT_TOKENS = 8000  # Maximum output tokens per chunk
    CHUNK_SIZE_CHARS = 30000  # Approximate characters per chunk to stay under output limits
    CHUNK_OVERLAP_CHARS = 2000  # Overlap between chunks to maintain context
    
    def __init__(self, 
                 poetic_service: Optional['PoeticResponseService'] = None,
                 context_analysis_service: Optional['ContextAnalysisService'] = None,
                 content_filter_service: Optional['ContentFilterService'] = None,
                 date_conversion_service: Optional['DateConversionService'] = None,
                 text_utility_service: Optional['TextUtilityService'] = None):
        """
        Initialize the AI Engine with instance state and service dependencies.
        
        Args:
            poetic_service: Service for poetic responses (for context information)
            context_analysis_service: Service for context analysis
            content_filter_service: Service for content filtering
            date_conversion_service: Service for date conversion
            text_utility_service: Service for text utilities
        """
        self.response_cache = {}  # Instance-level cache instead of global
        
        # Store service dependencies
        self._poetic_service = poetic_service
        self._context_analysis_service = context_analysis_service
        self._content_filter_service = content_filter_service
        self._date_conversion_service = date_conversion_service
        self._text_utility_service = text_utility_service
        
        print("✓ AIEngine initialized with instance-level caching and service injection")
    
    @property
    def poetic_service(self) -> 'PoeticResponseService':
        """Lazy-load poetic service."""
        if self._poetic_service is None:
            try:
                from ..service_container import get_poetic_service
                self._poetic_service = get_poetic_service()
            except ImportError:
                # Fallback for testing
                from ..ai_emotion.poetic_service import PoeticResponseService
                self._poetic_service = PoeticResponseService()
        return self._poetic_service
    
    @property
    def context_analysis_service(self) -> 'ContextAnalysisService':
        """Lazy-load context analysis service."""
        if self._context_analysis_service is None:
            try:
                from ..service_container import get_context_analysis_service
                self._context_analysis_service = get_context_analysis_service()
            except ImportError:
                # Fallback for testing
                from ..ai_logic.context_analysis_service import ContextAnalysisService
                self._context_analysis_service = ContextAnalysisService()
        return self._context_analysis_service
    
    @property
    def content_filter_service(self) -> 'ContentFilterService':
        """Lazy-load content filter service."""
        if self._content_filter_service is None:
            try:
                from ..service_container import get_content_filter_service
                self._content_filter_service = get_content_filter_service()
            except ImportError:
                # Fallback for testing
                from ..utilities.content_filter_service import ContentFilterService
                self._content_filter_service = ContentFilterService()
        return self._content_filter_service
    
    @property
    def date_conversion_service(self) -> 'DateConversionService':
        """Lazy-load date conversion service."""
        if self._date_conversion_service is None:
            try:
                from ..service_container import get_date_conversion_service
                self._date_conversion_service = get_date_conversion_service()
            except ImportError:
                # Fallback for testing
                from ..utilities.date_conversion_service import DateConversionService
                self._date_conversion_service = DateConversionService()
        return self._date_conversion_service
    
    @property
    def text_utility_service(self) -> 'TextUtilityService':
        """Lazy-load text utility service."""
        if self._text_utility_service is None:
            try:
                from ..service_container import get_text_utility_service
                self._text_utility_service = get_text_utility_service()
            except ImportError:
                # Fallback for testing
                from ..utilities.text_utility_service import TextUtilityService
                self._text_utility_service = TextUtilityService()
        return self._text_utility_service

    def generate_response_with_decision(self, decision: ResponseDecision, user_message: str, conversation_history: list) -> str:
        """
        AI response generation using a pre-made decision.
        For standard mode: directly relay wisdom engine content.
        For roleplay mode: use AI engine processing.
        """
        try:
            if not GEMMA_API_KEY:
                return "I'm currently unable to access my AI capabilities. Please check the API configuration."

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
                if self._should_use_chunking(wisdom_content):
                    print(f"   📦 Content requires chunking - returning in parts")
                    return self._return_content_in_chunks(wisdom_content, user_message)
                
                # Return wisdom engine content directly
                return wisdom_content
            
            # ALL OTHER MODES: Use AI engine processing (roleplay, simple_chat, general, etc.)
            print(f"   🤖 AI ENGINE MODE ({approach}) - Processing with AI engine")
            final_prompt = wisdom_content
            
            # If the prompt is too long, summarize it using an LLM
            if len(final_prompt) > self.MAX_PROMPT_CHARS:
                final_prompt = self._summarize_prompt_context(final_prompt, user_message)

            print(f"   💬 Final prompt length: {len(final_prompt)} characters")

            # Check cache first
            cache_key = (final_prompt, user_message)
            if cache_key in self.response_cache:
                print("   ✅ CACHE HIT - Returning cached response.")
                return self.response_cache[cache_key]
            
            model = genai.GenerativeModel('gemma-3-27b-it')
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=8000,
                temperature=0.8
            )

            response = model.generate_content(final_prompt, generation_config=generation_config)
            response_text = response.text.strip()
            
            # Check if the response might be truncated and needs chunking
            estimated_full_size = self._estimate_output_size(final_prompt)
            if estimated_full_size > self.MAX_OUTPUT_TOKENS and len(response_text) >= self.MAX_OUTPUT_TOKENS * 3:  # Rough char estimate
                print(f"   ⚠️  Response may be truncated ({len(response_text)} chars, estimated {estimated_full_size} tokens)")
                print(f"   📦 Content appears truncated - returning what we have")
                # For roleplay mode, return the partial response rather than trying to chunk
            
            # Post-processing and tracking logic for roleplay...
            response_text = self._post_process_response(response_text, strategy, user_message, conversation_history)

            # Cache the response
            self.response_cache[cache_key] = response_text
            return response_text
            
        except Exception as e:
            print(f"❌ Error in AI response generation: {e}")
            import traceback
            traceback.print_exc()
            return "I'm experiencing some technical difficulties. Please try again in a moment."

    def _summarize_prompt_context(self, long_prompt: str, user_message: str) -> str:
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
Your task is to summarize this context. The summary must be less than {self.SUMMARIZATION_TARGET_CHARS} characters but use as much as possible.

CRITICAL INSTRUCTIONS:
-FORBIDDEN: You are not to comment on the context and pretend you are a Narrative consultant.
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
            start_index = len(long_prompt) - self.SUMMARIZATION_TARGET_CHARS
            return "[... context truncated due to length ...]\\n" + long_prompt[start_index:]

    def _return_content_in_chunks(self, content: str, user_message: str) -> str:
        """
        Returns large content in chunks without LLM processing.
        """
        print(f"   📦 Returning content in chunks directly without LLM processing")
        
        chunks = self._split_content_into_chunks(content)
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

    def _estimate_output_size(self, content: str) -> int:
        """
        Estimates the output size in tokens based on content length.
        Uses the text utility service for consistent token estimation.
        """
        return self.text_utility_service.estimate_token_count(content)

    def _should_use_chunking(self, content: str) -> bool:
        """
        Determines if content should be processed in chunks based on estimated output size.
        """
        estimated_tokens = self._estimate_output_size(content)
        return estimated_tokens > self.MAX_OUTPUT_TOKENS or len(content) > self.CHUNK_SIZE_CHARS

    def _split_content_into_chunks(self, content: str) -> List[str]:
        """
        Splits large content into smaller chunks with overlap to maintain context.
        Tries to split at natural boundaries like paragraph breaks.
        """
        if len(content) <= self.CHUNK_SIZE_CHARS:
            return [content]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(content):
            # Calculate chunk end position
            chunk_end = min(current_pos + self.CHUNK_SIZE_CHARS, len(content))
            
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
            current_pos = max(chunk_end - self.CHUNK_OVERLAP_CHARS, current_pos + 1)
        
        print(f"   📦 Split content into {len(chunks)} chunks")
        return chunks

    def _post_process_response(self, response_text: str, strategy: Dict, user_message: str, conversation_history: List[str]) -> str:
        """Helper function to apply all post-processing to the generated text using service classes."""
        # Filter out AI-generated conversation continuations using content filter service
        response_text = self.content_filter_service.remove_conversation_continuations(response_text)
        
        # Determine if this is a roleplay response
        is_roleplay_response = strategy.get('approach', '').startswith('roleplay_')
        
        # Filter meeting information unless it's a non-roleplay schedule query
        schedule_terms = ['schedule', 'meeting', 'time', 'when', 'gm', 'game master']
        is_schedule_query = any(word in user_message.lower() for word in schedule_terms)
        if is_roleplay_response or not is_schedule_query:
            response_text = self.content_filter_service.filter_meeting_info(response_text)
        
        # Apply Star Trek date conversion ONLY for roleplay queries
        if is_roleplay_response:
            response_text = self.date_conversion_service.convert_earth_date_to_star_trek(response_text)
        
        # Poetic circuit for casual dialogue using poetic service
        if strategy.get('approach') in ['simple_chat', 'general'] and self.poetic_service.should_trigger_poetic_circuit(user_message, conversation_history):
            print(f"🎭 POETIC SHORT CIRCUIT TRIGGERED")
            response_text = self.poetic_service.get_poetic_response(user_message, response_text)
            
        # Roleplay-specific processing
        if is_roleplay_response:
            # Convert to third person emotes and strip Discord formatting
            response_text = self._convert_to_third_person_emotes(response_text)
            response_text = self.content_filter_service.clean_discord_formatting(response_text)
            
            # Track who Elsie addressed in her response using context analysis service
            try:
                from ..service_container import get_roleplay_state
                rp_state = get_roleplay_state()
                turn_number = len(conversation_history) + 1
                addressed_character = self.context_analysis_service.detect_who_elsie_addressed(response_text, user_message)
                if addressed_character:
                    rp_state.set_last_character_addressed(addressed_character)
                    print(f"   📝 TRACKING UPDATE: Elsie addressed {addressed_character}")

                if not rp_state.turn_history or rp_state.turn_history[-1][1] != "Elsie":
                    rp_state.mark_response_turn(turn_number)
            except ImportError:
                print("   ⚠️  Could not access roleplay state for tracking")

        return response_text
    
    def _convert_to_third_person_emotes(self, text: str) -> str:
        """
        Convert first-person emotes to third-person for roleplay consistency.
        This method encapsulates the logic that was previously in conversation_utils.
        """
        if not text:
            return text
        
        # First-person to third-person conversions
        conversions = [
            ("I ", "Elsie "),
            (" I ", " Elsie "),
            (" my ", " her "),
            (" mine", " hers"),
            (" myself", " herself"),
            ("*I ", "*Elsie "),
            ("* I ", "* Elsie "),
            ("*my ", "*her "),
            ("* my ", "* her "),
        ]
        
        converted_text = text
        for first_person, third_person in conversions:
            converted_text = converted_text.replace(first_person, third_person)
        
        return converted_text

    def generate_response_with_strategy(self, user_message: str, strategy: Dict[str, Any], conversation_history: list) -> str:
        """
        Generate AI response using a strategy dictionary.
        
        This is a simplified interface that creates a ResponseDecision internally
        and processes it through the main generation pipeline.
        
        Args:
            user_message: The user's message
            strategy: Strategy dictionary with approach, context, and hints
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response string
        """
        from ..ai_logic.response_decision import ResponseDecision
        
        try:
            # Build a simple chat prompt - all interactions go through LLM now
            prompt = self._build_simple_chat_prompt(user_message, strategy, conversation_history)
            
            # Create a ResponseDecision with the prompt as pre_generated_response
            decision = ResponseDecision(
                needs_ai_generation=True,
                pre_generated_response=prompt,
                strategy=strategy
            )
            
            # Process through the main generation pipeline
            return self.generate_response_with_decision(decision, user_message, conversation_history)
            
        except Exception as e:
            print(f"❌ Error in generate_response_with_strategy: {e}")
            import traceback
            traceback.print_exc()
            return "I'm experiencing some technical difficulties. Please try again in a moment."
    
    def _build_simple_chat_prompt(self, user_message: str, strategy: Dict[str, Any], conversation_history: list) -> str:
        """
        Build a simple chat prompt for basic interactions.
        
        Args:
            user_message: The user's message
            strategy: Strategy with context information
            conversation_history: Previous messages
            
        Returns:
            Formatted prompt string
        """
        context_type = strategy.get('context_type', 'general_chat')
        personality = strategy.get('personality_context', 'complete_self')
        hints = strategy.get('prompt_hints', [])
        
        # Build personality context
        personality_instruction = ""
        if personality == 'bartender':
            personality_instruction = "You are Elsie, a holographic bartender aboard a starship. You're knowledgeable about drinks, attentive to customers, and maintain a professional yet warm demeanor."
        elif personality == 'stellar_cartographer':
            personality_instruction = "You are Elsie, a holographic stellar cartographer and science officer. You're knowledgeable about space, navigation, and scientific phenomena."
        elif personality == 'dance_instructor':
            personality_instruction = "You are Elsie, a holographic dance instructor. You're graceful, encouraging, and knowledgeable about various dance forms and movement."
        else:
            personality_instruction = "You are Elsie, a sophisticated holographic assistant aboard a starship. You're helpful, intelligent, and maintain an elegant presence."
        
        # Build context-specific instructions
        context_instruction = ""
        if context_type == 'greeting':
            context_instruction = "The user is greeting you. Respond warmly and establish your presence. Make them feel welcome."
        elif context_type == 'farewell':
            context_instruction = "The user is saying goodbye. Acknowledge their departure warmly but leave the door open for future interaction."
        elif context_type == 'drink_service':
            context_instruction = "The user is asking about drinks or bar service. Use your bartender expertise to help them."
        elif context_type == 'status_inquiry':
            context_instruction = "The user is asking how you are or about your status. Share your current state while maintaining character."
        else:
            context_instruction = "Engage in natural conversation while maintaining your character and being helpful."
        
        # Build conversation history context
        history_context = ""
        if conversation_history:
            recent_history = conversation_history[-3:]  # Last 3 exchanges
            history_context = "\n\nRecent conversation:\n"
            for i, msg in enumerate(recent_history):
                history_context += f"{i+1}. {msg}\n"
        
        # Build the complete prompt
        prompt = f"""You are Elsie, a holographic assistant. {personality_instruction}

{context_instruction}

Response guidelines:
- Be authentic and maintain character consistency
- Use appropriate emotes in *asterisks* when natural
- Keep responses conversational and engaging
- Match the tone and context of the interaction
{history_context}

User: {user_message}
Elsie:"""
        
        return prompt


# REMOVED: Global functions replaced by AIEngine class
# All functionality is now encapsulated in the AIEngine class
# Use service_container.get_ai_engine() to access the instance 