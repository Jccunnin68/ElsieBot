"""
LLM Query Post Processor
========================

Post-processes large query results using gemini-2.0-flash-lite to create concise,
relevant summaries for the main AI engine. Includes context-aware fallback handling
for roleplay vs non-roleplay scenarios with character rule integration.
"""

import time
import random
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List
from datetime import datetime, timedelta
import google.generativeai as genai
from config import GEMMA_API_KEY

@dataclass
class ProcessingResult:
    """Result of LLM query processing with fallback information"""
    content: str
    was_processed: bool
    processing_status: str  # "success", "rate_limited", "error", "fallback"
    is_fallback_response: bool
    retry_after_minutes: Optional[int] = None
    original_data_size: int = 0
    processed_data_size: int = 0
    fallback_reason: Optional[str] = None

@dataclass
class CharacterContext:
    """Minimal character context - LLM handles all character processing"""
    roleplay_active: bool = False


class RateLimiter:
    """Handles rate limiting for gemini-2.0-flash-lite API calls"""
    
    def __init__(self):
        self.call_times = []
        self.daily_limit = 1000  # Conservative limit for gemini-2.0-flash-lite
        self.minute_limit = 60
        self.current_delay = 0
        self.last_rate_limit = None
        
    def can_make_request(self) -> Tuple[bool, int]:
        """Returns (can_make_request, retry_after_minutes)"""
        now = datetime.now()
        
        # Clean old call times (older than 24 hours)
        self.call_times = [t for t in self.call_times if (now - t).total_seconds() < 86400]
        
        # Check if we hit rate limit recently
        if self.last_rate_limit:
            time_since_limit = (now - self.last_rate_limit).total_seconds() / 60
            if time_since_limit < self.current_delay:
                return False, int(self.current_delay - time_since_limit) + 1
        
        # Check daily limit
        if len(self.call_times) >= self.daily_limit:
            return False, 60  # Try again in an hour
            
        # Check minute limit
        recent_calls = [t for t in self.call_times if (now - t).total_seconds() < 60]
        if len(recent_calls) >= self.minute_limit:
            return False, 1
            
        return True, 0
        
    def record_request(self):
        """Record a successful request"""
        self.call_times.append(datetime.now())
        
    def record_rate_limit(self):
        """Record a rate limit hit and calculate backoff"""
        self.last_rate_limit = datetime.now()
        self.current_delay = min(self.current_delay * 2 if self.current_delay > 0 else 5, 60)
        
    def get_retry_time(self) -> int:
        """Get minutes until next retry attempt"""
        if not self.last_rate_limit:
            return 0
        time_since_limit = (datetime.now() - self.last_rate_limit).total_seconds() / 60
        return max(0, int(self.current_delay - time_since_limit))


