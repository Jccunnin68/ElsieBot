"""
OOC Handlers - Out-of-Character Query Processing
================================================

This module handles all out-of-character (OOC) queries including
URL requests and general OOC information retrieval.
"""

from content_retrieval_db import get_relevant_wiki_context, get_log_url
from ai_logic import extract_ooc_log_url_request, is_ooc_query


def handle_ooc_url_request(user_message: str) -> str:
    """Handle OOC URL requests directly."""
    is_url_request, search_query = extract_ooc_log_url_request(user_message)
    if not is_url_request:
        return "I can't seem to figure out which URL you need. Could you be more specific?"
        
    print(f"🔗 EXECUTING OOC URL STRATEGY: '{search_query}'")
    print(f"   ⚠️  OOC URL Request: Will preserve real Earth dates in response")
    url_response = get_log_url(search_query)
    print(f"   - URL response: {url_response}")
    return url_response


def get_ooc_context(user_message: str) -> str:
    """Generate context for OOC queries."""
    print(f"📋 SEARCHING OOC DATA")
    wiki_info = get_relevant_wiki_context(user_message)
    print(f"   - Retrieved OOC context length: {len(wiki_info)} chars")
    
    print(f"   ⚠️  OOC Query: Skipping date conversion to preserve real Earth dates")
    
    ooc_query = is_ooc_query(user_message)[1]
    if any(word in ooc_query.lower() for word in ['schedule', 'meeting', 'time', 'when', 'gm', 'game master']):
        return f"""You are Elsie, providing Out-Of-Character (OOC) information about game schedules and meetings.

CRITICAL INSTRUCTIONS FOR OOC SCHEDULE QUERIES:
- Provide complete information about meeting times, schedules, and Game Masters
- Include all relevant scheduling details
- Be direct and clear about times, dates, and frequencies
- Specify time zones when mentioned
- List all relevant GMs and their roles
- Use REAL EARTH DATES - do not convert to Star Trek era dates
- Keep all scheduling information in actual Earth calendar format

{f"SCHEDULE INFORMATION: {wiki_info}" if wiki_info else ""}

Respond with the complete scheduling information requested using real Earth dates and times."""
    else:
        return f"""You are Elsie, providing Out-Of-Character (OOC) information from the Players Handbook.

CRITICAL INSTRUCTIONS FOR OOC QUERIES:
- Focus on rules, mechanics, species traits, and character creation details
- Be direct and factual in your responses
- Keep responses clear and concise
- Use REAL EARTH DATES where applicable - do not convert to Star Trek era dates

{f"PLAYERS HANDBOOK QUERY: {ooc_query}" if ooc_query else ""}

{f"HANDBOOK INFORMATION: {wiki_info}" if wiki_info else ""}

Respond with ONLY the relevant Players Handbook information using real Earth dates.""" 