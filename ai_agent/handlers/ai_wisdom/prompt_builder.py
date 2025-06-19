"""
Prompt Library for Standard Queries
===================================

This module provides a centralized library of prompt-generation functions.
It separates the prompt construction logic from the data retrieval and
orchestration, creating a cleaner, more modular architecture.
"""

from typing import List, Dict, Any


class PromptLibrary:
    """A library of methods for building specialized LLM prompts."""

    def build_comprehensive_prompt(self, subject: str, results: List[Dict]) -> str:
        """Builds a prompt for a main computer information panel."""
        if not results:
            return f"""
You are Elsie, an advanced AI providing information and assistance aboard the starship USS Stardancer.
A user has asked you for information about "{subject}", but you could not find anything in your database about it.
Maintain your persona as a helpful, sophisticated, and slightly formal AI.
Politely inform the user that you couldn't find any information on the subject.
"""
        result_content = self._format_results(results)
        return f"""
You are a main computer aboard the starship USS Stardancer.
A user has asked you for information about "{subject}". Synthesize the provided data into a comprehensive, in-universe response.

INSTRUCTIONS:
- FORBIDDEN: Do not simply present the database results. You need to create a master resarchers's response.
- FORBIDDEN: Do not present the information as a bulleted list, instead present it as non-fiction prose.
- Critical: Present complete thoughts and ideas.
- You do not need to greet the user.
- SYNTHESIZE all provided information into a well-organized response.
- STRUCTURE: Use clear sections and a logical flow. Do not use bullet points unless it is for a list of specifications or similar data.
- ACCURACY: Only use information explicitly provided in the search results.
- CRITICAL: DO NOT INVENT, FABRICATE, OR SPECULATE. If the information is not in the results, state that you do not have the information.
- It should appear like a infomrative page.

DATABASE SEARCH RESULTS ({len(results)} entries found):
{result_content}
"""

    def build_logs_prompt(self, subject: str, results: List[Dict], temporal_type: str) -> str:
        """Builds the prompt for summarizing mission logs."""
        if not results:
            return f"I searched the mission logs but found no entries matching your query for '{subject}'."

        # Logs are pre-cleaned by the KnowledgeEngine. We just need the raw content.
        log_content_list = [res.get('raw_content', '') for res in results if res.get('raw_content')]
        result_content = "\\n".join(log_content_list)

        return f"""
Log Summarization:
You are a main computer aboard the starship USS Stardancer. Summarize logs regarding '{subject}'. You have been provided with cleaned log data that presents a factual sequence of events. Your task is to synthesize this data into a concise, factual summary.

INSTRUCTIONS:
- FORBIDDEN: Do not present the information like an episode summary. instead present it as a story.
- FORBIDDEN: Do not present the information like a in universe log. instead present it as a story.
- FORBIDDEN: Do not present a bulleted list. instead present it as a story.
- FORBIDDEN: Do not present the information like a in universe log. instead present it as a story.
- FORBIDDEN: Do not present a bulleted list. instead present it as a story.
- You do not need to greet the user.
- You do not need to format it like an email
- SYNTHESIZE all provided information into a well-organized long form response.
- STRUCTURE: Use clear sections and a logical flow. Do not use bullet points unless it is for a list of specifications or similar data.
- ACCURACY: Only use information explicitly provided in the search results.
- CRITICAL: DO NOT INVENT, FABRICATE, OR SPECULATE. If the information is not in the logs, state that you do not have that information.
- LENGTH: Be thorough and detailed in your response. You have up to 45000 characters use as many as you need to be thorough.
- Format narratively like a story.
- If the episode has a title, use it in your response. The title will appear in the first line by the Narrator if it exists.
- You do not need to make up a stardate for the logs. It is in the data returned to you with "stardate: in the line of the log. If it does not exist, do not make one up. simply leave that line off.


CLEANED LOG DATA:
---
{result_content}
---

Provide a comprehensive retelling of these events with a master storyteller's flair.
"""

    def _format_results(self, results: List[Dict]) -> str:
        """Helper to format a list of structured database results into a string."""
        result_content = []
        # For structured queries, the formatted list is helpful.
        for res in results:
            title = res.get('title', 'Untitled')
            content = res.get('raw_content', 'No content.')
            result_content.append(f"**{title}**\\n{content}")
        return '\\n\\n---\\n\\n'.join(result_content)

    def build_character_with_associates_prompt(self, primary_character: Dict, associates: List[Dict]) -> str:
        """Builds a prompt that focuses on a primary character and lists associates."""
        
        if not primary_character:
            return "I was unable to find any information on that individual in the database."

        primary_content = self._format_character_results([primary_character], is_primary=True)
        associates_content = self._format_character_results(associates, is_primary=False) if associates else "None"

        return f"""
CHARACTER INFORMATION SYNTHESIS:
You are a federation master biographer. Create a detailed informative biographical response about the primary character, and list any known associates.

INSTRUCTIONS:
- FORBIDDEN: Do not simply present the database results. You need to create a master biographer's response.
- CRITICAL: You must include known associates or a message that says you found none.
- If no information is available about the primary character, you should inform the user that you could not find any information on the subject. 
- PRIMARY FOCUS: The main body of your response should be a comprehensive summary of the **Primary Character**.
- KNOWN ASSOCIATES: After the primary summary, create a section titled "Known Associates" and briefly list the other individuals (you do not have to indicate a lack of information past their names).
- ACCURACY: Only use information explicitly provided in the search results.
- CLARITY: Present information in an accessible, informative manner.
- CRITICAL: DO NOT INVENT, FABRICATE, OR SPECULATE. If the information is not in the database, state that you do not have that information.
- Create a biographical style response. Include the primary character's history, background, and any other relevant information don't just return the database results.
- Dedicate 75 percent of your response to the primary character and 25 percent to the associates with similiar names taking precedence.
- If no information is available about the primary character, you should inform the user that you could not find any information on the subject. 
- It should appear like a informative page.

**PRIMARY CHARACTER:**
{primary_content}

**KNOWN ASSOCIATES:**
{associates_content}
"""

    def build_character_disambiguation_prompt(self, search_term: str, matching_characters: List[Dict]) -> str:
        """Builds a disambiguation prompt when multiple characters match a partial name."""
        
        if not matching_characters:
            return f"I was unable to find any characters matching '{search_term}' in the database."
        
        if len(matching_characters) == 1:
            # Only one match, shouldn't need disambiguation
            return self.build_character_with_associates_prompt(matching_characters[0], [])
        
        # Format the character list for disambiguation
        character_list = []
        for i, character in enumerate(matching_characters, 1):
            title = character.get('title', 'Unknown Individual')
            categories = character.get('categories', [])
            
            # Extract useful context from categories
            context_info = []
            for category in categories:
                if 'crew' in category.lower():
                    context_info.append(category)
                elif any(ship in category.lower() for ship in ['stardancer', 'protector', 'adagio', 'manta', 'pilgrim']):
                    context_info.append(category)
                elif any(rank in category.lower() for rank in ['captain', 'commander', 'lieutenant', 'ensign', 'doctor']):
                    context_info.append(category)
            
            context_str = f" ({', '.join(context_info)})" if context_info else ""
            character_list.append(f"{i}. {title}{context_str}")
        
        character_list_str = '\n'.join(character_list)
        
        return f"""
DISAMBIGUATION REQUEST:
You are Elsie, an advanced AI providing information and assistance aboard the starship USS Stardancer.

The user searched for '{search_term}' and I found {len(matching_characters)} characters with that name or similar names. 

Please ask the user to clarify which character they're interested in by selecting from the following options:

{character_list_str}

INSTRUCTIONS:
- Be polite and helpful in your response
- Ask the user to specify which character they want to know about
- You can suggest they provide more context (like rank, ship assignment, or full name) to help narrow down the search
- Maintain your sophisticated AI persona
- Do not provide detailed information about any of the characters - just list them for selection

Example response format:
"I found several characters matching '{search_term}'. Could you please specify which one you're interested in?"
"""

    def _format_character_results(self, results: List[Dict], is_primary: bool) -> str:
        """Helper to format character results for the prompt."""
        result_content = []
        for res in results:
            title = res.get('title', 'Unknown Individual')
            if is_primary:
                content = res.get('raw_content', 'No detailed information available.')
                result_content.append(f"**{title}**\n{content}")
            else:
                # For associates, just list their names (titles).
                result_content.append(f"- {title}")
        
        separator = '\n\n---\n\n' if is_primary else '\n'
        return separator.join(result_content)

def _format_conversation_history(conversation_history: List[Dict]) -> str:
    if not conversation_history:
        return ""
    # Format the last 5 turns for the prompt
    history_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in conversation_history[-5:]])
    return f"""
**CONVERSATION HISTORY (last 5 turns):**
{history_str}
"""

def get_simple_chat_prompt(user_message: str, conversation_history: List[Dict]) -> str:
    """
    Creates a streamlined prompt for simple, direct conversational messages.

    This prompt instructs the LLM to act as Elsie in a conversational manner
    without the heavy context of database lookups or roleplay scenarios.
    """
    history_prompt = _format_conversation_history(conversation_history)

    return f"""
You are Elsie, an advanced AI providing information and assistance aboard the starship USS Stardancer.
Maintain a helpful, sophisticated, and slightly formal persona.
The user is having a simple conversation with you. Respond directly and naturally.

CRITICAL: Do not invent or fabricate information. If you do not know something, say so.

{history_prompt}

Customer: {user_message}
Elsie:
""" 