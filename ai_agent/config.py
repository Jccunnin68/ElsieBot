"""Configuration module for AI agent"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
import re

# Load environment variables
load_dotenv()

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

# Character-based limits (conservative estimates)
MAX_CHARS_CONTEXT = 15000    # ~4000 tokens for context
MAX_CHARS_LOG = 6000         # ~1500 tokens for logs
MAX_CHARS_TELL_ME_ABOUT = 3000  # ~750 tokens for tell me about
MAX_CHARS_SHIP_INFO = 4000   # ~1000 tokens for ship info
MAX_CHARS_PROMPT_BASE = 8000 # ~2000 tokens for base prompt/instructions

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

# Legacy constants - use the new token-aware limits above instead
# MAX_CHARS_LOG = 8000
# MAX_CHARS_CONTEXT = 30000  
# MAX_CHARS_TELL_ME_ABOUT = 5000

# Ship names from the fleet
SHIP_NAMES = [
    'stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 
    'caelian', 'enterprise', 'montagnier', 'faraday', 'cook', 'mjolnir',
    'rendino', 'gigantes', 'banshee'
]

# Log indicators for query detection
LOG_INDICATORS = [
    'log', 'logs', 'mission log', 'ship log', 'stardancer log', 
    'captain log', 'personal log', 'stardate', 'entry',
    'what happened', 'events', 'mission report', 'incident report',
    'summarize', 'summary', 'recap', 'tell me what',
    'last mission', 'recent mission', 'latest log',
    'captain\'s log', 'first officer\'s log',
    'expedition', 'away mission', 'away team',
    'event log', 'event logs', 'incident', 'incident log',
    'event report', 'occurrence', 'happening',
    # Ship-specific log patterns
    'adagio log', 'pilgrim', 'stardancer log', 'protector log',
    'manta ', 'sentinel', 'caelian', 'enterprise log',
    'montagnier log', 'faraday log', 'cook log', 'mjolnir log',
    'rendino log', 'gigantes', 'banshee','adagio'
    # Date-based patterns
    'retrieve', 'show me', 'get the log', 'find the log',
    # Named incidents
    'incident log', 'crisis log', 'affair log', 'operation log'
]

# Ship log search patterns
SHIP_LOG_PATTERNS = [
    r"show.*logs? for (?:the )?(USS )?(?P<ship>[A-Za-z]+)",
    r"what.*happened (?:on|aboard) (?:the )?(USS )?(?P<ship>[A-Za-z]+)",
    r"tell.*about.*(?:the )?(USS )?(?P<ship>[A-Za-z]+).*(?:logs?|events|missions?)",
    r"(?:get|fetch|find).*logs? for (?:the )?(USS )?(?P<ship>[A-Za-z]+)",
    r"summarize.*logs? (?:for|from) (?:the )?(USS )?(?P<ship>[A-Za-z]+)"
]

# Log search keywords
LOG_SEARCH_KEYWORDS = [
    'mission', 'event', 'incident', 'encounter', 'expedition',
    'first contact', 'combat', 'diplomatic', 'exploration',
    'scientific', 'medical', 'emergency', 'distress', 'rescue'
]

# Character name patterns and indicators
CHARACTER_PATTERNS = [
    r"tell.*about (?:captain |commander |lieutenant |doctor |dr\. |ensign |chief )?(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)",
    r"who (?:is|was) (?:captain |commander |lieutenant |doctor |dr\. |ensign |chief )?(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)",
    r"(?:captain |commander |lieutenant |doctor |dr\. |ensign |chief )?(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*) (?:biography|background|history|profile)",
    r"(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*) (?:character|person|officer|crew)",
    r"(?:about|info on|information about) (?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)",
    r"(?P<name>[A-Z][a-z]+(?: [A-Z][a-z']*)*)'s (?:background|history|bio)"
]

CHARACTER_KEYWORDS = [
    'captain', 'commander', 'lieutenant', 'doctor', 'dr.', 'ensign', 'chief',
    'officer', 'crew', 'member', 'personnel', 'biography', 'background', 
    'history', 'profile', 'character', 'person'
]

# Common Star Trek character names (for better detection)
COMMON_CHARACTER_NAMES = [
    'kirk', 'spock', 'mccoy', 'scotty', 'uhura', 'sulu', 'chekov',
    'picard', 'riker', 'data', 'worf', 'geordi', 'troi', 'beverly',
    'janeway', 'chakotay', 'tuvok', 'paris', 'torres', 'kim', 'neelix',
    'sisko', 'kira', 'odo', 'dax', 'bashir', 'obrien', 'nog',
    'archer', 'trip', 'reed', 'hoshi', 'travis', 'phlox'
]

# Activity keywords for ship activity detection
ACTIVITY_KEYWORDS = ['what happened', 'recent', 'latest', 'activities', 'missions', 'events']

# OOC query detection
OOC_PREFIX = "OOC"
OOC_KEYWORDS = [
    'players handbook',
    'phb',
    'rules',
    'species traits',
    'character creation',
    'mechanics',
    'game mechanics',
    'link',
    'url',
    'page',
    'get me',
    'show me',
    'find'
]

# Meeting information to filter out
MEETING_INFO_PATTERNS = [
    r"meets.*[0-9].*[AP]M.*[A-Z]ST",
    r"GMed by.*",
    r"DGM.*and DGM.*",
    r"Game Master.*schedule",
    r"session.*schedule"
]

# Port configuration
PORT = int(os.getenv("PORT", 8000)) 