class ProcessingMetrics:
    """Tracks processing metrics for monitoring"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_processing = 0
        self.rate_limited_requests = 0
        self.fallback_responses = 0
        self.token_savings = 0
        self.daily_reset = datetime.now().date()
        
    def log_processing_attempt(self, result: ProcessingResult):
        """Log processing metrics for monitoring"""
        # Reset daily counters if needed
        if datetime.now().date() > self.daily_reset:
            self._reset_daily_counters()
            
        self.total_requests += 1
        
        if result.processing_status == "success":
            self.successful_processing += 1
            if result.original_data_size > 0 and result.processed_data_size > 0:
                self.token_savings += result.original_data_size - result.processed_data_size
        elif result.processing_status == "rate_limited":
            self.rate_limited_requests += 1
        
        # Count fallback responses separately (can overlap with rate_limited)
        if result.is_fallback_response:
            self.fallback_responses += 1
            
        print(f"📊 PROCESSING METRICS: Total={self.total_requests}, Success={self.successful_processing}, "
              f"Rate Limited={self.rate_limited_requests}, Fallbacks={self.fallback_responses}")
              
    def _reset_daily_counters(self):
        """Reset daily counters"""
        self.total_requests = 0
        self.successful_processing = 0
        self.rate_limited_requests = 0
        self.fallback_responses = 0
        self.token_savings = 0
        self.daily_reset = datetime.now().date()
        
    def get_daily_stats(self) -> Dict[str, int]:
        """Get daily processing statistics"""
        return {
            "total_requests": self.total_requests,
            "successful_processing": self.successful_processing,
            "rate_limited_requests": self.rate_limited_requests,
            "fallback_responses": self.fallback_responses,
            "token_savings": self.token_savings
        }


class LLMQueryProcessor:
    """
    Post-processes large query results using gemini-2.0-flash-lite
    to create concise, relevant summaries for the main AI engine.
    Enhanced with character rule integration for proper name disambiguation.
    """
    
    # New limits expressed as tokens (Gemini supports larger context windows).
    # Using a rough 4-chars-per-token heuristic to convert: 14 000 tokens ≈ 56 000 characters.
    PROCESSING_THRESHOLD = 56000  # Characters (~14k tokens)
    MAX_RETRIES = 3
    
    def __init__(self):
        self.client = self._initialize_gemini_client()
        self.rate_limiter = RateLimiter()
        self.metrics = ProcessingMetrics()
        
    def _initialize_gemini_client(self):
        """Initialize the Gemini client for gemini-2.0-flash-lite"""
        try:
            genai.configure(api_key=GEMMA_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash-lite')
            print("✅ LLM Query Processor initialized with gemini-2.0-flash-lite")
            return model
        except Exception as e:
            print(f"⚠️  Failed to initialize Gemini client: {e}")
            return None
            
    def _extract_character_context(self, raw_data: str, user_query: str) -> CharacterContext:
        """Extract minimal character context - LLM handles all character processing"""
        try:
            from ..ai_attention.state_manager import get_roleplay_state
            
            context = CharacterContext()
            
            # Only check roleplay state for logging/debugging purposes
            try:
                rp_state = get_roleplay_state()
                context.roleplay_active = rp_state.is_roleplaying
            except:
                context.roleplay_active = False
            
            return context
            
        except Exception as e:
            print(f"⚠️  Error extracting character context: {e}")
            return CharacterContext()
    
    def _build_character_processing_rules(self, character_context: CharacterContext) -> List[str]:
        """Build character processing rules dynamically from log_patterns.py"""
        try:
            # Import character corrections from log_patterns.py
            from .log_patterns import SHIP_SPECIFIC_CHARACTER_CORRECTIONS, FALLBACK_CHARACTER_CORRECTIONS
            
            character_rules = [
                f"- Roleplay Session Active: {character_context.roleplay_active}",
                "- Character Disambiguation Rules (APPLY THESE):"
            ]
            
            # Add ship-specific corrections
            character_rules.append("  SHIP-SPECIFIC CORRECTIONS:")
            for ship, corrections in SHIP_SPECIFIC_CHARACTER_CORRECTIONS.items():
                ship_corrections = []
                for incorrect, correct in corrections.items():
                    ship_corrections.append(f"'{incorrect}' → '{correct}'")
                character_rules.append(f"  * {ship.title()}: {', '.join(ship_corrections)}")
            
            # Add general character corrections
            character_rules.append("  GENERAL CHARACTER CORRECTIONS:")
            for incorrect, correct in FALLBACK_CHARACTER_CORRECTIONS.items():
                character_rules.append(f"  * '{incorrect}' → '{correct}'")
            
            # Add other processing rules
            character_rules.extend([
                "- DGM Character Control Patterns:",
                "  * Process [Character], Character:, (Character) patterns",
                "  * Handle DGM gamemaster accounts (liorexus, isis, cygnus, illuice, captain_rien)",
                "- [DOIC] Channel Rules:",
                "  * Content in [DOIC] channels is primarily narration or other character dialogue",
                "  * Rarely will [DOIC] content be from the character@account_name speaking",
                "  * Treat [DOIC] content as environmental/narrative description",
                "- OOC Content Filtering:",
                "  * Filter out ((text)), //text, [ooc text], ooc: patterns",
                "- ⚠️ IMPORTANT: PERFORM CHARACTER DISAMBIGUATION",
                "- Apply character name corrections using ship context",
                "- Resolve ambiguous character names with proper ranks/titles",
                "- Use surrounding text context for ambiguous names like 'tolena' and 'blaine'"
            ])
            
            return character_rules
            
        except Exception as e:
            print(f"⚠️  Error building character processing rules: {e}")
            # Fallback to basic rules if import fails
            return [
                f"- Roleplay Session Active: {character_context.roleplay_active}",
                "- Character Disambiguation Rules: Apply basic character name corrections",
                "- DGM Character Control Patterns: Process [Character], Character:, (Character) patterns",
                "- [DOIC] Channel Rules: Treat as narration/environmental description",
                "- OOC Content Filtering: Filter out ((text)), //text, [ooc text], ooc: patterns",
                "- ⚠️ IMPORTANT: PERFORM CHARACTER DISAMBIGUATION"
            ]
            
    def process_query_results(self, query_type: str, raw_data: str, user_query: str, 
                            is_roleplay: bool = False, force_processing: bool = False) -> ProcessingResult:
        """Main processing entry point with character rule integration and forced processing support"""
        print(f"🔄 LLM PROCESSING: type='{query_type}', size={len(raw_data)} chars, roleplay={is_roleplay}, force={force_processing}")
        
        original_size = len(raw_data)
        
        # NEW: Force processing for log content regardless of size
        if query_type == "logs" or force_processing:
            print(f"   🎯 FORCED PROCESSING: Log content will be processed regardless of size")
            # Check rate limits
            can_process, retry_minutes = self.rate_limiter.can_make_request()
            if not can_process:
                print(f"⏳ Rate limited, retry in {retry_minutes} minutes")
                fallback_content = self._generate_fallback_response(query_type, user_query, is_roleplay, retry_minutes)
                result = ProcessingResult(
                    content=fallback_content,
                    was_processed=False,
                    processing_status="rate_limited",
                    is_fallback_response=True,
                    retry_after_minutes=retry_minutes,
                    original_data_size=original_size,
                    processed_data_size=len(fallback_content),
                    fallback_reason="rate_limited"
                )
                self.metrics.log_processing_attempt(result)
                return result
            
            # Process with character rules (forced)
            return self._process_with_character_rules(raw_data, user_query, query_type, is_roleplay, original_size)
        
        # Existing size-based logic for non-log content
        if len(raw_data) < self.PROCESSING_THRESHOLD:
            return ProcessingResult(
                content=raw_data,
                was_processed=False,
                processing_status="not_needed",
                is_fallback_response=False,
                original_data_size=original_size,
                processed_data_size=original_size
            )
            
        # Check rate limits for regular processing
        can_process, retry_minutes = self.rate_limiter.can_make_request()
        if not can_process:
            print(f"⏳ Rate limited, retry in {retry_minutes} minutes")
            fallback_content = self._generate_fallback_response(query_type, user_query, is_roleplay, retry_minutes)
            result = ProcessingResult(
                content=fallback_content,
                was_processed=False,
                processing_status="rate_limited",
                is_fallback_response=True,
                retry_after_minutes=retry_minutes,
                original_data_size=original_size,
                processed_data_size=len(fallback_content),
                fallback_reason="rate_limited"
            )
            self.metrics.log_processing_attempt(result)
            return result
            
        # Regular processing for large non-log content
        return self._process_with_character_rules(raw_data, user_query, query_type, is_roleplay, original_size)
    
    def _process_with_character_rules(self, raw_data: str, user_query: str, query_type: str, 
                                    is_roleplay: bool, original_size: int) -> ProcessingResult:
        """Unified processing method with character rule integration"""
        # Extract minimal character context (LLM handles all character processing)
        character_context = self._extract_character_context(raw_data, user_query)
        print(f"🎭 CHARACTER CONTEXT: roleplay_active={character_context.roleplay_active} (LLM handles all character processing)")
            
        # Attempt processing
        try:
            # Determine if we need summarization or just character processing
            needs_summarization = len(raw_data) >= self.PROCESSING_THRESHOLD
            print(f"   📊 PROCESSING DECISION: needs_summarization={needs_summarization} (threshold={self.PROCESSING_THRESHOLD})")
            
            if query_type == "logs":
                if needs_summarization:
                    print(f"   📝 LOG PROCESSING: Character processing + summarization ({len(raw_data)} chars)")
                    processed_content = self._process_log_data_with_character_rules(raw_data, user_query, character_context)
                else:
                    print(f"   🎭 LOG PROCESSING: Character processing only (no summarization) ({len(raw_data)} chars)")
                    processed_content = self._process_log_character_only(raw_data, user_query, character_context)
            else:
                print(f"   📋 GENERAL PROCESSING: Character processing + summarization ({len(raw_data)} chars)")
                processed_content = self._process_general_data_with_character_rules(raw_data, user_query, character_context)
                
            if processed_content:
                self.rate_limiter.record_request()
                result = ProcessingResult(
                    content=processed_content,
                    was_processed=True,
                    processing_status="success",
                    is_fallback_response=False,
                    original_data_size=original_size,
                    processed_data_size=len(processed_content)
                )
                print(f"✅ Processing successful: {original_size} → {len(processed_content)} chars")
                self.metrics.log_processing_attempt(result)
                return result
            else:
                print(f"❌ LLM returned empty content")
                raise Exception("Empty response from LLM")
                
        except Exception as e:
            print(f"❌ Processing failed: {e}")
            fallback_content = self._generate_fallback_response(query_type, user_query, is_roleplay, 0)
            result = ProcessingResult(
                content=fallback_content,
                was_processed=False,
                processing_status="error",
                is_fallback_response=True,
                original_data_size=original_size,
                processed_data_size=len(fallback_content),
                fallback_reason=str(e)
            )
            self.metrics.log_processing_attempt(result)
            return result
        
    def _process_log_data(self, raw_logs: str, user_query: str) -> str:
        """Specialized log processing with character dialogue parsing"""
        prompt = self._create_log_summary_prompt(raw_logs, user_query)
        return self._call_llm_with_prompt(prompt)
    
    def _process_log_data_with_character_rules(self, raw_logs: str, user_query: str, 
                                             character_context: CharacterContext) -> str:
        """Enhanced log processing with character rule integration"""
        prompt = self._create_character_aware_log_summary_prompt(raw_logs, user_query, character_context)
        return self._call_llm_with_prompt(prompt)
        
    def _process_general_data(self, raw_data: str, user_query: str) -> str:
        """General data summarization"""
        prompt = self._create_general_summary_prompt(raw_data, user_query)
        return self._call_llm_with_prompt(prompt)
    
    def _process_general_data_with_character_rules(self, raw_data: str, user_query: str,
                                                 character_context: CharacterContext) -> str:
        """Enhanced general data processing with character rule integration"""
        prompt = self._create_character_aware_general_summary_prompt(raw_data, user_query, character_context)
        return self._call_llm_with_prompt(prompt)
    
    def _process_log_character_only(self, raw_logs: str, user_query: str, 
                                  character_context: CharacterContext) -> str:
        """Character processing only for log content without summarization"""
        prompt = self._create_character_processing_only_prompt(raw_logs, user_query, character_context)
        return self._call_llm_with_prompt(prompt)
        
    def _create_log_summary_prompt(self, logs: str, query: str) -> str:
        """Create optimized prompt for log processing with minimal summarization"""
        return f"""You are a mission log processor. Process the following mission logs in response to this query: "{query}"

