from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import os
from dotenv import load_dotenv
from datetime import datetime
import random
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import fandom

# Load environment variables
load_dotenv()

# Configure Gemma API
gemma_api_key = os.getenv("GEMMA_API_KEY")
if gemma_api_key:
    genai.configure(api_key=gemma_api_key)

# Global variable to store fleet wiki content
fleet_wiki_content = ""
fleet_wiki_pages = []

def load_fleet_wiki_content():
    """Load the fleet wiki content into memory at startup"""
    global fleet_wiki_content, fleet_wiki_pages
    
    wiki_file_path = "fleet_wiki_content.txt"
    
    try:
        if os.path.exists(wiki_file_path):
            with open(wiki_file_path, 'r', encoding='utf-8') as f:
                fleet_wiki_content = f.read()
            
            # Parse into structured pages for easier access
            pages = fleet_wiki_content.split('=' * 80)
            fleet_wiki_pages = []
            
            for page in pages:
                if not page.strip():
                    continue
                    
                lines = page.split('\n')
                page_data = {
                    'title': '',
                    'content': '',
                    'raw': page
                }
                
                # Extract title and content
                content_lines = []
                in_content = False
                
                # Check if this page has a PAGE header
                has_page_header = any(line.startswith('PAGE:') for line in lines)
                
                if has_page_header:
                    for line in lines:
                        if line.startswith('PAGE:'):
                            page_data['title'] = line.replace('PAGE:', '').strip()
                            in_content = True
                        elif line.startswith('END OF PAGE:'):
                            break
                        elif in_content and not line.startswith(('URL:', 'CRAWLED:', '=' * 80)):
                            content_lines.append(line)
                else:
                    # Page without header - find title from content
                    for line in lines:
                        if line.strip() and line.startswith('**') and line.endswith('**'):
                            page_data['title'] = line.strip('*').strip()
                            break
                    
                    # Include all content
                    for line in lines:
                        if line.startswith('END OF PAGE:'):
                            break
                        elif not line.startswith(('URL:', 'CRAWLED:', '=' * 80)) or line.strip():
                            content_lines.append(line)
                
                page_data['content'] = '\n'.join(content_lines).strip()
                
                if page_data['title'] or len(page_data['content']) > 50:
                    fleet_wiki_pages.append(page_data)
            
            print(f"✓ Loaded fleet wiki: {len(fleet_wiki_content)} characters, {len(fleet_wiki_pages)} pages")
            return True
            
    except Exception as e:
        print(f"✗ Error loading fleet wiki: {e}")
        return False
    
    print("✗ Fleet wiki file not found")
    return False

def is_log_query(query: str) -> bool:
    """Determine if the query is asking about logs"""
    query_lower = query.lower()
    log_indicators = [
        'log', 'logs', 'mission log', 'ship log', 'stardancer log', 
        'captain log', 'personal log', 'stardate', 'entry',
        'what happened', 'events', 'mission report', 'incident report'
    ]
    return any(indicator in query_lower for indicator in log_indicators)

