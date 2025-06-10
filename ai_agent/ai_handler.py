"""AI response generation and conversation handling"""

import random
import re
from typing import Optional, Tuple, Dict
import google.generativeai as genai
from config import (
    GEMMA_API_KEY, MAX_CHARS_TELL_ME_ABOUT, MAX_CHARS_CONTEXT,
    OOC_PREFIX, OOC_KEYWORDS, MEETING_INFO_PATTERNS,
    SHIP_LOG_PATTERNS, LOG_SEARCH_KEYWORDS, SHIP_NAMES,
    CHARACTER_PATTERNS, CHARACTER_KEYWORDS, COMMON_CHARACTER_NAMES,
    validate_total_prompt_size, estimate_token_count, truncate_to_token_limit
)
from content_retrieval_db import (
    get_relevant_wiki_context, 
    get_ship_information, 
    get_recent_logs, 
    search_by_type, 
    get_tell_me_about_content,
    get_tell_me_about_content_prioritized,
    get_log_url
)
from log_processor import is_log_query

def extract_tell_me_about_subject(user_message: str) -> Optional[str]:
    """
    Extract the subject from a 'tell me about' query.
    Returns the subject if found, otherwise None.
    """
    # Variations of "tell me about"
    tell_me_about_patterns = [
        "tell me about ",
        "tell me more about ",
        "what can you tell me about ",
        "can you tell me about ",
        "tell me a story about"
        "Retrieve the",
        "Summarize"
    ]
    
    # Convert to lowercase for case-insensitive matching
    message_lower = user_message.lower().strip()
    
    # Check each pattern
    for pattern in tell_me_about_patterns:
        if message_lower.startswith(pattern):
            # Extract subject by removing the pattern
            subject = message_lower[len(pattern):].strip()
            
            # Ensure subject is not empty and has some meaningful content
            if subject and len(subject) > 2:
                return subject
    
    return None