CRITICAL LENGTH REQUIREMENT: Your response should be approximately 30000-33000 characters. Use ALL available space to preserve as much log content as possible.

INSTRUCTIONS:
- PRESERVE as much original log content as possible - minimize summarization
- Include ALL character dialogue, actions, and interactions
- Maintain ALL character names, dates, locations, and specific details
- Keep chronological order and preserve log structure
- Include ALL significant events, decisions, and outcomes
- Preserve character personalities through their actual words and actions
- Keep ALL mission context, technical details, and background information
- MINIMAL SUMMARIZATION: Only condense if absolutely necessary to fit 33000 characters
- PRIORITY: Completeness over brevity - use every available character
- Preserve the narrative flow and dramatic moments from the logs

MISSION LOGS TO PROCESS:
{logs}

Process these logs with minimal summarization, preserving as much original content as possible while staying under 14000 characters. Focus on keeping the complete story intact."""

    def _create_character_aware_log_summary_prompt(self, logs: str, query: str, 
                                                 character_context: CharacterContext) -> str:
        """Create character-aware prompt for log summarization with disambiguation rules"""
        
        # Build character processing rules dynamically from log_patterns.py
        character_rules = self._build_character_processing_rules(character_context)
        character_context_text = "\n".join(character_rules)
        
        return f"""You are a mission log processor with character rule awareness. Process the following mission logs in response to this query: "{query}"