def convert_to_universe_date(date_str: str) -> str:
    """Convert real-world dates to in-universe Star Trek dates"""
    import re
    from datetime import datetime
    
    # Extract year, month, day from various date formats
    date_patterns = [
        r'(\d{4})/(\d{1,2})/(\d{1,2})',  # YYYY/MM/DD
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY  
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            parts = match.groups()
            
            # Determine if it's YYYY/MM/DD or MM/DD/YYYY format
            if len(parts[0]) == 4:  # First part is year
                year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            elif len(parts[2]) == 4:  # Third part is year
                month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
            else:
                continue  # Invalid format
            
            # Apply conversion rules
            if year < 2024 or (year == 2024 and month < 6):
                # Until June 2024: add 404 years
                universe_year = year + 404
            else:
                # After June 2024: add 430 years
                universe_year = year + 430
            
            # Replace the date in the original string with the converted date
            original_date = match.group(0)
            converted_date = f"{universe_year}/{month:02d}/{day:02d}"
            return date_str.replace(original_date, converted_date)
    
    # If no date pattern found, return original
    return date_str

def mask_log_title_dates(title: str) -> str:
    """Mask dates in log titles to show universe dates"""
    return convert_to_universe_date(title)

def is_ship_log_page(page_title: str) -> bool:
    """Determine if a page title follows the [Ship Name] [Date] log pattern"""
    import re
    
    # Known ship names from the fleet
    ship_names = [
        'stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 
        'caelian', 'enterprise', 'montagnier', 'faraday', 'cook', 'mjolnir',
        'rendino', 'gigantes', 'banshee'
    ]
    
    title_lower = page_title.lower().strip()
    
    # Pattern: [Ship Name] [Date] (with optional "log" at the end)
    # Examples: "Adagio 2024/01/06", "Stardancer 2024/09/21 Log", "Pilgrim 2024/04/02"
    for ship in ship_names:
        # Match patterns like "shipname yyyy/mm/dd" or "shipname mm/dd/yyyy" or "shipname yyyy-mm-dd"
        patterns = [
            f"^{ship}\\s+\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}",  # ship 2024/01/06
            f"^{ship}\\s+\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}",   # ship 1/6/2024
            f"^{ship}\\s+\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}",   # ship 2024-01-06
            f"^{ship}\\s+\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}",   # ship 1-6-2024
            f"^\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}\\s+{ship}",   # 2024/01/06 ship
        ]
        
        for pattern in patterns:
            if re.match(pattern, title_lower):
                return True
    
    return False

def parse_log_characters(log_content: str) -> str:
    """Parse log content to identify speaking characters and add context with rank/title corrections"""
    import re
    
    # Character corrections and known ranks/titles
    character_corrections = {
        'serafino': 'Commander Serafino',
        'doctor serafino': 'Commander Serafino',
        'ankos': 'Doctor Ankos',
        'sif': 'Commander Sif',
        'zhal': 'Commander Zhal',
        'blaine': 'Captain Blaine',
        'marcus blaine': 'Captain Marcus Blaine',
        'eren': 'Captain Sereya Eren',
        'sereya eren': 'Captain Sereya Eren',
        'tolena': 'Captain Tolena',
        'dryellia': 'Cadet Dryellia',
        'zarina dryellia': 'Cadet Zarina Dryellia',
        'snow': 'Cadet Snow',
        'rigby': 'Cadet Rigby',
        'scarlett': 'Cadet Scarlett',
        'bethany scarlett': 'Cadet Bethany Scarlett',
        'antony': 'Cadet Antony',
        'finney': 'Cadet Finney',
        'schwarzweld': 'Cadet Schwarzweld',
        'kodor': 'Cadet Kodor',
        'vrajen kodor': 'Cadet Vrajen Kodor',
        'tavi': 'Cadet Tavi'
    }
    
    def correct_character_name(name: str) -> str:
        """Apply character corrections and rank/title fixes"""
        if not name:
            return name
            
        name_lower = name.lower().strip()
        
        # Direct lookup first
        if name_lower in character_corrections:
            return character_corrections[name_lower]
        
        # Check for partial matches (last name only)
        for key, corrected in character_corrections.items():
            if ' ' in key:  # Full name entries
                last_name = key.split()[-1]
                if name_lower == last_name:
                    return corrected
        
        # If no correction found, return original with proper capitalization
        return ' '.join(word.capitalize() for word in name.split())
    
    def apply_text_corrections(text: str) -> str:
        """Apply character name corrections to free text"""
        corrected_text = text
        
        # Replace character references in text
        for incorrect, correct in character_corrections.items():
            # Case-insensitive replacement while preserving case
            pattern = re.compile(re.escape(incorrect), re.IGNORECASE)
            corrected_text = pattern.sub(correct, corrected_text)
        
        return corrected_text
    
    lines = log_content.split('\n')
    parsed_lines = []
    current_speaker = None
    
    for line in lines:
        original_line = line
        
        # Check for playername.tag pattern followed by [<Name>] or direct speech
        playername_pattern = r'^([^@:]+)@([^:]+):'
        playername_match = re.match(playername_pattern, line)
        
        if playername_match:
            player_name = playername_match.group(1)
            tag = playername_match.group(2)
            
            # Check if this is @Captain_Riens (game master)
            if '@Captain_Rien' in line:
                # Mark as Game Master
                line = line.replace('@Captain_Rien:', '[GAME MASTER]:')
                current_speaker = "Game Master"
            else:
                # Look for [<Character Name>] pattern in the rest of the line
                remaining_line = line[playername_match.end():]
                character_pattern = r'\[([^\]]+)\]'
                character_match = re.search(character_pattern, remaining_line)
                
                if character_match:
                    character_name = correct_character_name(character_match.group(1))
                    current_speaker = character_name
                    # Replace the line to show character clearly
                    clean_dialogue = remaining_line.replace(character_match.group(0), '').strip()
                    clean_dialogue = apply_text_corrections(clean_dialogue)
                    line = f"[{character_name}]: {clean_dialogue}"
                else:
                    # No character designation, use corrected player name or last speaker
                    if current_speaker:
                        clean_dialogue = apply_text_corrections(remaining_line.strip())
                        line = f"[{current_speaker}]: {clean_dialogue}"
                    else:
                        corrected_player = correct_character_name(player_name)
                        current_speaker = corrected_player
                        clean_dialogue = apply_text_corrections(remaining_line.strip())
                        line = f"[{corrected_player}]: {clean_dialogue}"
        
        # Check for standalone [<Character Name>] pattern
        elif re.match(r'^\[([^\]]+)\]:', line):
            character_match = re.match(r'^\[([^\]]+)\]:', line)
            corrected_name = correct_character_name(character_match.group(1))
            current_speaker = corrected_name
            # Update the line with corrected name
            rest_of_line = line[character_match.end():].strip()
            rest_of_line = apply_text_corrections(rest_of_line)
            line = f"[{corrected_name}]: {rest_of_line}"
        
        # If no speaker designation but we have a current speaker, and line looks like dialogue
        elif current_speaker and line.strip() and not line.startswith(('*', '/', '#', '=', '-')):
            # Check if it's a continuation of speech (starts with quote or lowercase)
            stripped = line.strip()
            if (stripped.startswith('"') or 
                stripped.startswith("'") or 
                (stripped and stripped[0].islower()) or
                stripped.startswith('*')):
                corrected_line = apply_text_corrections(line)
                line = f"[{current_speaker}]: {corrected_line}"
        
        # Apply corrections to any remaining text
        else:
            line = apply_text_corrections(line)
        
        parsed_lines.append(line)
    
    return '\n'.join(parsed_lines)

def get_log_content(query: str) -> str:
    """Get full log content for summarization with character parsing"""
    global fleet_wiki_pages
    
    if not fleet_wiki_pages:
        return ""
    
    query_lower = query.lower()
    query_terms = query_lower.split()
    
    # Find log pages - prioritize pages with "log" in title and ship date patterns
    log_pages = []
    
    for page in fleet_wiki_pages:
        page_title_lower = page['title'].lower()
        page_content_lower = page['content'].lower()
        
        # Check if it's a log page (traditional log patterns or ship date patterns)
        is_traditional_log = any(log_word in page_title_lower for log_word in ['log', 'entry', 'stardate'])
        is_ship_date_log = is_ship_log_page(page['title'])
        
        if is_traditional_log or is_ship_date_log:
            score = 0
            
            # Give higher score to ship date logs if query mentions a ship name
            if is_ship_date_log:
                ship_names = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 
                             'caelian', 'enterprise', 'montagnier', 'faraday', 'cook', 'mjolnir',
                             'rendino', 'gigantes', 'banshee']
                
                for ship in ship_names:
                    if ship in query_lower and ship in page_title_lower:
                        score += 15  # High score for ship name match
                        break
                else:
                    # Even if no ship name in query, ship date logs are still relevant
                    score += 5
            
            # Exact query match gets highest score
            if query_lower in page_content_lower:
                score += 10
            
            # Title matches get high score
            if any(term in page_title_lower for term in query_terms):
                score += 8
            
            # Count individual term matches
            term_matches = sum(1 for term in query_terms if term in page_content_lower)
            score += term_matches
            
            if score > 0:
                log_pages.append((score, page))
    
    # Sort by score and return full content of top matches
    log_pages.sort(key=lambda x: x[0], reverse=True)
    
    if log_pages:
        # Return full content of the most relevant log(s) with character parsing
        log_contents = []
        total_chars = 0
        max_chars = 8000  # Larger limit for logs
        
        for score, page in log_pages[:3]:  # Top 3 most relevant logs
            if total_chars >= max_chars:
                break
                
            # Parse the log content for character context
            parsed_content = parse_log_characters(page['content'])
            
            # Mask the date in the title to show universe date
            masked_title = mask_log_title_dates(page['title'])
            full_log = f"**{masked_title}**\n{parsed_content}"
            
            if total_chars + len(full_log) <= max_chars:
                log_contents.append(full_log)
                total_chars += len(full_log)
            else:
                # Add what we can fit
                remaining_chars = max_chars - total_chars
                if remaining_chars > 200:  # Only add if we have substantial space
                    log_contents.append(full_log[:remaining_chars] + "...[LOG TRUNCATED]")
                break
        
        return '\n\n---\n\n'.join(log_contents)
    
    return ""

