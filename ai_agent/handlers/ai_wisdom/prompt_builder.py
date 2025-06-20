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

        # Determine the context based on temporal type and subject
        context_description = self._get_log_context_description(subject, temporal_type, len(results))

        return f"""
Log Summarization:
Your task is to summarize the log data that presents a factual sequence of events in the style of a historical narrative. {context_description} You have been provided with cleaned log data that presents a factual sequence of events. Your task is to synthesize this data into a concise, factual summary.

INSTRUCTIONS:
- FORBIDDEN: Do not present the information like an episode summary. instead present it as a story.
- FORBIDDEN: Do not present the information like a in universe log. instead present it as a story.
- FORBIDDEN: Do not present a bulleted list. instead present it as a story.
- FORBIDDEN: Do not invent positions for the characters. Assume the reader knows the positions of the characters.
- FORBIDDEN: Inventing relationships between characters not described in the logs.
- IMPERATIVE: You must include a title for the result you may find a title the Setting scenes at the start fo the episode to use just after the title card. (Star Trek: Stardancer "TITLE" Pattern) It varies for ships but roughly follows this pattern.
- SYNTHESIZE all provided information into a well-organized long form response.
- STRUCTURE: Use clear sections and a logical flow. Do not use bullet points unless it is for a list of specifications or similar data. The -setting- events will always be the first set of actions until the first post in a -Scene- Channel, after that -setting- will augment, use the line numbers as references to action happening at the same time.
- ACCURACY: Only use information explicitly provided in the search results.
- CRITICAL: DO NOT INVENT, FABRICATE, OR SPECULATE. If the information is not in the logs, state that you do not have that information.
- LENGTH: Be thorough and detailed in your response. You have up to 32000 characters use as many as you need to be thorough.
- Make sure to include all storylines even side storylines.
- You do not need to make up a stardate for the logs. It is in the data returned to you with "stardate: in the line of the log. If it does not exist, do not make one up. simply leave that line off.


CLEANED LOG DATA:
---
{result_content}
---

Provide a comprehensive retelling of these events with a master historical narrative storyteller's flair.
"""

    def _get_log_context_description(self, subject: str, temporal_type: str, result_count: int) -> str:
        """
        Generate appropriate context description based on the type of log query.
        
        Args:
            subject: The subject of the log query
            temporal_type: The temporal modifier (latest, first, recent, random)
            result_count: Number of results found
            
        Returns:
            Context description for the prompt
        """
        # Handle special subjects
        if subject == 'mission':
            if temporal_type == 'random':
                return f"Summarize this randomly selected mission from the fleet records."
            elif temporal_type == 'latest':
                return f"Summarize the most recent mission from the fleet records."
            elif temporal_type == 'first':
                return f"Summarize the earliest mission from the fleet records."
            else:
                return f"Summarize recent missions from the fleet records."
        
        elif subject == 'any':
            if temporal_type == 'random':
                return f"Summarize this randomly selected log entry from the fleet records."
            elif temporal_type == 'latest':
                return f"Summarize the most recent log entry from the fleet records."
            elif temporal_type == 'first':
                return f"Summarize the earliest log entry from the fleet records."
            else:
                return f"Summarize recent log entries from the fleet records."
        
        # Handle specific subjects (ships/characters)
        else:
            count_text = ""
            if result_count > 1:
                count_text = f" ({result_count} entries)"
            
            if temporal_type == 'random':
                return f"Summarize this randomly selected log regarding '{subject}'{count_text}."
            elif temporal_type == 'latest':
                return f"Summarize the most recent log regarding '{subject}'{count_text}."
            elif temporal_type == 'first':
                return f"Summarize the earliest log regarding '{subject}'{count_text}."
            else:
                return f"Summarize recent logs regarding '{subject}'{count_text}."

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

    def build_historical_summary_prompt(self, subject: str, results: List[Dict], temporal_type: str) -> str:
        """
        Builds a prompt for historical summary of multiple logs.
        Enhanced for multi-log queries to ensure chronological order and log source separation.
        """
        if not results:
            return f"I searched the mission logs but found no entries matching your query for '{subject}'."

        # Group logs by source/category for better organization
        logs_by_source = {}
        for result in results:
            # Try to extract source from categories or title
            source = self._extract_log_source(result)
            if source not in logs_by_source:
                logs_by_source[source] = []
            logs_by_source[source].append(result)

        # Format logs grouped by source, maintaining chronological order within each source
        formatted_sections = []
        
        for source, source_logs in logs_by_source.items():
            # Sort logs within each source chronologically (earliest to latest)
            sorted_logs = self._sort_logs_chronologically(source_logs)
            
            source_entries = []
            for i, result in enumerate(sorted_logs, 1):
                title = result.get('title', f'Log Entry {i}')
                content = result.get('raw_content', 'No content available.')
                
                # Extract date from title if available
                date_info = self._extract_date_info(title)
                date_str = f" - {date_info}" if date_info else ""
                
                source_entries.append(f"**{title}{date_str}**\n{content}")
            
            # Create a section for this source
            source_section = f"**=== {source.upper()} LOGS ===**\n\n" + "\n\n" + "-"*30 + "\n\n".join(source_entries)
            formatted_sections.append(source_section)

        # Join all sections with clear separators
        formatted_logs = "\n\n" + "="*60 + "\n\n".join(formatted_sections)
        
        # Determine the context based on temporal type and subject
        context_description = self._get_historical_context_description(subject, temporal_type, len(results))

        return f"""
Historical Log Summary:
You are a main computer aboard the starship USS Stardancer. {context_description} You have been provided with multiple log entries that should be summarized in a structured historical format.

INSTRUCTIONS FOR MULTI-LOG HISTORICAL SUMMARY:
- FORBIDDEN: Do not present the information like the raw laws with the "scene" structure intact.
- PRESENT logs in CHRONOLOGICAL ORDER from EARLIEST to LATEST within each source
- SEPARATE logs by source/origin (ship, mission, character, etc.)
- CREATE clear sections for each log source with "=== SOURCE LOGS ===" headers
- STRUCTURE: Provide a concise summary of key events for each log entry
- CHRONOLOGY: Maintain strict chronological progression from earliest events to most recent
- LOG SOURCE SEPARATION: Group related logs together by their source or origin
- ACCURACY: Only use information explicitly provided in the search results
- CRITICAL: DO NOT INVENT, FABRICATE, OR SPECULATE. If information is missing, state that you do not have that information
- CONSISTENCY: Use consistent formatting throughout all log entries
- BREVITY: Keep each log summary focused and concise while capturing key events and timeline
- IMPERATIVE: Each summary should be a short descriptive informational summary of the events of the logs you do not need scne tracking mearly a summary of the what has transpired.

MULTIPLE LOG ENTRIES TO SUMMARIZE (Organized by Source):
---
{formatted_logs}
---

Provide a structured historical summary with logs organized by source and presented in chronological order from earliest to latest events.
"""

    def build_log_list_prompt(self, subject: str, results: List[Dict]) -> str:
        """
        Builds a prompt for listing log titles.
        Returns a simple list of log titles without content summaries.
        """
        if not results:
            return f"I searched the mission logs but found no entries matching your query for '{subject}'."

        # Extract titles and format as a numbered list
        log_titles = []
        for i, result in enumerate(results, 1):
            title = result.get('title', f'Untitled Log {i}')
            
            # Extract date info if available
            date_info = self._extract_date_info(title)
            date_str = f" ({date_info})" if date_info else ""
            
            log_titles.append(f"{i}. {title}{date_str}")

        title_list = "\n".join(log_titles)
        total_count = len(results)
        
        return f"""
Log Database Query Results:
You are a main computer aboard the starship USS Stardancer. The user has requested a list of all logs related to '{subject}'. Present this as a clean, organized list.

INSTRUCTIONS:
- PRESENT the results as a numbered list
- INCLUDE the log title and date (if available) for each entry
- USE a professional, database-style format
- DO NOT include content summaries - titles only
- MAINTAIN chronological order
- PROVIDE a count of total entries found

QUERY RESULTS FOR '{subject.upper()}' LOGS:
Found {total_count} matching log entries:

{title_list}

---
Total: {total_count} log entries found in the database.
"""

    def _extract_date_info(self, title: str) -> str:
        """
        Extract date information from log titles.
        
        Args:
            title: The log title to extract date from
            
        Returns:
            Formatted date string or empty string if no date found
        """
        import re
        
        # Look for common date patterns in titles
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY
            r'\b(\d{4}-\d{1,2}-\d{1,2})\b',  # YYYY-MM-DD
            r'\b(\d{1,2}-\d{1,2}-\d{4})\b',  # MM-DD-YYYY
            r'stardate\s+(\d+\.?\d*)',       # Stardate format
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ""

    def _extract_log_source(self, log_result: Dict) -> str:
        """
        Extract the source/origin of a log entry for grouping purposes.
        
        Args:
            log_result: Dictionary containing log information
            
        Returns:
            String representing the log source (ship name, mission, character, etc.)
        """
        # Try to extract source from categories first
        categories = log_result.get('categories', [])
        if categories:
            for category in categories:
                category_lower = category.lower()
                # Look for ship names, mission types, or character-related categories
                if any(ship_term in category_lower for ship_term in ['stardancer', 'adagio', 'protector', 'manta', 'pilgrim']):
                    return category
                elif 'mission' in category_lower:
                    return 'Mission Logs'
                elif any(char_term in category_lower for char_term in ['captain', 'commander', 'crew', 'personnel']):
                    return 'Personnel Logs'
        
        # Try to extract from title
        title = log_result.get('title', '').lower()
        if 'stardancer' in title:
            return 'USS Stardancer'
        elif 'adagio' in title:
            return 'USS Adagio'
        elif 'protector' in title:
            return 'USS Protector'
        elif 'mission' in title:
            return 'Mission Logs'
        elif any(rank in title for rank in ['captain', 'commander', 'lieutenant']):
            return 'Personnel Logs'
        
        # Default fallback
        return 'General Logs'

    def _sort_logs_chronologically(self, logs: List[Dict]) -> List[Dict]:
        """
        Sort logs chronologically from earliest to latest.
        
        Args:
            logs: List of log dictionaries to sort
            
        Returns:
            List of logs sorted chronologically (earliest to latest)
        """
        import re
        from datetime import datetime
        
        def extract_sortable_date(log):
            """Extract a date that can be used for sorting"""
            title = log.get('title', '')
            
            # Look for stardate first (most common in Star Trek logs)
            stardate_match = re.search(r'stardate\s+(\d+\.?\d*)', title, re.IGNORECASE)
            if stardate_match:
                return float(stardate_match.group(1))
            
            # Look for standard date formats
            date_patterns = [
                (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', '%Y-%m-%d'),  # YYYY-MM-DD
                (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', '%m/%d/%Y'),   # MM/DD/YYYY
                (r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b', '%m-%d-%Y'),   # MM-DD-YYYY
            ]
            
            for pattern, date_format in date_patterns:
                match = re.search(pattern, title)
                if match:
                    try:
                        if date_format == '%Y-%m-%d':
                            date_str = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                        else:
                            date_str = match.group(0)
                        date_obj = datetime.strptime(date_str, date_format)
                        # Convert to a sortable number (days since epoch)
                        return date_obj.timestamp()
                    except ValueError:
                        continue
            
            # If no date found, try to extract ID or use order in results
            log_id = log.get('id')
            if log_id:
                # Try to extract numeric part of ID for sorting
                id_match = re.search(r'(\d+)', str(log_id))
                if id_match:
                    return float(id_match.group(1))
            
            # Final fallback - return 0 to maintain original order
            return 0
        
        # Sort logs by extracted date
        try:
            sorted_logs = sorted(logs, key=extract_sortable_date)
            return sorted_logs
        except Exception as e:
            print(f"   ⚠️  Error sorting logs chronologically: {e}")
            # Return original order if sorting fails
            return logs

    def _get_historical_context_description(self, subject: str, temporal_type: str, result_count: int) -> str:
        """
        Generate appropriate context description for historical summaries.
        
        Args:
            subject: The subject of the log query
            temporal_type: The temporal modifier
            result_count: Number of results found
            
        Returns:
            Context description for historical summary prompt
        """
        if subject == 'mission':
            return f"Provide a historical summary of {result_count} mission records from the fleet database."
        elif subject == 'any':
            return f"Provide a historical summary of {result_count} log entries from the fleet database."
        else:
            if temporal_type == 'random':
                return f"Provide a historical summary of {result_count} randomly selected logs regarding '{subject}'."
            elif temporal_type == 'latest':
                return f"Provide a historical summary of the {result_count} most recent logs regarding '{subject}'."
            elif temporal_type == 'first':
                return f"Provide a historical summary of the {result_count} earliest logs regarding '{subject}'."
            else:
                return f"Provide a historical summary of {result_count} logs regarding '{subject}'."

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