CHARACTER PROCESSING RULES:
{character_context_text}

CRITICAL LENGTH REQUIREMENT: Your response should be approximately 12000-13800 characters. Use ALL available space to preserve as much log content as possible.

INSTRUCTIONS:
- APPLY character disambiguation rules using ship context
- Process DGM character control patterns: [Character], Character:, (Character)
- Filter out OOC content: ((text)), //text, [ooc text], ooc:
- Handle [DOIC] channel content as narration/environmental description
- Apply character name corrections and resolve ambiguities
- PRESERVE as much original log content as possible - minimize summarization
- Include ALL character dialogue, actions, and interactions
- Maintain ALL character names, dates, locations, and specific details
- Keep chronological order and preserve log structure
- Include ALL significant events, decisions, and outcomes
- Preserve character personalities through their actual words and actions
- Keep ALL mission context, technical details, and background information
- MINIMAL SUMMARIZATION: Only condense if absolutely necessary to fit 14000 characters
- PRIORITY: Completeness over brevity - use every available character
- Preserve the narrative flow and dramatic moments from the logs

MISSION LOGS TO PROCESS:
{logs}

Process these logs with character rules applied and minimal summarization, preserving as much original content as possible while staying under 14000 characters. Focus on keeping the complete story intact with proper character disambiguation."""

    def _create_general_summary_prompt(self, data: str, query: str) -> str:
        """Create optimized prompt for general data"""
        return f"""You are a database analyst. Process the following information in response to this query: "{query}"

