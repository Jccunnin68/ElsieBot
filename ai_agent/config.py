"""Configuration module for AI agent"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemma API
GEMMA_API_KEY = os.getenv("GEMMA_API_KEY")
if GEMMA_API_KEY:
    genai.configure(api_key=GEMMA_API_KEY)

# Constants
MAX_CHARS_LOG = 8000
MAX_CHARS_CONTEXT = 3000
MAX_CHARS_TELL_ME_ABOUT = 5000

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
    'what happened', 'events', 'mission report', 'incident report'
]

# Activity keywords for ship activity detection
ACTIVITY_KEYWORDS = ['what happened', 'recent', 'latest', 'activities', 'missions', 'events']

# Port configuration
PORT = int(os.getenv("PORT", 8000)) 