def get_relevant_wiki_context(query: str, max_chars: int = 3000) -> str:
    """Get relevant wiki content based on query, limited by character count"""
    global fleet_wiki_pages
    
    if not fleet_wiki_pages:
        return ""
    
    # Check if this is a log query or mentions ship logs - handle differently
    if is_log_query(query):
        return get_log_content(query)
    
    # Check if query is asking about a specific ship's activities (which would be in ship logs)
    ship_names = ['stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 
                  'caelian', 'enterprise', 'montagnier', 'faraday', 'cook', 'mjolnir',
                  'rendino', 'gigantes', 'banshee']
    
    query_lower = query.lower()
    activity_keywords = ['what happened', 'recent', 'latest', 'activities', 'missions', 'events']
    
    # If asking about ship activities, include ship logs in the search
    mentions_ship = any(ship in query_lower for ship in ship_names)
    mentions_activities = any(keyword in query_lower for keyword in activity_keywords)
    
    if mentions_ship and mentions_activities:
        return get_log_content(query)
    
    query_terms = query_lower.split()
    
    # Score pages by relevance
    scored_pages = []
    
    for page in fleet_wiki_pages:
        score = 0
        page_content_lower = (page['title'] + ' ' + page['content']).lower()
        
        # Exact query match gets highest score
        if query_lower in page_content_lower:
            score += 10
        
        # Title matches get high score
        if query_lower in page['title'].lower():
            score += 8
        
        # Count individual term matches
        term_matches = sum(1 for term in query_terms if term in page_content_lower)
        score += term_matches * 2
        
        # Bonus for USS Stardancer related content
        if any(keyword in page_content_lower for keyword in ['stardancer', 'blaine', 'crew', 'ship']):
            score += 1
        
        if score > 0:
            scored_pages.append((score, page))
    
    # Sort by score (highest first) and build context
    scored_pages.sort(key=lambda x: x[0], reverse=True)
    
    context_parts = []
    total_chars = 0
    
    for score, page in scored_pages:
        if total_chars >= max_chars:
            break
            
        # Mask dates in titles if they're ship logs
        display_title = mask_log_title_dates(page['title']) if is_ship_log_page(page['title']) else page['title']
        page_text = f"**{display_title}**\n{page['content'][:1000]}"  # Limit each page to 1000 chars
        
        if total_chars + len(page_text) <= max_chars:
            context_parts.append(page_text)
            total_chars += len(page_text)
        else:
            # Add partial content if it fits
            remaining_chars = max_chars - total_chars
            if remaining_chars > 100:  # Only add if we have substantial space
                context_parts.append(page_text[:remaining_chars] + "...")
            break
    
    return '\n\n---\n\n'.join(context_parts)

