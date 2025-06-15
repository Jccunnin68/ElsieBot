"""
LLM Query Post Processor
========================

Post-processes large query results using gemini-2.0-flash-lite to create concise,
relevant summaries for the main AI engine. Includes context-aware fallback handling
for roleplay vs non-roleplay scenarios.
"""

import time
import random
import re
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
    """
    
    PROCESSING_THRESHOLD = 14000  # Characters
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
            
    def process_query_results(self, query_type: str, raw_data: str, user_query: str, 
                            is_roleplay: bool = False) -> ProcessingResult:
        """Main processing entry point"""
        print(f"🔄 LLM PROCESSING: type='{query_type}', size={len(raw_data)} chars, roleplay={is_roleplay}")
        
        original_size = len(raw_data)
        
        # Check if processing is needed
        if len(raw_data) < self.PROCESSING_THRESHOLD:
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
            
        # Attempt processing
        try:
            if query_type == "logs":
                processed_content = self._process_log_data(raw_data, user_query)
            else:
                processed_content = self._process_general_data(raw_data, user_query)
                
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
        
    def _process_general_data(self, raw_data: str, user_query: str) -> str:
        """General data summarization"""
        prompt = self._create_general_summary_prompt(raw_data, user_query)
        return self._call_llm_with_prompt(prompt)
        
    def _create_log_summary_prompt(self, logs: str, query: str) -> str:
        """Create optimized prompt for log summarization"""
        return f"""You are a mission log analyst. Process the following mission logs in response to this query: "{query}"

INSTRUCTIONS:
- Focus on key events, character actions, and dialogue relevant to the query
- Preserve important character names, dates, and locations
- Maintain chronological order when possible
- Include significant decisions and outcomes
- Keep character personalities and relationships clear
- Include detailed dialogue and character interactions when relevant
- Preserve mission context and background information
- Be comprehensive and detailed - aim to retain 70-90% of essential content
- Maximum output: 14000 characters - use this space generously for thorough coverage

MISSION LOGS TO PROCESS:
{logs}

Provide a comprehensive and detailed summary that thoroughly addresses the user's query while preserving all essential mission details, character interactions, and context."""

    def _create_general_summary_prompt(self, data: str, query: str) -> str:
        """Create optimized prompt for general data"""
        return f"""You are a database analyst. Process the following information in response to this query: "{query}"

INSTRUCTIONS:
- Extract key facts and relationships relevant to the query
- Preserve important names, dates, specifications, and details
- Organize information logically and clearly
- Include comprehensive context and background information
- Maintain accuracy of all factual content
- Focus on information that directly answers the user's question
- Be thorough and detailed - aim to retain 70-90% of essential content
- Maximum output: 14000 characters - use this space generously for comprehensive coverage

DATA TO PROCESS:
{data}

Provide a well-organized and comprehensive response that thoroughly addresses the user's query while preserving all important factual information and context."""

    def _call_llm_with_prompt(self, prompt: str) -> str:
        """Call LLM with the given prompt"""
        if not self.client:
            raise Exception("Gemini client not initialized")
            
        try:
            response = self.client.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            else:
                raise Exception("Empty response from Gemini")
        except Exception as e:
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