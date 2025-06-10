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
MAX_CHARS_CONTEXT = 30000
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
    'game mechanics'
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