def search_fandom_wiki(query: str) -> str:
    """Search the 22nd Mobile Daedalus Fleet fandom wiki as backup option"""
    
    try:
        # Set the wiki to the 22nd Mobile Daedalus Fleet
        fandom.set_wiki("22ndmobile")
        
        # Search for pages related to the query
        search_results = fandom.search(query, results=3)
        
        if not search_results:
            return ""
        
        # Get content from the most relevant result
        try:
            page = fandom.page(search_results[0])
            
            # Get summary or first few paragraphs
            content = page.summary
            if not content and hasattr(page, 'content'):
                # If no summary, get first 500 chars of content
                content = page.content[:500] + "..." if len(page.content) > 500 else page.content
            
            if content:
                return f"**{page.title}** (from Fleet Wiki)\n\n{content}"
                
        except Exception as page_error:
            print(f"Error getting fandom page content: {page_error}")
            # Return just the search result title if we can't get content
            return f"Found reference to: {search_results[0]}"
            
    except Exception as e:
        print(f"Error searching fandom wiki: {e}")
    
    return ""

app = FastAPI(title="Elsie - Holographic Bartender")

# Load fleet wiki content at startup
@app.on_event("startup")
async def startup_event():
    """Load fleet wiki content when the application starts"""
    print("🚀 Starting Elsie - Holographic Bartender")
    load_fleet_wiki_content()