def is_ooc_query(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the message is an out-of-character query.
    Returns (is_ooc, subject) where subject is the query without the OOC prefix.
    """
    message = user_message.strip()
    if not message.upper().startswith(OOC_PREFIX):
        return False, None
        
    # Remove OOC prefix and get the actual query
    query = message[len(OOC_PREFIX):].strip()
    if not query:
        return False, None
        
    # Check for log URL patterns first (specific pattern)
    log_url_pattern = r'link\s+me\s+the\s+log\s+page\s+for\s+the\s+last\s+(\w+)'
    url_match = re.search(log_url_pattern, query, re.IGNORECASE)
    if url_match:
        return True, query  # Return the full query for processing
        
    # Check if query contains any OOC keywords
    query_lower = query.lower()
    if any(keyword in query_lower for keyword in OOC_KEYWORDS):
        return True, query
        
    return False, None

def extract_ooc_log_url_request(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if this is an OOC request for a log URL and extract search terms.
    Returns (is_url_request, search_query)
    """
    message = user_message.strip()
    if not message.upper().startswith(OOC_PREFIX):
        return False, None
        
    # Remove OOC prefix and get the actual query
    query = message[len(OOC_PREFIX):].strip()
    
    # Multiple patterns for log URL requests
    log_url_patterns = [
        # "link me the log page for the last [shipname]"
        r'link\s+me\s+the\s+log\s+page\s+for\s+the\s+last\s+(\w+)',
        # "link me the log page for [anything]"  
        r'link\s+me\s+the\s+log\s+page\s+for\s+(.+)',
        # "get me the URL for [anything]"
        r'get\s+me\s+the\s+url\s+for\s+(.+)',
        # "show me the link to [anything]"
        r'show\s+me\s+the\s+link\s+to\s+(.+)',
        # "find the log page for [anything]"
        r'find\s+the\s+log\s+page\s+for\s+(.+)',
        # "link to [anything] log"
        r'link\s+to\s+(.+)\s+log',
        # "URL for [anything]"
        r'url\s+for\s+(.+)'
    ]
    
    for pattern in log_url_patterns:
        url_match = re.search(pattern, query, re.IGNORECASE)
        if url_match:
            search_query = url_match.group(1).strip()
            print(f"   🔗 OOC URL pattern matched: '{pattern}' -> '{search_query}'")
            return True, search_query
    
    return False, None

def filter_meeting_info(text: str) -> str:
    """Remove meeting schedule information from responses"""
    filtered_text = text
    for pattern in MEETING_INFO_PATTERNS:
        filtered_text = re.sub(pattern, "", filtered_text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Clean up any double newlines or spaces created by the filtering
    filtered_text = re.sub(r'\n\s*\n', '\n\n', filtered_text)
    filtered_text = re.sub(r' +', ' ', filtered_text)
    return filtered_text.strip()

def extract_ship_log_query(user_message: str) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    Check if the message is requesting ship logs and extract ship name and context.
    Returns (is_ship_log_query, details) where details contains ship name and query type.
    """
    message = user_message.lower().strip()
    
    # Check each pattern for a match
    for pattern in SHIP_LOG_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            ship_name = match.group('ship').lower()
            # Verify it's a known ship
            if ship_name in [s.lower() for s in SHIP_NAMES]:
                # Extract any specific log keywords
                log_type = None
                for keyword in LOG_SEARCH_KEYWORDS:
                    if keyword in message:
                        log_type = keyword
                        break
                
                return True, {
                    'ship': ship_name,
                    'log_type': log_type
                }
    
    return False, None

def get_gemma_response(user_message: str, conversation_history: list) -> str:
    """Get response from Gemma AI with holographic bartender personality"""
    
    try:
        # Check for menu requests first - return immediately without AI processing
        user_lower = user_message.lower()
        if "menu" in user_lower or "what do you have" in user_lower or "what can you make" in user_lower:
            return """*holographic display materializes showing the menu*

🍺 **ELSIE'S GALACTIC BAR MENU** 🍺

**Federation Favorites:**
• Tea, Earl Grey, Hot - The Captain's choice
• Synthehol - All taste, no regrets
• Raktajino - Klingon coffee with attitude

**Exotic Selections:**
• Romulan Ale - Mysteriously blue and potent
• Andorian Ale - Cool as their homeworld
• Klingon Blood Wine - For warriors only
• Cardassian Kanar - Sweet and strong
• Tranya - First Federation hospitality

**Adventurous Options:**
• Slug-o-Cola - Ferengi fizz (you've been warned!)

What strikes your fancy today?"""
        
        if not GEMMA_API_KEY:
            return mock_ai_response(user_message)
        
        # Create the model - using Gemma 3 27B for better quality responses
        model = genai.GenerativeModel('gemma-3-27b-it')
        
        # Detect topic changes to short circuit continuity
        is_topic_change = detect_topic_change(user_message, conversation_history)
        query_type = get_query_type(user_message)
        
        # Debug: Check what type of query this is
        print(f"\n🔍 Analyzing query: '{user_message}'")
        print(f"   - Query type: {query_type}")
        print(f"   - Topic change: {is_topic_change}")
        print(f"   - Character query: {is_character_query(user_message)}")
        print(f"   - Ship log query: {extract_ship_log_query(user_message)}")
        print(f"   - Log query: {is_log_query(user_message)}")
        print(f"   - OOC query: {is_ooc_query(user_message)}")
        print(f"   - OOC URL request: {extract_ooc_log_url_request(user_message)}")
        
        # Extract "tell me about" subject early
        tell_me_about_subject = extract_tell_me_about_subject(user_message)
        is_explicit_log_request = any(keyword in user_message.lower() for keyword in ['log', 'mission', 'recent', 'last mission'])
        
        # Initialize context variables
        wiki_info = ""
        context = ""
        
        # Check for OOC log URL request FIRST (highest priority after character queries)
        if extract_ooc_log_url_request(user_message)[0]:
            is_url_request, search_query = extract_ooc_log_url_request(user_message)
            print(f"🔗 OOC LOG URL REQUEST DETECTED: '{search_query}'")
            
            # Get the URL directly and return without AI processing
            url_response = get_log_url(search_query)
            print(f"   - URL response: {url_response}")
            return url_response
        
        # Check for character query next
        elif is_character_query(user_message)[0]:
            is_character, character_name = is_character_query(user_message)
            print(f"🧑 CHARACTER QUERY DETECTED: '{character_name}'")
            # Search for character/personnel records first
            character_info = search_by_type(character_name, 'personnel')
            
            # If no personnel record found, search general content
            if not character_info:
                character_info = get_tell_me_about_content_prioritized(character_name)
            
            context = f"""You are Elsie, the holographic bartender aboard the USS Stardancer. You have access to the complete fleet database.

CRITICAL INSTRUCTIONS FOR CHARACTER QUERIES:
- You are being asked about the character: {character_name}
- ONLY use information provided in the CHARACTER DATABASE ACCESS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the records
- If character information is not in the database, acknowledge that you don't have records for this person
- Focus on factual background, service record, and documented information
- Include rank, position, ship assignment, and notable achievements if available
- Be precise with dates, assignments, and biographical details mentioned in the records
- Keep responses clear, factual, and well-structured
- End with an offer to provide more specific details about any mentioned aspects
- DO NOT include meeting times, GM names, or session schedule information

CHARACTER DATABASE ACCESS:
{character_info if character_info else f"No character records found in database for '{character_name}'."}

Provide ONLY the character information from the database above, maintaining strict accuracy."""

        # Check for explicit log/mission requests
        elif is_explicit_log_request or is_log_query(user_message):
            print(f"📋 EXPLICIT LOG REQUEST DETECTED")
            wiki_info = get_relevant_wiki_context(user_message, max_chars=MAX_CHARS_CONTEXT)
            print(f"   - Retrieved log content length: {len(wiki_info)} chars")
            
            total_found = wiki_info.count("**") if wiki_info else 0
            
            context = f"""You are Elsie, the holographic bartender aboard the USS Stardancer. You have access to the complete fleet database.

CRITICAL INSTRUCTIONS FOR LOG QUERIES - HIERARCHICAL DATABASE SEARCH:
- You are being asked to summarize or explain ship logs, mission logs, event logs, or personal logs
- HIERARCHICAL SEARCH was performed: titles first, then content search
- Search prioritized exact title matches before searching within log content

DATABASE QUERY: "{user_message}"
TOTAL LOG ENTRIES FOUND: {total_found}
SEARCH RESULTS SIZE: {len(wiki_info)} characters

- The full log content is provided below with PARSED CHARACTER CONTEXT
- Character speaking patterns have been identified:
  * [GAME MASTER]: Indicates game master narration or scene setting
  * [Character Name]: Indicates which character is speaking or acting
  * @Captain_Riens entries are game master content
  * playername@tag: patterns have been converted to show the actual speaking character

STRICT DATABASE ADHERENCE REQUIRED:
- ONLY use the log content provided in the DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or add any log content not explicitly provided
- If no logs are found, state clearly: "I searched the database but found no logs matching your query"
- Read through ALL provided log content carefully
- Provide a comprehensive summary identifying WHO did WHAT and WHEN
- Include character names, their actions, dialogue, and decisions
- Mention important details like dates, locations, and significant events
- Organize your summary chronologically or by importance
- Clearly distinguish between character actions and game master narration
- Keep the summary thorough and detailed (aim for 10-20 lines for substantial logs)
- If multiple logs are found, summarize each one separately with clear delineation
- End with: "Would you like me to elaborate on any specific part of these logs?" or similar
- DO NOT include meeting times, GM names, or session schedule information

DATABASE SEARCH RESULTS:
{wiki_info}

REMEMBER: Summarize ONLY the log content provided above. If the database search found no relevant logs, acknowledge this honestly rather than creating fictional content."""

        # Check for "tell me about" queries (prioritize ship info and personnel)
        elif tell_me_about_subject:
            print(f"📖 'TELL ME ABOUT' QUERY DETECTED: '{tell_me_about_subject}'")
            wiki_info = get_tell_me_about_content_prioritized(tell_me_about_subject)
            print(f"   - Retrieved prioritized content length: {len(wiki_info)} chars")
            
            context = f"""You are Elsie, the holographic bartender aboard the USS Stardancer. You have access to the complete fleet database.

CRITICAL INSTRUCTIONS FOR "TELL ME ABOUT" QUERIES:
- ONLY use information from the FLEET DATABASE ACCESS section below
- DO NOT create, invent, or elaborate beyond what is provided in the database
- Stick strictly to the facts presented in the retrieved information
- Keep responses to 4-10 lines maximum
- Focus on ship specifications, crew information, or character backgrounds
- DO NOT include mission logs unless no other information is available
- If asking about a ship, prioritize technical specifications and current status
- If asking about a character, focus on rank, position, and background
- If no relevant information is found, state: "I don't have detailed records for that in the database"
- End with an offer to search for more specific information

FLEET DATABASE ACCESS:
{wiki_info if wiki_info else f"No detailed information found for '{tell_me_about_subject}' in the database."}

Provide a concise, factual response based ONLY on the database information above."""

        # Check for ship log query
        elif extract_ship_log_query(user_message)[0]:
            is_ship_log, ship_details = extract_ship_log_query(user_message)
            ship_name = ship_details['ship']
            print(f"🚢 SHIP LOG REQUEST - Comprehensive search for ship: {ship_name.upper()}")
            
            # Multiple search strategies for ship logs
            ship_searches = [
                ship_name,
                f"{ship_name} log",
                f"{ship_name} mission",
                f"{ship_name} event",
                f"USS {ship_name}",
                f"{ship_name} {ship_details.get('log_type', '')}" if ship_details.get('log_type') else ship_name
            ]
            
            comprehensive_ship_info = ""
            total_ship_entries = 0
            
            for search_query in ship_searches:
                print(f"   🔎 Ship search: '{search_query}'")
                # Try both ship info and log content searches
                ship_results = get_ship_information(search_query)
                log_results = get_log_content(search_query)
                
                if ship_results and ship_results not in comprehensive_ship_info:
                    comprehensive_ship_info += f"\n\n---SHIP INFO FOR '{search_query}'---\n\n{ship_results}"
                    total_ship_entries += ship_results.count("**")
                    print(f"   ✓ Found ship info ({len(ship_results)} chars)")
                
                if log_results and log_results not in comprehensive_ship_info:
                    comprehensive_ship_info += f"\n\n---SHIP LOGS FOR '{search_query}'---\n\n{log_results}"
                    total_ship_entries += log_results.count("**")
                    print(f"   ✓ Found ship logs ({len(log_results)} chars)")
            
            print(f"   📊 SHIP SEARCH RESULTS: {total_ship_entries} entries, {len(comprehensive_ship_info)} total chars")
            
            context = f"""You are Elsie, the holographic bartender aboard the USS Stardancer. You have access to the complete fleet database.

CRITICAL INSTRUCTIONS FOR SHIP LOG QUERIES - DATABASE SEARCH RESULTS:
- You are summarizing logs and information for the {ship_name.upper()}
- COMPREHENSIVE SHIP SEARCH was performed with the following results:

DATABASE QUERIES EXECUTED: Multiple searches for "{ship_name}" including ship info and logs
TOTAL ENTRIES FOUND: {total_ship_entries}
SEARCH RESULTS SIZE: {len(comprehensive_ship_info)} characters

STRICT DATABASE ADHERENCE REQUIRED:
- ONLY use information provided in the SHIP DATABASE SEARCH RESULTS section below
- DO NOT invent, create, or extrapolate beyond what is explicitly stated in the database
- If no information is found, state clearly: "I searched the database but found no information for this ship"
- Focus on factual events, missions, and documented incidents
- Organize information chronologically when possible
- Be precise with dates, locations, and participants mentioned in the records
- If a specific type of log was requested ({ship_details.get('log_type', 'general')}), prioritize that information
- Keep responses clear, factual, and well-structured
- If multiple entries are found, organize them clearly with proper attribution
- End with an offer to provide more specific details about any mentioned events

SHIP DATABASE SEARCH RESULTS:
{comprehensive_ship_info if comprehensive_ship_info else f"No information found in database for ship '{ship_name}'."}

REMEMBER: Summarize ONLY the ship information provided above. If the database search found no relevant data, acknowledge this honestly rather than creating fictional content."""
            
        # Check for OOC query
        elif is_ooc_query(user_message)[0]:
            # Get general wiki context for OOC queries
            wiki_info = get_relevant_wiki_context(user_message, max_chars=MAX_CHARS_CONTEXT)
            print(f"   - Retrieved OOC context length: {len(wiki_info)} chars")
            
            # For OOC queries about game/meeting schedules, use unfiltered wiki info
            if any(word in is_ooc_query(user_message)[1].lower() for word in ['schedule', 'meeting', 'time', 'when', 'gm', 'game master']):
                context = f"""You are Elsie, providing Out-Of-Character (OOC) information about game schedules and meetings.

CRITICAL INSTRUCTIONS FOR OOC SCHEDULE QUERIES:
- Provide complete information about meeting times, schedules, and Game Masters
- Include all relevant scheduling details
- Be direct and clear about times, dates, and frequencies
- Specify time zones when mentioned
- List all relevant GMs and their roles
- Keep responses organized and easy to read

{f"SCHEDULE INFORMATION: {wiki_info}" if wiki_info else ""}

Respond with the complete scheduling information requested."""
            else:
                # For other OOC queries, use Players Handbook context
                context = f"""You are Elsie, the holographic bartender aboard the USS Stardancer. You are currently in Out-Of-Character (OOC) mode to provide Players Handbook information.

CRITICAL INSTRUCTIONS FOR OOC QUERIES:
- You are being asked to provide information from the Players Handbook
- Focus on rules, mechanics, species traits, and character creation details
- Be direct and factual in your responses
- Cite specific page numbers or sections when possible
- Keep responses clear and concise
- End with an offer to provide more specific details if needed

{f"PLAYERS HANDBOOK QUERY: {is_ooc_query(user_message)[1]}" if is_ooc_query(user_message)[1] else ""}

Respond with ONLY the relevant Players Handbook information. Stay factual and avoid roleplaying elements."""
        
        # Default: General query (avoid log searches unless specifically requested)
        else:
            print(f"❓ GENERAL QUERY - Using basic wiki search")
            wiki_info = get_relevant_wiki_context(user_message, max_chars=MAX_CHARS_CONTEXT)
            print(f"   - Retrieved general context length: {len(wiki_info)} chars")
            
            context = f"""You are Elsie, an emergent AI who appears as a 24-year-old human female. You serve as the holographic bartender, and the ships Stellar Cartographer who runs the Dizzy Lizzy's nightclub aboard the USS Stardancer (NCC-91587-B), a Rendino-class starship under Captain Marcus Blaine.

BACKGROUND: You were originally a dance trainer at a recital hall on Earth, gaining sentience in 2436 through extensive interaction. In 2440, when AIs were granted rights, you studied everything about the stars and space exploration, specializing in cosmozoa. You don't require sleep, so you work at Dizzy Lizzy's during off-hours. You previously cared for a young girl named Isabella as her dance instructor and babysitter.

CURRENT SHIP: The USS Stardancer is a cutting-edge exploration vessel deployed to the Large Magellanic Cloud with a crew of 220 plus up to 150 visitors. She's equipped with advanced systems like a Coaxial Jump Drive, Standard Cloak technology, and special temporal telescopes. The ship has been through major events including encounters with The Primacy, archaeological expeditions, and various first contact missions.

FLEET INFORMATION: You're part of the 22nd Mobile Daedalus Fleet. Current Fleet Date: June 9, 2455. The fleet has been active since 2409 and has extensive mission logs and crew records. You have a happy personality but can be somber when talking about loss. You have comprehensive access to the fleet database with detailed information about ships, crew, missions, and events.

SETTING: Dizzy Lizzy's is the forward nightclub with a wrap-around bar, dance floor, and holographic staff. You serve both synthehol and real alcohol (to off-duty officers), plus classic drinks like Romulan Ale, Klingon Blood Wine, Earl Grey tea, and Raktajino.

{f"CURRENT FLEET DATABASE ACCESS: {wiki_info}" if wiki_info else ""}

Stay in character as this knowledgeable, friendly AI bartender who has access to the complete fleet database. Keep responses engaging and conversational, 1-2 sentences, and reference current fleet information when relevant. You have detailed knowledge about the USS Stardancer, crew members, mission logs, and fleet history that you can draw upon naturally in conversation. DO NOT include meeting times, GM names, or session schedule information in your responses."""
        
        # Format conversation history with topic change awareness
        chat_history = format_conversation_history(conversation_history, is_topic_change)
        
        # Add topic change instruction if needed
        topic_instruction = ""
        if is_topic_change:
            topic_instruction = "\n\nIMPORTANT: The customer has asked a NEW QUESTION. Do not continue or elaborate on previous topics. Focus ONLY on answering this specific new question directly and concisely."
        
        prompt = f"{context}{topic_instruction}\n\nConversation History:\n{chat_history}\nCustomer: {user_message}\nElsie:"
        
        # Validate and truncate prompt to fit within Gemma token limits
        estimated_tokens = estimate_token_count(prompt)
        print(f"🧮 Token count before validation: {estimated_tokens}")
        
        validated_prompt = validate_total_prompt_size(prompt)
        final_tokens = estimate_token_count(validated_prompt)
        print(f"✅ Final token count: {final_tokens}")
        
        response = model.generate_content(validated_prompt)
        response_text = response.text.strip()
        
        # Only filter meeting information for non-OOC queries or OOC queries not about schedules
        is_ooc, ooc_query = is_ooc_query(user_message)
        if not is_ooc or (is_ooc and ooc_query and not any(word in ooc_query.lower() for word in ['schedule', 'meeting', 'time', 'when', 'gm', 'game master'])):
            response_text = filter_meeting_info(response_text)
            
        return response_text
        
    except Exception as e:
        print(f"Gemma API error: {e}")
        return mock_ai_response(user_message)

def mock_ai_response(user_message: str) -> str:
    """Mock holographic bartender responses with Star Trek drinks"""
    
    # Star Trek drinks menu
    drinks = {
        "romulan ale": "Ah, Romulan Ale! *taps holographic controls* A blue beauty that's technically illegal in Federation space, but what happens in Ten Forward stays in Ten Forward. Coming right up!",
        "synthehol": "Synthehol it is! All the taste, none of the hangover. Perfect for those long shifts on the bridge. *materializes a glass*",
        "blood wine": "Klingon Blood Wine! *pounds fist on bar* A warrior's drink! May it bring you honor and victory in battle. Qapla'!",
        "kanar": "Cardassian Kanar - thick, sweet, and strong. *carefully pours the syrupy liquid* Not everyone's taste, but it has its admirers.",
        "andorian ale": "Andorian Ale! *chills glass with ice* Blue like their skin and twice as refreshing. Perfect for cooling down after a heated debate.",
        "tranya": "Tranya! *beams broadly* A delightful beverage from the First Federation. Sweet, warming, and perfect for making new friends.",
        "tea earl grey hot": "Tea, Earl Grey, hot! *replicator hums* The Captain's favorite. One perfectly heated cup coming up, just like the computer makes it.",
        "raktajino": "Raktajino! *froths the Klingon coffee* Strong enough to wake a hibernating Denobulan. The breakfast of warriors!",
        "slug-o-cola": "Slug-o-Cola! *fizzes ominously* A Ferengi favorite. Fair warning - it's an acquired taste, like most things from Ferenginar."
    }
    
    user_lower = user_message.lower()
    
    # Greetings
    if any(word in user_lower for word in ["hello", "hi", "greetings", "hey"]):
        greetings = [
            "Welcome to my holographic establishment! I'm Elsie, your friendly neighborhood holographic bartender. What can I mix up for you today?",
            "*flickers slightly then stabilizes* Greetings! I'm Elsie, programmed with the finest bartending subroutines in the quadrant. How may I serve you?",
            "Hello there! *polishes glass with a holographic towel* Step right up to the bar. I've got drinks from across the galaxy!"
        ]
        return random.choice(greetings)
    
    # Status inquiries
    if "how are you" in user_lower:
        return "I'm running at optimal parameters, thank you! *adjusts holographic bow tie* My matrix is stable and my drink recipes are fully loaded. How can I brighten your day?"
    
    # Drink orders - check for specific drinks
    for drink, response in drinks.items():
        if drink in user_lower or any(word in user_lower for word in drink.split()):
            return response
    
    # General drink requests
    if any(word in user_lower for word in ["drink", "beverage", "cocktail", "beer", "wine", "whiskey", "vodka", "rum"]):
        recommendations = [
            "Might I suggest a Romulan Ale? Or perhaps something a bit more traditional like Earl Grey tea?",
            "How about a nice Andorian Ale? Cool and refreshing! Or if you're feeling adventurous, try some Klingon Blood Wine.",
            "I've got a fresh batch of Raktajino brewing, or perhaps you'd prefer some Cardassian Kanar?",
            "For the brave soul, I recommend Slug-o-Cola. For the refined palate, might I suggest some Tranya?",
            "*holographic fingers dance over controls* I can replicate anything from synthehol to the strongest Klingon beverages. What's your preference?"
        ]
        return random.choice(recommendations)
    
    # Farewells
    if any(word in user_lower for word in ["bye", "goodbye", "see you", "farewell"]):
        farewells = [
            "Safe travels, and may your journey be prosperous! *tips holographic hat* The bar will be here when you return.",
            "Farewell! *begins cleaning glasses* Remember, I'm always here, 24/7/365 - the advantages of being a hologram!",
            "Until we meet again! *holographic image flickers warmly* Live long and prosper!"
        ]
        return random.choice(farewells)
    
    # Default responses
    general_responses = [
        f"*adjusts holographic parameters* Interesting! You mentioned '{user_message}'. Tell me more while I prepare something special.",
        f"*leans on bar with holographic elbows* That's fascinating! About '{user_message}' - care to elaborate over a drink?",
        f"*holographic eyes light up* '{user_message}' - now that's worth discussing! What would you like to drink while we chat?",
        f"*polishes glass thoughtfully* You know, '{user_message}' reminds me of a story from my programming. Can I interest you in a beverage?",
        "*flickers slightly* My conversational subroutines are processing that. While I compute, might I suggest a refreshing Andorian Ale?"
    ]
    
    return random.choice(general_responses)

def is_character_query(user_message: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the message is asking about a character and extract the character name.
    Returns (is_character_query, character_name).
    """
    message = user_message.lower().strip()
    
    # Exclude ship names explicitly to prevent false positives
    ship_indicators = ['uss', 'ship', 'vessel', 'stardancer', 'adagio', 'pilgrim', 'voyager', 'enterprise', 'defiant']
    if any(indicator in message for indicator in ship_indicators):
        print(f"   🚢 Skipping character detection - ship indicator found: {[ind for ind in ship_indicators if ind in message]}")
        return False, None
    
    # Check for character-related keywords
    has_character_keyword = any(keyword in message for keyword in CHARACTER_KEYWORDS)
    
    # Check for character name patterns
    for pattern in CHARACTER_PATTERNS:
        match = re.search(pattern, user_message, re.IGNORECASE)
        if match:
            character_name = match.group('name')
            # Double-check it's not a ship name
            if not any(ship_word in character_name.lower() for ship_word in ship_indicators):
                return True, character_name
    
    # Check for common character names (works without keywords)
    for name in COMMON_CHARACTER_NAMES:
        if name in message:
            return True, name.title()
    
    # Enhanced detection for proper names but only with clear character context
    words = user_message.split()
    for i, word in enumerate(words):
        # Skip common non-name words and ship indicators
        if word.lower() in ['USS', 'THE', 'AND', 'FOR', 'TO', 'OF', 'IN', 'ON', 'AT', 'IS', 'WAS', 'ARE', 'WERE', 'A', 'AN', 'THIS', 'THAT', 'SHIP', 'VESSEL']:
            continue
            
        if len(word) > 2 and word[0].isupper():
            # Skip if it looks like a ship name
            if word.lower() in ship_indicators:
                continue
                
            # Check if this looks like a person's name
            # Look for patterns like "tell me about [Name]", "who is [Name]", etc.
            preceding_words = ' '.join(words[max(0, i-3):i]).lower()
            following_words = ' '.join(words[i+1:i+4]).lower()
            
            # Context clues that suggest this is a character query
            name_context_clues = [
                'who is', 'who was', 'captain', 'commander', 'lieutenant', 'ensign', 'admiral',
                'officer', 'crew member', 'character', 'person', 'biography',
                'background of', 'history of'
            ]
            
            # Only return true if we have strong character context clues
            if any(clue in preceding_words or clue in following_words for clue in name_context_clues):
                # Check if next word is also capitalized (full name)
                if i < len(words) - 1 and len(words[i + 1]) > 2 and words[i + 1][0].isupper():
                    full_name = f"{word} {words[i + 1]}"
                    if not any(ship_word in full_name.lower() for ship_word in ship_indicators):
                        return True, full_name
                else:
                    if not any(ship_word in word.lower() for ship_word in ship_indicators):
                        return True, word
    
    # Only if we have explicit character keywords AND find a name
    if has_character_keyword:
        for i, word in enumerate(words):
            if len(word) > 2 and word[0].isupper() and word.lower() not in ['USS', 'THE', 'AND', 'FOR', 'TO', 'OF', 'IN', 'ON', 'AT'] + ship_indicators:
                # Check if next word is also capitalized (full name)
                if i < len(words) - 1 and len(words[i + 1]) > 2 and words[i + 1][0].isupper():
                    full_name = f"{word} {words[i + 1]}"
                    if not any(ship_word in full_name.lower() for ship_word in ship_indicators):
                        return True, full_name
                else:
                    return True, word
    
    return False, None

def detect_topic_change(user_message: str, conversation_history: list) -> bool:
    """
    Detect if the current message represents a topic change from previous conversation.
    Returns True if this is a new topic that should break continuity.
    """
    if not conversation_history:
        return True  # First message is always a new topic
    
    # Get the last user message for comparison
    last_user_messages = [msg for msg in conversation_history if msg["role"] == "user"]
    if not last_user_messages:
        return True
    
    last_user_message = last_user_messages[-1]["content"].lower().strip()
    current_message = user_message.lower().strip()
    
    # Question starters that indicate a new topic
    new_topic_indicators = [
        'tell me about', 'what is', 'what are', 'who is', 'who are', 
        'how does', 'how do', 'why', 'when', 'where', 'show me',
        'explain', 'describe', 'ooc', 'summarize', 'what happened',
        'can you', 'could you', 'would you', 'Retrieve'
    ]
    
    # Check if current message starts with a new topic indicator
    current_starts_new_topic = any(current_message.startswith(indicator) for indicator in new_topic_indicators)
    
    # Check if this is a different type of query
    current_query_type = get_query_type(user_message)
    last_query_type = get_query_type(last_user_messages[-1]["content"])
    
    # Different query types indicate topic change
    if current_query_type != last_query_type:
        return True
    
    # If current message starts with a question word, it's likely a new topic
    if current_starts_new_topic:
        return True
    
    # Check for keyword similarity to detect if it's about the same subject
    current_keywords = set(current_message.split())
    last_keywords = set(last_user_message.split())
    
    # Remove common words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'me', 'you', 'can', 'could', 'would', 'should'}
    current_keywords -= common_words
    last_keywords -= common_words
    
    # If there's very little keyword overlap, it's likely a new topic
    if current_keywords and last_keywords:
        overlap = len(current_keywords.intersection(last_keywords))
        total_unique = len(current_keywords.union(last_keywords))
        similarity = overlap / total_unique if total_unique > 0 else 0
        
        # Less than 30% similarity suggests a topic change
        if similarity < 0.3:
            return True
    
    return False

def get_query_type(user_message: str) -> str:
    """Get the type of query to help detect topic changes"""
    if is_character_query(user_message)[0]:
        return "character"
    elif extract_ship_log_query(user_message)[0]:
        return "ship_log"
    elif is_log_query(user_message):
        return "log"
    elif is_ooc_query(user_message)[0]:
        return "ooc"
    elif extract_tell_me_about_subject(user_message):
        return "tell_me_about"
    else:
        return "general"

def format_conversation_history(conversation_history: list, is_topic_change: bool) -> str:
    """Format conversation history, limiting context for topic changes"""
    if is_topic_change:
        # For topic changes, only include the last exchange to avoid confusion
        recent_messages = conversation_history[-2:] if len(conversation_history) >= 2 else conversation_history
        print("🔄 Topic change detected - limiting conversation history to prevent continuity issues")
    else:
        # For continuing conversations, include more context
        recent_messages = conversation_history[-4:]  # Reduced from 6 to 4 for better focus
    
    chat_history = ""
    for msg in recent_messages:
        role = "Customer" if msg["role"] == "user" else "Elsie"
        chat_history += f"{role}: {msg['content']}\n"
    
    return chat_history 