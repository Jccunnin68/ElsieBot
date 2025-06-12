"""Configuration module for AI agent"""

import os
from dotenv import load_dotenv
import google.generativeai as genai


# Load environment variables
load_dotenv()

# Port configuration
PORT = int(os.getenv("PORT", 8000))
# Configure Gemma API
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
if GEMMA_API_KEY:
    genai.configure(api_key=GEMMA_API_KEY)

# Token and content limits for Gemma API (max 8192 tokens)
# Rough conversion: 1 token ≈ 3-4 characters for English text
# We use conservative estimates to stay well under the limit
GEMMA_MAX_TOKENS = 8192
GEMMA_SAFETY_MARGIN = 1000  # Reserve tokens for response generation
MAX_INPUT_TOKENS = GEMMA_MAX_TOKENS - GEMMA_SAFETY_MARGIN  # 7192 tokens

# Character-based limits REMOVED - Elsie now gets full context
# These were previously used for truncation but are now disabled
# MAX_CHARS_CONTEXT = 15000    # ~4000 tokens for context
# MAX_CHARS_LOG = 6000         # ~1500 tokens for logs
# MAX_CHARS_TELL_ME_ABOUT = 3000  # ~750 tokens for tell me about
# MAX_CHARS_SHIP_INFO = 4000   # ~1000 tokens for ship info
MAX_CHARS_PROMPT_BASE = 5000 # ~2000 tokens for base prompt/instructions (kept for prompt validation)





def estimate_token_count(text: str) -> int:
    """
    Estimate token count for text input to Gemma API
    Uses conservative estimate: 1 token ≈ 4 characters (more conservative)
    """
    if not text:
        return 0
    return int(len(text) / 4)

def truncate_to_token_limit(text: str, max_tokens: int) -> str:
    """
    Truncate text to fit within token limit
    Preserves word boundaries when possible
    """
    if not text:
        return text
    
    estimated_tokens = estimate_token_count(text)
    if estimated_tokens <= max_tokens:
        return text
    
    # Calculate target character count (more conservative)
    target_chars = int(max_tokens * 4)
    
    if len(text) <= target_chars:
        return text
    
    # Truncate at word boundary
    truncated = text[:target_chars]
    last_space = truncated.rfind(' ')
    
    if last_space > target_chars * 0.8:  # If we can find a space in the last 20%
        truncated = truncated[:last_space]
    
    return truncated + "...[CONTENT TRUNCATED DUE TO LENGTH]"

def validate_total_prompt_size(prompt: str) -> str:
    """
    Validate and truncate entire prompt to fit within Gemma token limits
    """
    estimated_tokens = estimate_token_count(prompt)
    
    if estimated_tokens <= MAX_INPUT_TOKENS:
        return prompt
    
    print(f"⚠️  WARNING: Prompt too long ({estimated_tokens} tokens > {MAX_INPUT_TOKENS} limit)")
    
    # Truncate the prompt to fit, being more aggressive
    target_tokens = MAX_INPUT_TOKENS - 50  # Extra safety margin
    truncated_prompt = truncate_to_token_limit(prompt, target_tokens)
    
    final_tokens = estimate_token_count(truncated_prompt)
    print(f"   ✂️  Truncated prompt to {final_tokens} tokens")
    
    return truncated_prompt










