"""
Structured Query Detector
=========================

This module contains the logic for detecting specific, structured query patterns
that can be handled directly without LLM intervention. It is a key component
of the new agentic architecture, allowing for fast-pathing of explicit user commands.
"""

import re
from typing import Dict, Optional, Any
from handlers.ai_knowledge.log_patterns import FLEET_SHIP_NAMES

class StructuredQueryDetector:
    """
    Detects specific, structured query patterns in a user's message.
    """
    def detect_query(self, user_message: str) -> Dict[str, Any]:
        """
        Analyzes the user message to find a matching structured query pattern.

        Args:
            user_message: The raw message from the user.

        Returns:
            A dictionary containing the detected query details, or a 'general'
            type if no specific pattern is matched.
        """
        # The order of these checks is important, from most specific to most general.
        
        # 1. Log search: "logs for <ship/character> [latest|first|recent]" (most specific keywords)
        log_search = self._detect_log_search(user_message)
        if log_search:
            return log_search

        # 2. "Who is <character>" - specific character queries
        who_is_query = self._detect_who_is_query(user_message)
        if who_is_query:
            return who_is_query

        # 3. "Tell me about <term>"
        tell_me_about = self._detect_tell_me_about(user_message)
        if tell_me_about:
            return tell_me_about
            
        # 4. Explicit search: "search for 'term' in 'category'"
        explicit_search = self._detect_explicit_search(user_message)
        if explicit_search:
            return explicit_search

        # 5. Typed search: "ship <name>", "character <name>", etc.
        typed_search = self._detect_typed_search(user_message)
        if typed_search:
            return typed_search

        # If no specific pattern is found, it's a general query for the LLM.
        return {'type': 'general', 'query': user_message}

    def _detect_who_is_query(self, user_message: str) -> Optional[Dict[str, str]]:
        """
        Detects "who is" queries which are typically character queries.
        """
        pattern = re.compile(r'who\s+is\s+([A-Za-z0-9\s\'-]+)', re.IGNORECASE)
        match = pattern.search(user_message)
        if not match:
            return None

        term = match.group(1).strip()
        print(f"   👤 DETECTOR: 'Who is' query detected for '{term}'. Routing to character search.")
        return {'type': 'character', 'term': term}

    def _detect_tell_me_about(self, user_message: str) -> Optional[Dict[str, str]]:
        """
        Detects "tell me about" queries and attempts to classify them.
        If the subject is clearly a ship or character, it's typed.
        Otherwise, it's a general query for the LogicEngine to disambiguate.
        """
        pattern = re.compile(r'tell me about\s+(?:the\s+)?([A-Za-z0-9\s\'-]+)', re.IGNORECASE)
        match = pattern.search(user_message)
        if not match:
            return None

        term = match.group(1).strip()
        term_lower = term.lower()

        # Check for specific entity types in the term itself
        if 'ship' in term_lower or any(ship.lower() in term_lower for ship in FLEET_SHIP_NAMES):
            return {'type': 'ship', 'term': term}
        
        # Simple check for character indicators in the message
        character_indicators = ['who is', 'character']
        if any(indicator in user_message.lower() for indicator in character_indicators):
             return {'type': 'character', 'term': term}

        # Enhanced: Check if the term looks like a character name
        if self._looks_like_character_name(term):
            print(f"   👤 DETECTOR: Term '{term}' appears to be a character name. Routing to character search.")
            return {'type': 'character', 'term': term}

        # For ambiguous "tell me about" queries, let the LogicEngine decide.
        # We pass the full user message to give the LLM maximum context.
        print(f"   👁️‍🗨️ DETECTOR: Ambiguous 'tell me about' for '{term}'. Routing to LogicEngine.")
        return {'type': 'general', 'query': user_message}

    def _looks_like_character_name(self, term: str) -> bool:
        """
        Determine if a term looks like a character name based on patterns.
        """
        # Split into words
        words = term.strip().split()
        term_lower = term.lower()
        
        # Exclude known location/place patterns that might look like names
        location_indicators = [
            # Planets and systems
            'planet', 'system', 'sector', 'quadrant', 'nebula', 'station', 'base', 'outpost',
            'colony', 'world', 'moon', 'asteroid', 'belt', 'cluster', 'expanse',
            # Common planet name patterns
            'prime', 'major', 'minor', 'alpha', 'beta', 'gamma', 'delta', 'epsilon',
            # Star Trek specific locations
            'deep space', 'starbase', 'space dock', 'dry dock', 'shipyard',
            # Generic location words
            'city', 'town', 'capital', 'region', 'territory', 'empire', 'republic',
            'federation', 'union', 'alliance', 'dominion', 'hegemony'
        ]
        
        # Check if the term contains location indicators
        if any(indicator in term_lower for indicator in location_indicators):
            return False
        
        # Known planet name patterns (common in Star Trek)
        # These are specific combinations that indicate planets, not character names
        planet_name_patterns = [
            # Common planet naming patterns - these are geographical/descriptive terms
            ('magna', 'roma'), ('terra', 'nova'), ('alpha', 'centauri'), 
            ('beta', 'rigel'), ('gamma', 'hydra'), ('delta', 'vega'),
            # Other common planet patterns
            ('new', 'earth'), ('old', 'earth'), ('neo', 'tokyo'),
            ('prime', 'world'), ('major', 'world'), ('minor', 'world')
        ]
        
        if len(words) == 2:
            word_pair = (words[0].lower(), words[1].lower())
            if word_pair in planet_name_patterns:
                return False
        
        # Single word that's capitalized (like "Jackson", "Riens", "Sif")
        if len(words) == 1:
            word = words[0]
            # Must be capitalized and not a common word or location
            excluded_single_words = [
                'ship', 'vessel', 'station', 'base', 'planet', 'system', 'sector', 
                'the', 'and', 'for', 'with', 'earth', 'mars', 'vulcan', 'andoria',
                'bajor', 'cardassia', 'romulus', 'remus', 'qonos', 'kronos'
            ]
            if (word[0].isupper() and 
                len(word) >= 3 and 
                word.lower() not in excluded_single_words):
                return True
        
        # Two words that look like "First Last" (like "Jackson Riens", "Marcus Blaine")
        elif len(words) == 2:
            first, last = words
            
            # Exclude common location patterns
            location_pairs = [
                ('deep', 'space'), ('dry', 'dock'), ('space', 'dock'), ('star', 'base'),
                ('terra', 'nova'), ('alpha', 'centauri'), ('beta', 'quadrant'),
                ('gamma', 'quadrant'), ('delta', 'quadrant')
            ]
            
            if (first.lower(), last.lower()) in location_pairs:
                return False
            
            # Standard character name pattern
            if (first[0].isupper() and last[0].isupper() and 
                len(first) >= 2 and len(last) >= 2):
                return True
        
        # Three words that might be "Title First Last" (like "Captain Marcus Blaine", "Doctor T'Lena")
        elif len(words) == 3:
            first, second, third = words
            titles = ['captain', 'commander', 'lieutenant', 'doctor', 'ensign', 'chief', 'admiral', 'dr']
            if (first.lower() in titles and 
                second[0].isupper() and third[0].isupper() and
                len(second) >= 2 and len(third) >= 2):
                return True
        
        # Four or more words that might be long character names (like "Marcus Antonius Telemachus Aquila")
        elif len(words) >= 4:
            # Check if all words are capitalized and look like proper names
            # Exclude the first word if it's a title
            start_index = 0
            titles = ['captain', 'commander', 'lieutenant', 'doctor', 'ensign', 'chief', 'admiral', 'dr']
            if words[0].lower() in titles:
                start_index = 1
            
            # Check if remaining words look like proper names
            name_words = words[start_index:]
            if len(name_words) >= 2:  # Need at least 2 name words
                all_proper_names = all(
                    word[0].isupper() and len(word) >= 2 and word.isalpha()
                    for word in name_words
                )
                if all_proper_names:
                    print(f"   📝 DETECTOR: Long name detected: '{term}' ({len(name_words)} name words)")
                    return True
        
        return False

    def _detect_explicit_search(self, user_message: str) -> Optional[Dict[str, str]]:
        """
        Detects the pattern: search for "term" in "category"
        """
        pattern = re.compile(r'search for\s+"([^"]+)"\s+in\s+"([^"]+)"', re.IGNORECASE)
        match = pattern.search(user_message)
        if match:
            term, category = match.groups()
            return {'type': 'explicit', 'term': term.strip(), 'category': category.strip()}
        return None

    def _detect_log_search(self, user_message: str) -> Optional[Dict[str, Any]]:
        """
        Detects log-related queries for ships or characters.
        Enhanced to handle multiple temporal patterns and general log queries.
        
        Patterns supported:
        1. logs for <subject> [modifier]
        2. [summarize/tell me about] [the] <modifier> <subject> log[s]
        3. [show me/give me] [the] <modifier> [number] <subject> log[s]
        4. [tell me about/summarize] [a] <modifier> <subject> log[s]
        5. [tell me about/summarize] [a] mission[s] (random from all logs)
        6. random log queries
        7. multi-log queries (summarize the last X logs, tell me about the recent Y logs)
        """
        
        # NEW Pattern: Multi-log queries - "summarize the last X logs", "tell me about the recent Y logs"
        # This pattern specifically catches numeric multi-log requests and forces historical summary
        multi_log_pattern = re.compile(r'(?:summarize|tell me about|show me|give me)\s+(?:the\s+)?(last|latest|recent|first)(?:\s+(\d+))?\s+logs?\b', re.IGNORECASE)
        multi_log_match = multi_log_pattern.search(user_message)
        if multi_log_match:
            modifier, count = multi_log_match.groups()
            modifier = self._normalize_temporal_modifier(modifier)
            
            # Default to 3 logs if no specific count provided, but mark as multi-log
            count_value = int(count) if count else 3
            
            print(f"   🔢 MULTI-LOG QUERY DETECTED: modifier='{modifier}', count={count_value}")
            
            return {
                'type': 'logs',
                'subject': 'any',  # Multi-log queries search across all logs
                'modifier': modifier,
                'count': count_value,
                'is_general_log': True,
                'force_historical_summary': True  # NEW: Force historical summary format
            }
        
        # Pattern 1: "logs for <subject> [modifier]"
        pattern1 = re.compile(r'logs? for\s+([A-Za-z0-9\s\'-]+?)(?:\s+(latest|last|first|recent|most recent|random))?$', re.IGNORECASE)
        match1 = pattern1.search(user_message)
        if match1:
            subject, modifier = match1.groups()
            subject = subject.strip()
            modifier = self._normalize_temporal_modifier(modifier) if modifier else 'recent'
            
            return {
                'type': 'logs',
                'subject': subject,
                'modifier': modifier
            }

        # Pattern 2 & 3: Enhanced to handle more temporal modifiers and numeric patterns
        # "tell me about the <modifier> <subject> log" or "summarize the <modifier> <subject> log"
        # "show me the latest 5 <subject> logs" or "give me the first 3 <subject> logs"
        pattern2_3 = re.compile(r'(?:tell me about|summarize|show me|give me)\s+(?:the\s+)?(latest|last|first|recent|most recent|random)(?:\s+(\d+))?\s+([A-Za-z0-9\s\'-]+?)\s+logs?\b', re.IGNORECASE)
        match2_3 = pattern2_3.search(user_message)
        if match2_3:
            modifier, count, subject = match2_3.groups()
            modifier = self._normalize_temporal_modifier(modifier)
            subject = subject.strip()
            
            result = {
                'type': 'logs',
                'subject': subject,
                'modifier': modifier
            }
            
            # Add count if specified
            if count:
                result['count'] = int(count)
                # If count > 1, force historical summary
                if int(count) > 1:
                    result['force_historical_summary'] = True
            
            return result

        # Pattern 4: "tell me about a random <subject> log" or "summarize a recent mission"
        pattern4 = re.compile(r'(?:tell me about|summarize)\s+a\s+(random|recent|latest|first)\s+([A-Za-z0-9\s\'-]+?)\s+logs?\b', re.IGNORECASE)
        match4 = pattern4.search(user_message)
        if match4:
            modifier, subject = match4.groups()
            modifier = self._normalize_temporal_modifier(modifier)
            
            return {
                'type': 'logs',
                'subject': subject.strip(),
                'modifier': modifier
            }

        # Pattern 5: General mission queries without specific ship - "tell me about a mission", "summarize recent missions"
        pattern5 = re.compile(r'(?:tell me about|summarize)\s+(?:a\s+|(?:the\s+)?(?:recent|latest|random)\s+)?missions?\b', re.IGNORECASE)
        match5 = pattern5.search(user_message)
        if match5:
            # Extract temporal modifier if present
            modifier_match = re.search(r'\b(recent|latest|random|first)\b', user_message, re.IGNORECASE)
            modifier = self._normalize_temporal_modifier(modifier_match.group(1)) if modifier_match else 'random'
            
            return {
                'type': 'logs',
                'subject': 'mission',  # Special subject for all missions
                'modifier': modifier,
                'is_general_mission': True
            }

        # Pattern 6: Simple random/recent log queries - "random log please", "show me recent logs", "give me the first log"
        pattern6 = re.compile(r'(?:show me|give me|random)\s+(?:(?:the\s+)?(?:recent|latest|first|random)\s+)?logs?\b(?:\s+please)?', re.IGNORECASE)
        match6 = pattern6.search(user_message)
        if match6:
            # Extract temporal modifier if present
            modifier_match = re.search(r'\b(recent|latest|first|random)\b', user_message, re.IGNORECASE)
            modifier = self._normalize_temporal_modifier(modifier_match.group(1)) if modifier_match else 'random'
            
            return {
                'type': 'logs',
                'subject': 'any',  # Special subject for any logs
                'modifier': modifier,
                'is_general_log': True
            }

        # Pattern 7: "summarize recent missions" - general mission summaries
        pattern7 = re.compile(r'summarize\s+(?:(?:recent|latest|random)\s+)?missions?\b', re.IGNORECASE)
        match7 = pattern7.search(user_message)
        if match7:
            modifier_match = re.search(r'\b(recent|latest|random)\b', user_message, re.IGNORECASE)
            modifier = self._normalize_temporal_modifier(modifier_match.group(1)) if modifier_match else 'recent'
            
            return {
                'type': 'logs',
                'subject': 'mission',
                'modifier': modifier,
                'is_general_mission': True
            }

        # Pattern 8: "give me a random mission log" - specific pattern for mission log requests
        pattern8 = re.compile(r'(?:give me|show me)\s+a\s+(random|recent|latest|first)\s+mission\s+logs?\b', re.IGNORECASE)
        match8 = pattern8.search(user_message)
        if match8:
            modifier = self._normalize_temporal_modifier(match8.group(1))
            
            return {
                'type': 'logs',
                'subject': 'mission',
                'modifier': modifier,
                'is_general_mission': True
            }

        # Pattern 9: "show me a list of all X logs" - list queries for log titles
        pattern9 = re.compile(r'(?:show me|give me)\s+a\s+list\s+of\s+(?:all\s+)?([A-Za-z0-9\s\'-]+?)\s+logs?\b', re.IGNORECASE)
        match9 = pattern9.search(user_message)
        if match9:
            subject = match9.group(1).strip()
            
            return {
                'type': 'logs',
                'subject': subject,
                'modifier': 'list',
                'is_list_query': True
            }

        return None

    def _normalize_temporal_modifier(self, modifier: str) -> str:
        """
        Normalize temporal modifiers to standard forms.
        
        Args:
            modifier: Raw temporal modifier from regex
            
        Returns:
            Normalized modifier: 'latest', 'first', 'recent', 'random'
        """
        if not modifier:
            return 'recent'
        
        modifier = modifier.lower().strip()
        
        # Normalize variations
        if modifier in ['last', 'latest', 'most recent']:
            return 'latest'
        elif modifier == 'first':
            return 'first'
        elif modifier == 'recent':
            return 'recent'
        elif modifier == 'random':
            return 'random'
        else:
            return 'recent'  # Default fallback

    def _detect_typed_search(self, user_message: str) -> Optional[Dict[str, str]]:
        """
        Detects simple typed searches like "ship <name>".
        """
        typed_patterns = {
            'ship': re.compile(r'^ship\s+([A-Za-z0-9\s-]+)$', re.IGNORECASE),
            'character': re.compile(r'^character\s+([A-Za-z0-9\s\'-]+)$', re.IGNORECASE),
            'species': re.compile(r'^species\s+([A-Za-z\s-]+)$', re.IGNORECASE),
            'planet': re.compile(r'^planet\s+([A-Za-z0-9\s-]+)$', re.IGNORECASE),
        }

        for query_type, pattern in typed_patterns.items():
            match = pattern.match(user_message)
            if match:
                term = match.group(1).strip()
                return {'type': query_type, 'term': term}
        return None 