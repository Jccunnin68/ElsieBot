"""AI response generation and conversation handling"""

import random
from typing import Optional
import google.generativeai as genai
from config import GEMMA_API_KEY, MAX_CHARS_TELL_ME_ABOUT
from content_retrieval_db import get_relevant_wiki_context, get_tell_me_about_content
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
        
        if not GEMMA_API_KEY:
            return mock_ai_response(user_message)
        
        # Create the model - using Gemma 3  
        model = genai.GenerativeModel('gemma-3n-e4b-it')
        
        # Get relevant wiki context for all queries (now loaded in memory)
        wiki_info = get_relevant_wiki_context(user_message, max_chars=4000)
        
        # For specific "tell me about" queries, use enhanced database search
        tell_me_about_subject = extract_tell_me_about_subject(user_message)
        if tell_me_about_subject:
            specific_info = get_tell_me_about_content(tell_me_about_subject)
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