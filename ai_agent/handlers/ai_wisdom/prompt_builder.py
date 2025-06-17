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
        """Builds the prompt for a comprehensive information synthesis."""
        if not results:
            return f"""
You are Elsie, an advanced AI providing information and assistance aboard the starship USS Stardancer.
A user has asked you for information about "{subject}", but you could not find anything in your database about it.
Maintain your persona as a helpful, sophisticated, and slightly formal AI.
Politely inform the user that you couldn't find any information on the subject.

User: Tell me about {subject}
Elsie:
"""

        result_content = self._format_results(results)
        
        return f"""
COMPREHENSIVE INFORMATION SYNTHESIS:
Create a detailed informative response about: {subject}

INSTRUCTIONS:
- SYNTHESIZE all provided information into a comprehensive, well-organized response.
- STRUCTURE: Use clear sections and logical flow to present the information.
- ACCURACY: Only use information explicitly provided in the search results.
- CLARITY: Present information in an accessible, informative manner.

DATABASE SEARCH RESULTS ({len(results)} entries found):
{result_content}
"""

    def build_logs_prompt(self, subject: str, results: List[Dict], temporal_type: str) -> str:
        """Builds the prompt for narrative log storytelling."""
        if not results:
            return f"I searched the mission logs but found no entries matching your query for '{subject}'."

        result_content = self._format_results(results, is_log=True)

        return f"""
LOG NARRATIVE STORYTELLING:
Transform the following {temporal_type} log information for '{subject}' into a compelling NARRATIVE STORY format.

INSTRUCTIONS:
- Create a NARRATIVE STRUCTURE with a beginning, middle, and end.
- STORY FLOW: Connect events chronologically and thematically.
- IMMERSIVE DETAILS: Use the rich details from the logs to paint vivid scenes.
- MAINTAIN ACCURACY: Only use information explicitly provided in the logs.
- NARRATIVE VOICE: Write in an engaging, story-telling style that brings the events to life.

DATABASE SEARCH RESULTS ({len(results)} entries found):
{result_content}
"""

    def _format_results(self, results: List[Dict], is_log: bool = False) -> str:
        """Helper to format a list of database results into a string."""
        result_content = []
        for res in results:
            title = res.get('title', 'Untitled Log' if is_log else 'Untitled')
            content = res.get('raw_content', 'No content.')
            result_content.append(f"**{title}**\n{content}")
        
        return '\n\n---\n\n'.join(result_content)

    def build_character_with_associates_prompt(self, primary_character: Dict, associates: List[Dict]) -> str:
        """Builds a prompt that focuses on a primary character and lists associates."""
        
        primary_content = self._format_character_results([primary_character], is_primary=True)
        associates_content = self._format_character_results(associates, is_primary=False) if associates else "None"

        return f"""
CHARACTER INFORMATION SYNTHESIS:
Create a detailed informative response about the primary character, and list any known associates.

INSTRUCTIONS:
- If no information is available about the primary character, you should inform the user that you could not find any information on the subject. With an Star Trek style tone.
- PRIMARY FOCUS: The main body of your response should be a comprehensive summary of the **Primary Character**.
- KNOWN ASSOCIATES: After the primary summary, create a section titled "Known Associates" and briefly list the other individuals (you do not have to indicate a lack of information past their names).
- ACCURACY: Only use information explicitly provided in the search results.
- CLARITY: Present information in an accessible, informative manner.
- Dedicate 75 percent of your response to the primary character and 25 percent to the associates with similiar names taking precedence.
- If no information is available about the primary character, you should inform the user that you could not find any information on the subject. With an Star Trek style tone.

**PRIMARY CHARACTER:**
{primary_content}

**KNOWN ASSOCIATES:**
{associates_content}
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

{history_prompt}

Customer: {user_message}
Elsie:
""" 