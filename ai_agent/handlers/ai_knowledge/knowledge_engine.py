"""
Knowledge Engine - LLM Query Post-Processor
===========================================

This engine post-processes large query results using a fast LLM to create concise,
relevant summaries for the main AI engine. It is simplified to three clear query types:
- LOGS: Character processing + summarization (for mission logs)
- SHIPS: Direct summarization (for ship information)
- GENERAL: Direct summarization (for all other content)
"""

import time
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
    """Minimal character context - only used for logs processing"""
    pass  # No roleplay state dependencies


class RateLimiter:
    """Handles rate limiting for gemini-2.0-flash-lite API calls"""
    
    def __init__(self):
        self.call_times = []
        self.daily_limit = 1350  # Conservative limit for gemini-2.0-flash-lite
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


class KnowledgeEngine:
    """
    Post-processes large query results using a fast LLM to create concise,
    relevant summaries for the main AI engine.
    
    Simplified to three clear query types:
    - LOGS: Character processing + summarization (for mission logs)
    - SHIPS: Direct summarization (for ship information)  
    - GENERAL: Direct summarization (for all other content)
    """
    
    # Processing threshold for when to use LLM processing
    PROCESSING_THRESHOLD = 56000  # Characters (~14k tokens) - input threshold for processing
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
            print("✅ Knowledge Engine initialized with gemini-1.5-flash-latest")
            return model
        except Exception as e:
            print(f"⚠️  Failed to initialize Gemini client: {e}")
            return None
            
    def process_query_results(self, query_type: str, raw_data: str, user_query: str, 
                             force_processing: bool = False) -> ProcessingResult:
        """Main processing entry point with simplified three-way routing"""
        print(f"🔄 LLM PROCESSING: type='{query_type}', size={len(raw_data)} chars, force={force_processing}")
        
        original_size = len(raw_data)
        
        # Force processing for log content regardless of size
        if query_type == "logs" or force_processing:
            print(f"   🎯 FORCED PROCESSING: Log content will be processed regardless of size")
        # Check size threshold for non-log content
        elif len(raw_data) < self.PROCESSING_THRESHOLD:
            return ProcessingResult(
                content=raw_data,
                was_processed=False,
                processing_status="not_needed",
                is_fallback_response=False,
                original_data_size=original_size,
                processed_data_size=original_size
            )
            
        # Check rate limits
        can_process, retry_minutes = self.rate_limiter.can_make_request()
        if not can_process:
            print(f"⏳ Rate limited, retry in {retry_minutes} minutes")
            result = ProcessingResult(
                content="LLM_PROCESSOR_FALLBACK_RATE_LIMITED",
                was_processed=False,
                processing_status="rate_limited",
                is_fallback_response=True,
                retry_after_minutes=retry_minutes,
                original_data_size=original_size,
                processed_data_size=0,
                fallback_reason="rate_limited"
            )
            self.metrics.log_processing_attempt(result)
            return result
            
        # Route to appropriate processing method
        try:
            if query_type == "logs":
                processed_content = self._process_logs(raw_data, user_query)
            elif query_type == "ships":
                processed_content = self._process_ships(raw_data, user_query)
            else:  # general
                processed_content = self._process_general(raw_data, user_query)
                
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
            result = ProcessingResult(
                content="LLM_PROCESSOR_FALLBACK_ERROR",
                was_processed=False,
                processing_status="error",
                is_fallback_response=True,
                original_data_size=original_size,
                processed_data_size=0,
                fallback_reason=str(e)
            )
            self.metrics.log_processing_attempt(result)
            return result
        
    def _process_logs(self, raw_logs: str, user_query: str) -> str:
        """Process logs with character disambiguation and optional summarization as separate steps"""
        print(f"   📝 LOG PROCESSING: Character processing + optional summarization ({len(raw_logs)} chars)")
        
        # Extract character context for logs only
        character_context = self._extract_character_context(raw_logs, user_query)
        print(f"   🎭 CHARACTER CONTEXT: Processing character disambiguation rules")
        
        # STEP 1: Always do character processing first
        print(f"   📊 STEP 1: Character processing and disambiguation")
        character_prompt = self._create_log_character_processing_prompt(raw_logs, character_context)
        character_processed_logs = self._call_llm_with_prompt(character_prompt, max_output_tokens=100000)
        
        # STEP 2: Check if we need summarization after character processing
        needs_summarization = len(character_processed_logs) >= self.PROCESSING_THRESHOLD
        
        if needs_summarization:
            print(f"   📊 STEP 2: Summarization ({len(character_processed_logs)} chars processed content)")
            summary_prompt = self._create_log_summary_prompt(character_processed_logs, user_query)
            return self._call_llm_with_prompt(summary_prompt, max_output_tokens=12000)
        else:
            print(f"   ✅ CHARACTER PROCESSING COMPLETE: No summarization needed ({len(character_processed_logs)} chars)")
            return character_processed_logs
    
    def _process_ships(self, raw_data: str, user_query: str) -> str:
        """Process ship information with direct summarization"""
        print(f"   🚢 SHIP PROCESSING: Direct summarization ({len(raw_data)} chars)")
        prompt = self._create_ship_summary_prompt(raw_data, user_query)
        return self._call_llm_with_prompt(prompt, max_output_tokens=12000)
    
    def _process_general(self, raw_data: str, user_query: str) -> str:
        """Process general content with direct summarization"""
        print(f"   📋 GENERAL PROCESSING: Direct summarization ({len(raw_data)} chars)")
        prompt = self._create_general_summary_prompt(raw_data, user_query)
        return self._call_llm_with_prompt(prompt, max_output_tokens=12000)
        
    def _extract_character_context(self, raw_data: str, user_query: str) -> CharacterContext:
        """Extract minimal character context - only used for logs processing"""
        # No roleplay state dependencies - always process content the same way
        return CharacterContext()
    
    def _get_character_corrections(self) -> str:
        """Get character corrections from log_patterns.py"""
        try:
            # Import character corrections from log_patterns.py
            from .log_patterns import SHIP_SPECIFIC_CHARACTER_CORRECTIONS, FALLBACK_CHARACTER_CORRECTIONS
            
            corrections = ["CHARACTER CORRECTIONS TO APPLY:"]
            
            # Add ship-specific corrections
            corrections.append("SHIP-SPECIFIC CORRECTIONS:")
            for ship, ship_corrections in SHIP_SPECIFIC_CHARACTER_CORRECTIONS.items():
                correction_list = []
                for incorrect, correct in ship_corrections.items():
                    correction_list.append(f"'{incorrect}' → '{correct}'")
                corrections.append(f"  * {ship.title()}: {', '.join(correction_list)}")
            
            # Add general character corrections
            corrections.append("GENERAL CHARACTER CORRECTIONS:")
            for incorrect, correct in FALLBACK_CHARACTER_CORRECTIONS.items():
                corrections.append(f"  * '{incorrect}' → '{correct}'")
            
            return "\n".join(corrections)
            
        except Exception as e:
            print(f"⚠️  Error loading character corrections: {e}")
            return "CHARACTER CORRECTIONS: Apply basic character name corrections from context"
            
    def _create_log_summary_prompt(self, character_processed_logs: str, query: str) -> str:
        """Create prompt for log summarization only (character processing already done)"""
        
        return f"""You are a mission log summarizer. Summarize the following character-processed mission logs in response to this query: "{query}"

CRITICAL LENGTH REQUIREMENT: Your response should be approximately 35000-40000 characters. Use ALL available space to preserve as much log content as possible.

SUMMARIZATION INSTRUCTIONS:
- The logs have already been character-processed (names corrected, timestamps removed, OOC filtered)
- ORGANIZE BY NARRATIVE FLOW - like acts/scenes/episodes with natural story progression
- IDENTIFY SCENE CHANGES based on:
  * Location changes (bridge to engineering, ship to planet, etc.)
  * Time shifts (different shifts, days, missions)
  * Major plot developments or story beats
  * Character group changes (different characters entering/leaving)
- CREATE NARRATIVE SECTIONS that flow chronologically through the story
- DIALOGUE SUMMARIZATION: Keep important contextual dialogue that reveals character relationships, plot developments, decisions, and mission-critical information
- PRESERVE key character quotes that show personality, important decisions, or mission context
- SUMMARIZE routine conversations but keep dialogue that advances the story or reveals character
- INTEGRATE dialogue, actions, and narrative naturally within each scene/act
- Include ALL character names, locations, and specific details
- Focus on mission context, technical details, and background information
- PRIORITY: Natural narrative flow that tells the story chronologically

NARRATIVE SECTION FORMAT:
=== ACT/SCENE: [Location/Setting] - [Brief Scene Description] ===
[Integrated narrative combining dialogue, actions, and scene description in chronological order]
- Key dialogue and character interactions
- Important actions and decisions  
- Environmental context and scene setting
- Mission developments and plot progression

EXAMPLE SECTIONS:
=== SCENE: Bridge - Morning Shift Briefing ===
=== SCENE: Engineering - Crisis Response ===
=== SCENE: Ten Forward - Off-Duty Character Development ===
=== SCENE: Away Mission - Planet Surface Exploration ===

CHARACTER-PROCESSED MISSION LOGS TO SUMMARIZE:
{character_processed_logs}

Summarize these character-processed logs with narrative flow organization, creating natural story progression through acts/scenes. Integrate dialogue, actions, and narrative within each scene section. Focus on important contextual dialogue and mission-critical conversations while maintaining chronological story flow. ENSURE YOUR RESPONSE IS UNDER 40000 CHARACTERS."""

    def _create_log_character_processing_prompt(self, logs: str, character_context: CharacterContext) -> str:
        """Create prompt for character processing only (no summarization) - NO CHARACTER LIMITS"""
        
        # Get character corrections from log_patterns.py
        character_corrections = self._get_character_corrections()
        
        return f"""You are a mission log character processor. Your ONLY job is to fix character names and remove timestamps/OOC content.

{character_corrections}

PROCESSING RULES:
- DGM Character Control: Process [Character], Character:, (Character) patterns
- DGM Gamemaster Accounts: liorexus, isis, cygnus, illuice, captain_rien, demoncherub
- DOIC Channels: ALL of these contain valid roleplay content - remove ONLY the channel tags, keep ALL content:
  * [DOIC] - Main channel with DGM narration and environmental descriptions
  * [DOIC1] - Character dialogue and actions
  * [DOIC2] - Character dialogue and actions  
  * [DOIC3] - Character dialogue and actions
  * [DOIC4] - Character dialogue and actions
  * [DOIC5] - Character dialogue and actions
- OOC Filtering: Remove ((text)), //text, ooc: patterns - but NOT [text] patterns (character names)

🚨 CRITICAL: THIS IS FORMATTING ONLY - NOT SUMMARIZATION 🚨

TARGET OUTPUT LENGTH: {len(logs) - 5000} to {len(logs)} characters
(Input is {len(logs)} characters - output should be nearly identical length)

FORMATTING TASKS (ONLY THESE 5 MINIMAL CHANGES):
1. Fix character names using the rules above (e.g., "tolena" → "Captain Tolena Blaine")
2. Remove timestamps like [2024-12-28 15:30:45] but keep stardates
3. Remove channel name tags: [DOIC], [DOIC1], [DOIC2], [DOIC3], [DOIC4], [DOIC5] - BUT KEEP ALL CONTENT from these channels
4. Remove OOC content: ((text)), //text, ooc: - BUT NOT [text] patterns (these could be character names)
5. Process DGM patterns: [Character], Character:, (Character)

THIS IS TEXT FORMATTING - NOT CONTENT REDUCTION

WHAT YOU MUST NOT DO:
❌ Do NOT summarize dialogue - keep every word of conversation
❌ Do NOT summarize actions - keep every emote and action description  
❌ Do NOT summarize narrative - keep every scene description
❌ Do NOT remove any character interactions
❌ Do NOT condense multiple paragraphs into fewer paragraphs
❌ Do NOT create section headers or reorganize content
❌ Do NOT shorten descriptions or explanations
❌ Do NOT combine separate events into single descriptions
❌ Do NOT remove repetitive content - keep all repetition
❌ Do NOT paraphrase anything - use original wording
❌ Do NOT filter out content from ANY DOIC channel - process ALL [DOIC], [DOIC1], [DOIC2], [DOIC3], [DOIC4], [DOIC5] content

EXAMPLES OF CORRECT PROCESSING:
INPUT: "[2024-12-28 15:30:45] tolena says 'Hello there, how are you doing today?'"
OUTPUT: "Captain Tolena Blaine says 'Hello there, how are you doing today?'"
(Notice: Only timestamp removed and character name corrected - dialogue preserved exactly)

INPUT: "[DOIC1] tolena@liorexus says 'Welcome to the bridge, everyone.'"
OUTPUT: "Captain Tolena Blaine says 'Welcome to the bridge, everyone.'"
(Notice: Channel tag [DOIC1] removed, character name corrected, dialogue preserved exactly)

INPUT: "[DOIC] The ship's lights dim as evening approaches. [DOIC2] Cadet Tavi enters the gym. [DOIC3] Engineering reports all systems normal."
OUTPUT: "The ship's lights dim as evening approaches. Cadet Tavi enters the gym. Engineering reports all systems normal."
(Notice: ALL channel tags removed, ALL content from ALL channels preserved)

EXAMPLE OF WRONG PROCESSING:
INPUT: Multiple paragraphs of detailed scene description
WRONG OUTPUT: "The scene was busy with various activities"
CORRECT OUTPUT: [Keep all original paragraphs exactly as written]

EXPECTED OUTPUT LENGTH: {len(logs) - 5000} to {len(logs)} characters
(You are processing {len(logs)} characters - return nearly the same amount)

The only content reduction should be from removing timestamps, channel tags, and OOC patterns.
Everything else must be preserved word-for-word.

CONTENT TO PROCESS:
{logs}

Apply ONLY the 5 formatting changes listed above. Return the content with character names corrected and timestamps/OOC removed. Do not change anything else. Your output should be {len(logs) - 5000}+ characters."""

    def _create_ship_summary_prompt(self, data: str, query: str) -> str:
        """Create prompt for ship information processing"""
        return f"""You are a starship database analyst. Process the following ship information in response to this query: "{query}"

CRITICAL LENGTH REQUIREMENT: Your response should be approximately 35000-40000 characters. This is a SUBSTANTIAL response - use most of the available space to provide comprehensive ship information.

INSTRUCTIONS:
- Extract key ship specifications, capabilities, and technical details
- Preserve important ship names, registry numbers, class information, and specifications
- Organize information logically by ship systems, history, and capabilities
- Include comprehensive technical context and operational background
- Maintain accuracy of all factual ship data
- Focus on information that directly answers the user's question about the ship
- TARGET LENGTH: Aim for 35000-40000 characters - this should be a comprehensive, detailed response
- Use the full available space to provide thorough coverage of ship information
- Only summarize if absolutely necessary to fit within the character limit

SHIP DATA TO PROCESS:
{data}

Provide a well-organized response that thoroughly addresses the user's ship query while preserving important technical specifications and operational information. ENSURE YOUR RESPONSE IS UNDER 40000 CHARACTERS."""

    def _create_general_summary_prompt(self, data: str, query: str) -> str:
        """Create prompt for general content processing"""
        return f"""You are a database analyst. Process the following information in response to this query: "{query}"

CRITICAL LENGTH REQUIREMENT: Your response should be approximately 35000-40000 characters. This is a SUBSTANTIAL response - use most of the available space to provide comprehensive information.

INSTRUCTIONS:
- Extract key facts and relationships relevant to the query
- Preserve important names, dates, specifications, and details
- Organize information logically and clearly
- Include comprehensive context and background information
- Maintain accuracy of all factual content
- Focus on information that directly answers the user's question
- TARGET LENGTH: Aim for 35000-40000 characters - this should be a comprehensive, detailed response
- Use the full available space to provide thorough coverage of the content
- Only summarize if absolutely necessary to fit within the character limit

DATA TO PROCESS:
{data}

Provide a well-organized response that thoroughly addresses the user's query while preserving important factual information and context. ENSURE YOUR RESPONSE IS UNDER 40000 CHARACTERS."""

    def _call_llm_with_prompt(self, prompt: str, max_output_tokens: int = 8250) -> str:
        """Call LLM with the given prompt and configurable token limits"""
        if not self.client:
            raise Exception("Gemini client not initialized")
            
        print(f"🔄 LLM CALL: Prompt size = {len(prompt)} chars, max_tokens = {max_output_tokens}")
        
        try:
            # Apply explicit generation limits with configurable token count
            from google.generativeai.types import GenerationConfig

            generation_config = GenerationConfig(
                max_output_tokens=max_output_tokens,
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
                

            
    def get_processing_stats(self) -> Dict[str, int]:
        """Get current processing statistics"""
        return self.metrics.get_daily_stats()


# Global instance for use across the application
_knowledge_engine_instance = None

def get_knowledge_engine() -> KnowledgeEngine:
    """Get the global Knowledge Engine instance"""
    global _knowledge_engine_instance
    if _knowledge_engine_instance is None:
        _knowledge_engine_instance = KnowledgeEngine()
    return _knowledge_engine_instance


def should_process_data(data: str) -> bool:
    """Determine if data should be processed based on size and content"""
    return len(data) > KnowledgeEngine.PROCESSING_THRESHOLD 