CRITICAL LENGTH REQUIREMENT: Your response should be approximately 30000 characters. This is a SUBSTANTIAL response - use most of the available space to provide comprehensive information.

INSTRUCTIONS:
- Extract key facts and relationships relevant to the query
- Preserve important names, dates, specifications, and details
- Organize information logically and clearly
- Include comprehensive context and background information
- Maintain accuracy of all factual content
- Focus on information that directly answers the user's question
- TARGET LENGTH: Aim for 30000 characters - this should be a comprehensive, detailed response
- Use the full available space to provide thorough coverage of the content
- Only summarize if absolutely necessary to fit within the character limit

DATA TO PROCESS:
{data}

Provide a well-organized response that thoroughly addresses the user's query while preserving important factual information and context. ENSURE YOUR RESPONSE IS UNDER 30000 CHARACTERS."""

    def _create_character_aware_general_summary_prompt(self, data: str, query: str,
                                                     character_context: CharacterContext) -> str:
        """Create character-aware prompt for general data with disambiguation rules"""
        
        # Build character processing rules dynamically from log_patterns.py
        character_rules = self._build_character_processing_rules(character_context)
        character_context_text = "\n".join(character_rules)
        
        return f"""You are a database analyst with character rule awareness. Process the following information in response to this query: "{query}"

CHARACTER PROCESSING RULES:
{character_context_text}

CRITICAL LENGTH REQUIREMENT: Your response should be approximately 12000-13800 characters. This is a SUBSTANTIAL response - use most of the available space to provide comprehensive information.

INSTRUCTIONS:
- APPLY character disambiguation rules using ship context
- Process character designations and resolve ambiguities
- Filter out OOC content when appropriate
- Handle [DOIC] channel content as narration/environmental description
- Extract key facts and relationships relevant to the query
- Preserve important names with proper formatting and ranks/titles
- Organize information logically and clearly
- Include comprehensive context and background information
- Maintain accuracy of all factual content
- Focus on information that directly answers the user's question
- TARGET LENGTH: Aim for 12000-13800 characters - this should be a comprehensive, detailed response
- Use the full available space to provide thorough coverage of the content
- Only summarize if absolutely necessary to fit within the character limit

DATA TO PROCESS:
{data}

Provide a well-organized response that thoroughly addresses the user's query while preserving important factual information and context. APPLY CHARACTER DISAMBIGUATION AND FILTERING RULES. ENSURE YOUR RESPONSE IS UNDER 14000 CHARACTERS."""

    def _create_character_processing_only_prompt(self, logs: str, query: str, 
                                               character_context: CharacterContext) -> str:
        """Create prompt for character processing only (no summarization)"""
        
        # Build character processing rules dynamically from log_patterns.py
        character_rules = self._build_character_processing_rules(character_context)
        character_context_text = "\n".join(character_rules)
        
        return f"""You are a mission log character processor. Apply character disambiguation and formatting rules to the following content.

CHARACTER PROCESSING RULES:
{character_context_text}

CRITICAL INSTRUCTIONS:
- DO NOT SUMMARIZE OR SHORTEN THE CONTENT
- Return the FULL ORIGINAL CONTENT with character processing applied
- APPLY character disambiguation rules using ship context
- Process DGM character control patterns: [Character], Character:, (Character)
- Filter out OOC content: ((text)), //text, [ooc text], ooc:
- Handle [DOIC] channel content as narration/environmental description
- Apply character name corrections and resolve ambiguities
- Preserve ALL original dialogue, actions, and narrative content
- Maintain original structure and formatting
- Only change character names and filter OOC content

CONTENT TO PROCESS:
{logs}

Return the full content with character disambiguation and filtering applied. DO NOT SUMMARIZE."""

    def _call_llm_with_prompt(self, prompt: str) -> str:
        """Call LLM with the given prompt and validate response length"""
        if not self.client:
            raise Exception("Gemini client not initialized")
            
        print(f"🔄 LLM CALL: Prompt size = {len(prompt)} chars")
        
        try:
            # Apply explicit generation limits – Gemini can output up to 6 000 tokens safely
            from google.generativeai.types import GenerationConfig

            generation_config = GenerationConfig(
                max_output_tokens=13000,  # Allow up to ~52k chars (~13k tokens)
                temperature=0.7
            )

            response = self.client.generate_content(prompt, generation_config=generation_config)
            if response and response.text:
                content = response.text.strip()
                print(f"✅ LLM RESPONSE: Received {len(content)} chars")
                
                # No manual truncation – rely on GenerationConfig token limit instead.
                
                return content
            else:
                raise Exception("Empty response from Gemini")
        except Exception as e:
            print(f"❌ LLM CALL FAILED: {e}")
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                self.rate_limiter.record_rate_limit()
                raise Exception(f"Rate limited: {e}")
            else:
                raise Exception(f"LLM call failed: {e}")
                
    def _generate_fallback_response(self, query_type: str, user_query: str, 
                                  is_roleplay: bool, retry_minutes: int) -> str:
        """Generate context-appropriate fallback responses"""
        if is_roleplay:
            return self._generate_roleplay_fallback(query_type, user_query)
        else:
            return self._generate_nonroleplay_fallback(query_type, retry_minutes)
            
    def _generate_roleplay_fallback(self, query_type: str, user_query: str) -> str:
        """Generate in-character responses when processing fails"""
        
        roleplay_fallbacks = {
            "logs": [
                "I'm having trouble accessing those records right now. My memory banks seem a bit foggy on that particular mission.",
                "Those logs aren't coming to mind at the moment. Perhaps we could discuss something else while I sort through my data?",
                "I don't recall that information right now. My stellar cartography databases are being a bit stubborn today.",
                "My access to those mission records seems to be experiencing some interference. Could we try a different approach?"
            ],
            "general": [
                "I'm drawing a blank on that topic right now. My knowledge systems seem to be taking a little break.",
                "That information isn't readily available in my current memory banks. Perhaps I can help with something else?",
                "I don't have that data at my fingertips right now. My databases are being rather selective today.",
                "My information networks are having a quiet moment. Is there something else I can assist you with?"
            ],
            "character": [
                "I'm not recalling much about them at the moment. My personnel files seem to be having a quiet moment.",
                "That person isn't coming to mind right now. Perhaps you could refresh my memory with some details?",
                "My character databases are being a bit elusive today. Could you tell me more about who you're asking about?"
            ]
        }
        
        # Select appropriate response based on query type
        fallback_list = roleplay_fallbacks.get(query_type, roleplay_fallbacks["general"])
        return random.choice(fallback_list)
        
    def _generate_nonroleplay_fallback(self, query_type: str, retry_minutes: int) -> str:
        """Generate system-level responses when processing fails"""
        
        if retry_minutes > 0:
            if retry_minutes == 1:
                return f"Deep data searches are currently rate limited. Please try again in {retry_minutes} minute. For immediate assistance, try a more specific query."
            else:
                return f"Deep data searches are currently rate limited. Please try again in {retry_minutes} minutes. For immediate assistance, try a more specific query."
        else:
            return "Data processing services are temporarily unavailable. The system will automatically retry your request. You can also try rephrasing your query to be more specific."
            
    def get_processing_stats(self) -> Dict[str, int]:
        """Get current processing statistics"""
        return self.metrics.get_daily_stats()


# Global instance for use across the application
_processor_instance = None

def get_llm_processor() -> LLMQueryProcessor:
    """Get the global LLM processor instance"""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = LLMQueryProcessor()
    return _processor_instance


def is_fallback_response(content: str) -> bool:
    """Check if content is a fallback response"""
    roleplay_indicators = [
        "don't recall", "drawing a blank", "not coming to mind", 
        "memory banks seem", "databases are being", "having a quiet moment",
        "trouble accessing", "isn't readily available"
    ]
    
    system_indicators = [
        "rate limited", "try again", "temporarily unavailable",
        "processing services", "system will automatically retry"
    ]
    
    content_lower = content.lower()
    return (any(indicator in content_lower for indicator in roleplay_indicators) or
            any(indicator in content_lower for indicator in system_indicators))


def should_process_data(data: str) -> bool:
    """Determine if data should be processed based on size and content"""
    return len(data) > LLMQueryProcessor.PROCESSING_THRESHOLD 