"""
Structured Content Retriever
============================

This module is the data-fetching component of the new agentic architecture.
It takes a structured query object from the StructuredQueryDetector and
retrieves the relevant content from the database, orchestrating with the
LLMInterface when necessary for general queries.
"""

from typing import Dict, Any, List
from handlers.ai_knowledge.database_controller import get_db_controller
from handlers.ai_logic.logic_engine import get_logic_engine

class StructuredContentRetriever:
    """
    Retrieves content from the database based on a structured query object.
    """
    def __init__(self):
        self.db_controller = get_db_controller()
        self.logic_engine = get_logic_engine()
        # Set up database controller dependency for smart failover
        self.logic_engine.set_database_controller(self.db_controller)
        print("✓ StructuredContentRetriever initialized with smart failover")

    def get_content(self, structured_query: Dict[str, Any]) -> List[Dict]:
        """
        Main method to fetch content based on the structured query.

        Args:
            structured_query: A dictionary from StructuredQueryDetector.

        Returns:
            A list of matching records from the database.
        """
        query_type = structured_query.get('type')
        print(f"   📚 Structured Content Retriever: Handling type '{query_type}'")

        # Use the category if it was pre-determined by the LogicEngine
        if 'category' in structured_query:
            category = structured_query['category']
            subject = structured_query.get('subject', structured_query.get('query'))
            print(f"   - Using pre-determined category: '{category}' for subject: '{subject}'")

            search_categories = None
            limit = 5  # Default limit
            category_lower = category.lower()

            if 'ship' in category_lower:
                print(f"   - Wildcarding category '{category}' as a ship...")
                search_categories = self.db_controller.get_ship_categories()
                limit = 1
            elif 'character' in category_lower or 'npc' in category_lower:
                print(f"   - Wildcarding category '{category}' as a character...")
                search_categories = self.db_controller.get_character_categories()
                # Use enhanced character search for character queries
                return self._handle_enhanced_character_search(subject, search_categories)
            elif 'log' in category_lower:
                print(f"   - Wildcarding category '{category}' as a log...")
                search_categories = self.db_controller.get_log_categories()
            elif category_lower == 'general':
                # For general category, use two-step search: titles first, then deep content
                print(f"   - General category detected - using two-step search approach")
                
                # Step 1: Search titles only
                title_results = self.db_controller.search_titles_only(query=subject, categories=None, limit=5)
                
                if title_results:
                    print(f"   ✅ Found {len(title_results)} results in title search")
                    return title_results
                
                # Step 2: If no title matches, do deep content search
                print(f"   📖 No title matches found, performing deep content search...")
                content_results = self.db_controller.search_content_deep(query=subject, categories=None, limit=100)
                
                print(f"   ✅ Deep content search returned {len(content_results)} results")
                return content_results
            else:
                # If no keyword matches, search in the specific category returned
                search_categories = [category]

            return self.db_controller.search(query=subject, categories=search_categories, limit=limit)

        if query_type == 'tell_me_about':
            subject = structured_query.get('subject')
            print(f"   - Handling 'tell_me_about' for subject: '{subject}'")
            # Search across all categories for the best match.
            return self.db_controller.search(query=subject, categories=None, limit=5)
        elif query_type == 'explicit':
            return self._handle_explicit_search(structured_query)
        elif query_type == 'logs':
            return self._handle_log_search(structured_query)
        elif query_type in ['ship', 'character', 'species', 'planet']:
            return self._handle_typed_search(structured_query)
        elif query_type == 'general':
            return self._handle_general_query(structured_query)
        else:
            print(f"   ⚠️  Unknown query type in content retriever: {query_type}")
            return []

    def _handle_explicit_search(self, query: Dict[str, str]) -> List[Dict]:
        """Handles: search for "term" in "category" """
        term = query.get('term')
        category = query.get('category')
        return self.db_controller.search(query=term, categories=[category], limit=10)

    def _handle_log_search(self, query: Dict[str, Any]) -> List[Dict]:
        """Handles: logs for <ship/character> [latest|first|recent]"""
        subject = query.get('subject')
        modifier = query.get('modifier')
        
        order_by_map = {
            'latest': 'chronological',
            'first': 'id_asc',
            'recent': 'chronological'
        }
        limit_map = {
            'latest': 1,
            'first': 1,
            'recent': 3
        }

        order_by = order_by_map.get(modifier, 'chronological')
        limit = limit_map.get(modifier, 3)
        
        # We assume 'Logs' is a valid category. This could be made more robust.
        log_categories = self.db_controller.get_log_categories()
        
        return self.db_controller.search(
            query=subject, 
            categories=log_categories, 
            limit=limit, 
            order_by=order_by
        )

    def _handle_typed_search(self, query: Dict[str, str]) -> List[Dict]:
        """Handles: ship <name>, character <name>, etc."""
        term = query.get('term')
        query_type = query.get('type')

        category_map = {
            'ship': self.db_controller.get_ship_categories,
            'character': self.db_controller.get_character_categories,
            'species': lambda: ['Species', 'Race'], # Assuming these categories exist
            'planet': lambda: ['Planet'] # Assuming this category exists
        }

        # Get the categories associated with the query type
        category_func = category_map.get(query_type)
        categories = category_func() if category_func else [query_type.title()]

        # Enhanced character search with interaction analysis
        if query_type == 'character':
            return self._handle_enhanced_character_search(term, categories)
        
        return self.db_controller.search(query=term, categories=categories, limit=1)
    
    def _handle_enhanced_character_search(self, character_name: str, character_categories: List[str]) -> List[Dict]:
        """
        Enhanced character search that finds the primary character and related characters/interactions.
        Also handles disambiguation when multiple characters match a partial name.
        
        Args:
            character_name: Name of the character to search for
            character_categories: Character-related categories to search in
            
        Returns:
            List of results with primary character first, followed by related characters and interactions
            OR a special disambiguation result if multiple partial matches are found
        """
        print(f"   👥 Enhanced character search for: '{character_name}'")
        
        # Step 1: Find the primary character in character categories
        primary_results = self.db_controller.search(
            query=character_name, 
            categories=character_categories, 
            limit=10  # Increased limit to catch more potential matches
        )
        
        print(f"   📋 Found {len(primary_results)} primary character results")
        
        # Step 2: Check for disambiguation needs
        disambiguation_needed = self._check_disambiguation_needed(character_name, primary_results)
        
        if disambiguation_needed:
            print(f"   🔀 DISAMBIGUATION NEEDED: Multiple characters match '{character_name}'")
            # Filter results to only include actual character entries
            character_matches = self._filter_character_results(primary_results)
            # Return special disambiguation result
            return [{'type': 'disambiguation', 'search_term': character_name, 'matches': character_matches}]
        
        # Step 3: If no disambiguation needed, proceed with normal character search
        # Take only the top 3 primary results for the normal flow
        primary_results = primary_results[:3]
        
        # Step 4: Search content for character interactions and mentions
        interaction_results = self._search_character_interactions(character_name)
        
        print(f"   🤝 Found {len(interaction_results)} interaction results")
        
        # Step 5: Extract related characters from interaction content
        related_characters = self._extract_related_characters_from_content(
            character_name, 
            interaction_results
        )
        
        print(f"   👥 Identified {len(related_characters)} related characters")
        
        # Step 6: Search for the related characters in character categories
        related_character_results = []
        for related_char in related_characters[:5]:  # Limit to top 5 related characters
            related_results = self.db_controller.search(
                query=related_char,
                categories=character_categories,
                limit=1
            )
            if related_results:
                related_character_results.extend(related_results)
        
        print(f"   📚 Found {len(related_character_results)} related character profiles")
        
        # Step 7: Combine results - primary character first, then related characters
        all_results = primary_results + related_character_results
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_results = []
        for result in all_results:
            result_id = result.get('id')
            if result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)
        
        print(f"   ✅ Returning {len(unique_results)} total character-related results")
        return unique_results
    
    def _check_disambiguation_needed(self, search_term: str, results: List[Dict]) -> bool:
        """
        Check if disambiguation is needed based on search results.
        
        Args:
            search_term: The original search term
            results: Search results to analyze
            
        Returns:
            True if disambiguation is needed, False otherwise
        """
        if len(results) < 2:
            return False
        
        search_lower = search_term.lower().strip()
        search_words = search_lower.split()
        
        # Check if the search term is a partial name (short name that could match multiple characters)
        is_partial_name = (
            len(search_words) == 1 and  # Single word search
            len(search_lower) >= 3 and   # At least 3 characters
            not any(title in search_lower for title in ['captain', 'commander', 'lieutenant', 'doctor', 'ensign'])  # No rank
        )
        
        if not is_partial_name:
            return False
        
        # Count how many results have the search term as a partial match in their title
        partial_matches = []
        exact_matches = []
        
        for result in results:
            title = result.get('title', '').lower()
            title_words = title.split()
            
            # Check for exact match first
            if search_lower == title.lower():
                exact_matches.append(result)
            # Check for partial matches (search term appears in any word of the title)
            elif any(search_lower in word for word in title_words):
                partial_matches.append(result)
        
        # If we have one exact match, no disambiguation needed
        if len(exact_matches) == 1:
            print(f"   ✅ Exact match found for '{search_term}': {exact_matches[0].get('title')}")
            return False
        
        # If we have multiple partial matches and no exact match, disambiguation needed
        if len(partial_matches) >= 2:
            print(f"   🔀 Multiple partial matches found for '{search_term}': {[r.get('title') for r in partial_matches]}")
            return True
        
        return False
    
    def _filter_character_results(self, results: List[Dict]) -> List[Dict]:
        """
        Filter results to only include actual character entries, excluding locations, ships, etc.
        
        Args:
            results: List of search results to filter
            
        Returns:
            Filtered list containing only character-related results
        """
        character_results = []
        
        for result in results:
            categories = result.get('categories', [])
            categories_lower = [cat.lower() for cat in categories]
            
            # Check if this result has character-related categories
            character_indicators = ['characters', 'npcs', 'personnel', 'crew']
            is_character = any(
                any(indicator in category for indicator in character_indicators) 
                for category in categories_lower
            )
            
            # Exclude obvious non-character categories
            non_character_indicators = ['locations', 'planets', 'systems', 'ships', 'starships', 'stations', 'bases']
            is_non_character = any(
                any(indicator in category for indicator in non_character_indicators) 
                for category in categories_lower
            )
            
            if is_character and not is_non_character:
                character_results.append(result)
                print(f"   ✅ Character result included: {result.get('title')} - {categories}")
            else:
                print(f"   ❌ Non-character result excluded: {result.get('title')} - {categories}")
        
        return character_results
    
    def _search_character_interactions(self, character_name: str) -> List[Dict]:
        """
        Search for content that mentions the character to find interactions.
        
        Args:
            character_name: Name of the character to search for
            
        Returns:
            List of content results that mention the character
        """
        # Search broadly in content for character mentions
        # Use content-deep search to get more comprehensive results
        interaction_results = self.db_controller.search_content_deep(
            query=character_name,
            categories=None,  # Search all categories for interactions
            limit=50  # Get more results to analyze for character mentions
        )
        
        # Filter results to focus on those likely to contain character interactions
        filtered_results = []
        for result in interaction_results:
            content = result.get('raw_content', '').lower()
            title = result.get('title', '').lower()
            char_lower = character_name.lower()
            
            # Skip if this is the character's own profile page
            if char_lower in title and len(title.split()) <= 3:
                continue
                
            # Look for interaction indicators in content
            interaction_indicators = [
                'spoke to', 'talked to', 'met with', 'encountered', 'worked with',
                'accompanied', 'joined', 'helped', 'assisted', 'collaborated',
                'discussed', 'conversation', 'dialogue', 'interaction', 'meeting'
            ]
            
            if any(indicator in content for indicator in interaction_indicators):
                filtered_results.append(result)
            elif len([word for word in content.split() if word == char_lower]) >= 2:
                # Multiple mentions of the character suggest interaction content
                filtered_results.append(result)
        
        return filtered_results[:20]  # Return top 20 interaction results
    
    def _extract_related_characters_from_content(self, primary_character: str, content_results: List[Dict]) -> List[str]:
        """
        Extract character names that appear to be related to the primary character.
        
        Args:
            primary_character: The main character we're searching for
            content_results: List of content that mentions the character
            
        Returns:
            List of related character names
        """
        import re
        from collections import Counter
        
        related_characters = Counter()
        primary_lower = primary_character.lower()
        
        # Common character name patterns
        character_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # Capitalized names
            r'(?:Captain|Commander|Lieutenant|Doctor|Ensign|Chief)\s+([A-Z][a-z]+)',  # Titled names
            r'\[([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\]',  # Bracket format names
        ]
        
        # Words to exclude from character names
        exclude_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
            'after', 'above', 'below', 'between', 'among', 'ship', 'starship',
            'bridge', 'deck', 'room', 'bay', 'quarters', 'station', 'computer',
            'system', 'data', 'report', 'log', 'entry', 'mission', 'crew',
            'officer', 'personnel', 'starfleet', 'federation', 'uss', 'enterprise'
        }
        
        for result in content_results:
            content = result.get('raw_content', '')
            
            # Extract potential character names using patterns
            for pattern in character_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Clean up the match
                    name = match.strip()
                    name_lower = name.lower()
                    
                    # Skip if it's the primary character or excluded words
                    if (name_lower == primary_lower or 
                        name_lower in exclude_words or 
                        len(name) < 2 or
                        not name[0].isupper()):
                        continue
                    
                    # Skip single letters or very short names
                    if len(name.replace(' ', '')) < 3:
                        continue
                    
                    # Count frequency of this character name
                    related_characters[name] += 1
        
        # Return the most frequently mentioned related characters
        # Filter to those mentioned at least twice for relevance
        frequent_characters = [
            name for name, count in related_characters.most_common(10)
            if count >= 2
        ]
        
        return frequent_characters

    def _handle_general_query(self, query: Dict[str, Any]) -> List[Dict]:
        """
        Handles a general query when the category has not been pre-determined.
        Uses smart failover to verify category results before falling back to general search.
        """
        user_query = query.get('query')
        print(f"   🧠 SMART LOGIC: Processing general query: '{user_query}'")
        
        # Get all available categories for the LLM to choose from
        all_categories = self.db_controller.get_all_categories()
        
        # Use the enhanced LLM logic with smart failover
        decision = self.logic_engine.determine_query_category_with_failover(user_query, all_categories)
        
        chosen_category = decision['category']
        original_category = decision['original_category']
        failover_used = decision['failover_used']
        reason = decision['reason']
        
        if failover_used:
            print(f"   🔄 FAILOVER: '{original_category}' → 'General' ({reason})")
        else:
            print(f"   ✅ CATEGORY: '{chosen_category}' ({reason})")
        
        # Execute search based on final category
        if chosen_category.lower() == 'general':
            # Use two-step general search approach
            print(f"   🔍 Executing general search with two-step approach")
            
            # Step 1: Try title-only search first
            title_results = self.db_controller.search_titles_only(
                query=user_query, 
                categories=None, 
                limit=5
            )
            
            if title_results and len(title_results) > 0:
                print(f"   🎯 Title search successful: {len(title_results)} results")
                return title_results
            
            # Step 2: Fall back to deep content search
            print(f"   📚 Title search failed, trying deep content search")
            content_results = self.db_controller.search_content_deep(
                query=user_query, 
                categories=None, 
                limit=10
            )
            
            if content_results and len(content_results) > 0:
                print(f"   📖 Deep content search successful: {len(content_results)} results")
                return content_results
            
            print(f"   ❌ No results found in general search")
            return []
        else:
            # Search within the verified specific category
            print(f"   🎯 Executing category-specific search in '{chosen_category}'")
            return self.db_controller.search_with_category_matching(
                query=user_query, 
                target_category=chosen_category, 
                limit=10
            )

# Singleton instance
_content_retriever = None

def get_structured_content_retriever():
    """
    Provides a global singleton instance of the StructuredContentRetriever.
    """
    global _content_retriever
    if _content_retriever is None:
        _content_retriever = StructuredContentRetriever()
    return _content_retriever 