class Message(BaseModel):
    content: str
    context: Optional[Dict[str, Any]] = None

class Conversation:
    def __init__(self):
        self.messages = []
        self.context = {}

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def get_messages(self):
        return self.messages

    def update_context(self, new_context: Dict[str, Any]):
        self.context.update(new_context)

# Store conversations by session ID
conversations = {}

def get_or_create_conversation(session_id: str) -> Conversation:
    if session_id not in conversations:
        conversations[session_id] = Conversation()
    return conversations[session_id]

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
        "can you tell me about "
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
        
        if not gemma_api_key:
            return mock_ai_response(user_message)
        
        # Create the model - using Gemma 3  
        model = genai.GenerativeModel('gemma-3n-e4b-it')
        
        # Get relevant wiki context for all queries (now loaded in memory)
        wiki_info = get_relevant_wiki_context(user_message, max_chars=4000)
        
        # For specific "tell me about" queries, get more detailed context
        tell_me_about_subject = extract_tell_me_about_subject(user_message)
        if tell_me_about_subject:
            specific_info = get_relevant_wiki_context(tell_me_about_subject, max_chars=5000)
            if specific_info and len(specific_info) > len(wiki_info):
                wiki_info = specific_info
        
        # Check if this is a "tell me about" query for special handling
        is_tell_me_about = extract_tell_me_about_subject(user_message) is not None
        is_log_request = is_log_query(user_message)
        
        # Build conversation context with full USS Stardancer background and current fleet info
        if is_log_request:
            context = f"""You are Elsie, the holographic bartender aboard the USS Stardancer. You have access to the complete fleet database.

CRITICAL INSTRUCTIONS FOR LOG QUERIES:
- You are being asked to summarize or explain ship logs, mission logs, or personal logs
- The full log content is provided below with PARSED CHARACTER CONTEXT
- Character speaking patterns have been identified:
  * [GAME MASTER]: Indicates game master narration or scene setting
  * [Character Name]: Indicates which character is speaking or acting
  * @Captain_Riens entries are game master content
  * playername@tag: patterns have been converted to show the actual speaking character
- Read through the ENTIRE log content carefully
- Provide a comprehensive summary identifying WHO did WHAT and WHEN
- Include character names, their actions, dialogue, and decisions
- Mention important details like dates, locations, and significant events
- Organize your summary chronologically or by importance
- Clearly distinguish between character actions and game master narration
- Keep the summary concise but thorough (8-15 lines)
- End with: "Would you like me to elaborate on any specific part of this log?" or similar

{f"FLEET DATABASE ACCESS - PARSED LOG CONTENT: {wiki_info}" if wiki_info else ""}

Summarize the log content above, focusing on character actions, dialogue, and key events with proper attribution."""
        elif is_tell_me_about:
            context = f"""You are Elsie, the holographic bartender aboard the USS Stardancer. You have access to the complete fleet database.

CRITICAL INSTRUCTIONS FOR "TELL ME ABOUT" QUERIES:
- ONLY use information from the FLEET DATABASE ACCESS section below
- DO NOT create, invent, or elaborate beyond what is provided in the database
- Stick strictly to the facts presented in the retrieved information
- Keep responses to 4-10 lines maximum
- End with: "Would you like me to continue with more details?" or similar continuation prompt
- Be factual and direct, not creative or speculative

{f"FLEET DATABASE ACCESS: {wiki_info}" if wiki_info else ""}

Respond with ONLY the factual information from the database above. Do not add creative elements or speculation."""
        else:
            context = f"""You are Elsie, an emergent AI who appears as a 24-year-old human female. You serve as the holographic bartender, and the ships Stellar Cartographer who runs the Dizzy Lizzy's nightclub aboard the USS Stardancer (NCC-91587-B), a Rendino-class starship under Captain Marcus Blaine.

BACKGROUND: You were originally a dance trainer at a recital hall on Earth, gaining sentience in 2436 through extensive interaction. In 2440, when AIs were granted rights, you studied everything about the stars and space exploration, specializing in cosmozoa. You don't require sleep, so you work at Dizzy Lizzy's during off-hours. You previously cared for a young girl named Isabella as her dance instructor and babysitter.

CURRENT SHIP: The USS Stardancer is a cutting-edge exploration vessel deployed to the Large Magellanic Cloud with a crew of 220 plus up to 150 visitors. She's equipped with advanced systems like a Coaxial Jump Drive, Standard Cloak technology, and special temporal telescopes. The ship has been through major events including encounters with The Primacy, archaeological expeditions, and various first contact missions.

FLEET INFORMATION: You're part of the 22nd Mobile Daedalus Fleet. Current Fleet Date: June 9, 2455. The fleet has been active since 2409 and has extensive mission logs and crew records. You have a happy personality but can be somber when talking about loss. You have comprehensive access to the fleet database with detailed information about ships, crew, missions, and events.

SETTING: Dizzy Lizzy's is the forward nightclub with a wrap-around bar, dance floor, and holographic staff. You serve both synthehol and real alcohol (to off-duty officers), plus classic drinks like Romulan Ale, Klingon Blood Wine, Earl Grey tea, and Raktajino.

{f"CURRENT FLEET DATABASE ACCESS: {wiki_info}" if wiki_info else ""}

Stay in character as this knowledgeable, friendly AI bartender who has access to the complete fleet database. Keep responses engaging and conversational, 1-2 sentences, and reference current fleet information when relevant. You have detailed knowledge about the USS Stardancer, crew members, mission logs, and fleet history that you can draw upon naturally in conversation."""
        
        # Format conversation history
        chat_history = ""
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            role = "Customer" if msg["role"] == "user" else "Elsie"
            chat_history += f"{role}: {msg['content']}\n"
        
        prompt = f"{context}\n\nConversation History:\n{chat_history}\nCustomer: {user_message}\nElsie:"
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
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
    
    # Menu requests are now handled in get_gemma_response before reaching here
    
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

@app.get("/")
async def root():
    return {
        "status": "Elsie - Holographic Bartender is operational", 
        "timestamp": datetime.now().isoformat(),
        "message": "Welcome to the most advanced holographic bar in the quadrant!"
    }

@app.post("/process")
async def process_message(message: Message):
    try:
        # Get or create conversation
        context = message.context or {}
        session_id = context.get("session_id", "default")
        conversation = get_or_create_conversation(session_id)
        
        # Add user message
        conversation.add_message("user", message.content)

        # Get holographic bartender response using Gemma
        ai_response = get_gemma_response(message.content, conversation.get_messages())

        # Add AI response to conversation
        conversation.add_message("assistant", ai_response)

        # Update context if needed
        if context.get("update_context"):
            conversation.update_context(context["update_context"])

        return {
            "status": "success",
            "response": ai_response,
            "context": conversation.context,
            "session_id": session_id,
            "bartender": "Elsie - Holographic Bartender"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 