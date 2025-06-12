"""Configuration module for AI agent"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load environment variables
load_dotenv()

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
# Wiki endpoints for search_memory_alpha
WIKI_ENDPOINTS = [
    "https://memory-alpha.fandom.com/api.php",
    "https://22ndmobile.fandom.com/api.php"]



# Character-based limits REMOVED - Elsie now gets full context
# These were previously used for truncation but are now disabled
# MAX_CHARS_CONTEXT = 15000    # ~4000 tokens for context
# MAX_CHARS_LOG = 6000         # ~1500 tokens for logs
# MAX_CHARS_TELL_ME_ABOUT = 3000  # ~750 tokens for tell me about
# MAX_CHARS_SHIP_INFO = 4000   # ~1000 tokens for ship info
MAX_CHARS_PROMPT_BASE = 8000 # ~2000 tokens for base prompt/instructions (kept for prompt validation)








