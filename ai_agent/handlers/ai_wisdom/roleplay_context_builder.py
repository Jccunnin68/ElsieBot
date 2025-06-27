"""
Roleplay Context Builder - LLM-Powered Context Generation
=========================================================

This module builds roleplay context prompts using the content retriever and LLM processing.
"""

from typing import List, Dict, Any, Optional
from ..service_container import get_content_filter_service


class RoleplayContextBuilder:
    """
    Service class for building roleplay context prompts.
    
    This class provides a clean API for roleplay context generation while maintaining
    proper encapsulation and state management.
    """
    
    def __init__(self):
        """Initialize the roleplay context builder."""
        pass
    
    def build_context(self, user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
        """
        Build comprehensive roleplay context using the content retriever and LLM processing.
        
        Args:
            user_message: The user's message
            conversation_history: Recent conversation history
            character_context: Optional character context information
            
        Returns:
            Built roleplay context prompt
        """
        return build_roleplay_context(user_message, conversation_history, character_context)

    def build_context_for_strategy(self, strategy: Dict[str, Any], user_message: str) -> str:
        """
        Build roleplay context based on a strategy decision from the attention engine.
        
        This method integrates strategy decisions with roleplay state and conversation context
        to create rich, contextually-aware prompts for the AI engine.
        
        Args:
            strategy: Strategy dictionary from attention engine containing:
                - approach: The response approach (e.g., 'roleplay_active')
                - reasoning: Why this approach was chosen
                - suggested_tone: Emotional tone for the response
                - Additional strategy-specific fields
            user_message: The user's message
            
        Returns:
            Built roleplay context prompt with strategy integration
        """
        # Input validation - check strategy first
        if not isinstance(strategy, dict) or strategy is None:
            print(f"      ❌ Invalid strategy type: {type(strategy)}")
            return self._build_strategy_fallback_context({'approach': 'roleplay_active'}, user_message)
        
        print(f"      🎭 ROLEPLAY CONTEXT BUILDER: Processing strategy '{strategy.get('approach')}'")
        
        
        if not user_message or not isinstance(user_message, str):
            print(f"      ❌ Invalid user_message: {user_message}")
            user_message = "No message provided"
        
        try:
            # Import roleplay state manager for rich context
            from ..service_container import get_roleplay_state
            rp_state = get_roleplay_state()
            
            # Import character tracking for character information
            from ..service_container import get_character_tracking_service
            char_service = get_character_tracking_service()
            
            # Extract strategy information with defaults
            approach = strategy.get('approach', 'roleplay_active')
            reasoning = strategy.get('reasoning', 'Roleplay context building')
            suggested_tone = strategy.get('suggested_tone', 'natural')
            
            # Validate approach
            if not approach or not isinstance(approach, str):
                print(f"      ⚠️  Invalid approach '{approach}', using default")
                approach = 'roleplay_active'
            
            # Build comprehensive context parts
            context_parts = []
            
            # 1. Core roleplay setup
            context_parts.append("=== ROLEPLAY CONTEXT ===")
            context_parts.append("Setting: Star Trek - USS Stardancer")
            context_parts.append("Character: Elsie - Holographic bartender and stellar cartographer")
            
            # Check for DGM scene context to get correct location
            current_location = "Dizzy Lizzy's Bar"  # Default location
            try:
                if rp_state and rp_state.is_roleplaying:
                    dgm_context = rp_state.get_dgm_scene_context()
                    if dgm_context and dgm_context.get('location'):
                        current_location = dgm_context['location']
                    elif rp_state.is_dgm_session():
                        # DGM session but no specific location - keep Dizzy Lizzy's
                        current_location = "Dizzy Lizzy's Bar"
            except Exception as e:
                print(f"      ⚠️  Error getting location context: {e}")
            
            context_parts.append(f"Location: {current_location}")
            
            # 2. Critical formatting instructions
            context_parts.append("\n=== RESPONSE FORMATTING REQUIREMENTS ===")
            context_parts.append("CRITICAL: Follow these formatting rules exactly:")
            context_parts.append("1. Use third-person narration: 'Elsie smiles' not 'I smile'")
            context_parts.append("2. Prefix ALL responses with [Elsie]")
            context_parts.append("3. Put spoken dialogue in quotes: \"Hello there!\"")
            context_parts.append("4. Put actions/emotes in asterisks: *smiles warmly*")
            context_parts.append("5. Example: [Elsie] *looks up from cleaning a glass* \"Good evening! What can I get for you?\"")
            context_parts.append("6. Location is Dizzy Lizzy's Bar (NOT Ten Forward)")
            context_parts.append("7. Be concise and natural - avoid overly dramatic or verbose responses")
            
            # 3. Strategy-based approach guidance
            context_parts.append(f"\n=== RESPONSE STRATEGY ===")
            context_parts.append(f"Approach: {approach}")
            context_parts.append(f"Reasoning: {reasoning}")
            context_parts.append(f"Suggested Tone: {suggested_tone}")
            
            # 4. Current roleplay state context (with error handling)
            try:
                if rp_state and rp_state.is_roleplaying:
                    context_parts.append(f"\n=== ROLEPLAY SESSION STATE ===")
                    context_parts.append(f"Session Active: Yes")
                    
                    # Safe method calls with fallbacks
                    try:
                        context_parts.append(f"DGM Session: {rp_state.is_dgm_session()}")
                    except Exception as e:
                        print(f"      ⚠️  Error getting DGM session state: {e}")
                        context_parts.append(f"DGM Session: Unknown")
                    
                    try:
                        context_parts.append(f"Listening Mode: {rp_state.listening_mode}")
                    except Exception as e:
                        print(f"      ⚠️  Error getting listening mode: {e}")
                        context_parts.append(f"Listening Mode: Unknown")
                    
                    # Add participant information
                    try:
                        participants = rp_state.get_participant_names()
                        if participants:
                            context_parts.append(f"Known Participants: {', '.join(participants)}")
                    except Exception as e:
                        print(f"      ⚠️  Error getting participants: {e}")
                    
                    # Add character relationship context
                    try:
                        if hasattr(rp_state, 'last_character_elsie_addressed') and rp_state.last_character_elsie_addressed:
                            context_parts.append(f"Last Character Addressed by Elsie: {rp_state.last_character_elsie_addressed}")
                    except Exception as e:
                        print(f"      ⚠️  Error getting last addressed character: {e}")
                    
                    # Add DGM scene context if available
                    try:
                        dgm_context = rp_state.get_dgm_scene_context()
                        if dgm_context:
                            context_parts.append(f"\n=== DGM SCENE CONTEXT ===")
                            for key, value in dgm_context.items():
                                if key != 'raw_description' and value:
                                    context_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                    except Exception as e:
                        print(f"      ⚠️  Error getting DGM scene context: {e}")
                else:
                    context_parts.append(f"\n=== ROLEPLAY SESSION STATE ===")
                    context_parts.append(f"Session Active: No")
            except Exception as e:
                print(f"      ❌ Error accessing roleplay state: {e}")
                context_parts.append(f"\n=== ROLEPLAY SESSION STATE ===")
                context_parts.append(f"Session Active: Unknown (Error accessing state)")
            
            # 5. Character analysis of current message (with error handling)
            try:
                speaking_character = char_service.detect_speaking_character(user_message)
                addressed_characters = char_service.extract_addressed_characters(user_message)
                
                if speaking_character != 'Unknown' or addressed_characters:
                    context_parts.append(f"\n=== CHARACTER INTERACTION ===")
                    if speaking_character != 'Unknown':
                        context_parts.append(f"Speaking Character: {speaking_character}")
                    if addressed_characters:
                        context_parts.append(f"Addressed Characters: {', '.join(addressed_characters)}")
            except Exception as e:
                print(f"      ⚠️  Error in character analysis: {e}")
                context_parts.append(f"\n=== CHARACTER INTERACTION ===")
                context_parts.append(f"Character Analysis: Error occurred")
            
            # 6. Approach-specific context enhancement
            try:
                if approach == 'roleplay_listening':
                    context_parts.append(f"\n=== LISTENING MODE GUIDANCE ===")
                    context_parts.append("Elsie should observe quietly unless directly addressed or action is needed")
                    context_parts.append("Focus on subtle presence and scene awareness")
                elif approach == 'roleplay_active':
                    context_parts.append(f"\n=== ACTIVE ROLEPLAY GUIDANCE ===")
                    context_parts.append("Engage naturally in character as Elsie")
                    context_parts.append("Respond to interactions and maintain scene presence")
                elif approach.startswith('roleplay_'):
                    context_parts.append(f"\n=== SPECIALIZED ROLEPLAY GUIDANCE ===")
                    context_parts.append(f"Apply specialized approach: {approach}")
            except Exception as e:
                print(f"      ⚠️  Error in approach-specific guidance: {e}")
            
            # 7. Core Memory & Relationship Context (Essential for Elsie's personality)
            memory_context = self._load_memory_context()
            if memory_context:
                context_parts.append("\n=== ELSIE'S CORE MEMORIES & RELATIONSHIPS ===")
                context_parts.append(memory_context)
            
            # 8. Database content retrieval for enhanced context (with comprehensive error handling)
            context_parts.append(f"\n=== ADDITIONAL CONTEXT ===")
            try:
                # Get content filter service
                content_filter = get_content_filter_service()
                
                # Import content retriever via service container
                from ..service_container import get_content_retriever
                content_retriever = get_content_retriever()
                
                # Create a basic query structure for roleplay content
                roleplay_query = {
                    'type': 'general',
                    'query': user_message,
                    'category': 'general'
                }
                
                # Retrieve relevant content for roleplay
                retrieval_results = content_retriever.get_content(roleplay_query)
                
                if retrieval_results and len(retrieval_results) > 0:
                    # Use the first result's content
                    content = retrieval_results[0].get('raw_content', '')
                    if content and not content_filter.is_fallback_response(content):
                        # Truncate content to reasonable length
                        max_content_length = 500
                        if len(content) > max_content_length:
                            content = content[:max_content_length] + "..."
                        context_parts.append(f"Relevant Database Content: {content}")
                    else:
                        context_parts.append("Database content: Using base roleplay knowledge")
                else:
                    context_parts.append("Database content: No specific content found, using base knowledge")
                    
            except Exception as e:
                print(f"      ⚠️  Error retrieving database content: {e}")
                context_parts.append("Database content: Not available, using base knowledge")
            
            # 9. Current message context
            context_parts.append(f"\n=== CURRENT INTERACTION ===")
            # Sanitize user message for display
            safe_user_message = user_message.replace('\n', ' ').replace('\r', ' ')[:200]
            if len(user_message) > 200:
                safe_user_message += "..."
            context_parts.append(f"User Message: {safe_user_message}")
            
            # Build final prompt
            final_context = "\n".join(context_parts)
            
            # Validate final context
            if not final_context or len(final_context) < 100:
                print(f"      ⚠️  Generated context too short, using fallback")
                return self._build_strategy_fallback_context(strategy, user_message)
            
            print(f"      ✅ Strategy-aware context built: {len(final_context)} characters")
            return final_context
            
        except Exception as e:
            print(f"      ❌ Error in strategy-aware context building: {e}")
            import traceback
            print(f"      📋 Traceback: {traceback.format_exc()}")
            # Fallback to basic context building
            return self._build_strategy_fallback_context(strategy, user_message)

    def _build_strategy_fallback_context(self, strategy: Dict[str, Any], user_message: str) -> str:
        """
        Build a fallback context when strategy processing fails.
        
        Args:
            strategy: Strategy dictionary
            user_message: User's message
            
        Returns:
            Fallback context string
        """
        approach = strategy.get('approach', 'roleplay_active')
        reasoning = strategy.get('reasoning', 'Fallback context')
        
        return f"""=== ROLEPLAY CONTEXT (FALLBACK) ===
Setting: Star Trek - USS Stardancer
Character: Elsie - Holographic bartender and stellar cartographer
Location: Dizzy Lizzy's Bar

=== RESPONSE FORMATTING REQUIREMENTS ===
CRITICAL: Follow these formatting rules exactly:
1. Use third-person narration: 'Elsie smiles' not 'I smile'
2. Prefix ALL responses with [Elsie]
3. Put spoken dialogue in quotes: "Hello there!"
4. Put actions/emotes in asterisks: *smiles warmly*
5. Example: [Elsie] *looks up from cleaning a glass* "Good evening! What can I get for you?"
6. Location is Dizzy Lizzy's Bar (NOT Ten Forward)
7. Be concise and natural - avoid overly dramatic or verbose responses

=== RESPONSE STRATEGY ===
Approach: {approach}
Reasoning: {reasoning}

=== CURRENT INTERACTION ===
User Message: {user_message}

Respond naturally as Elsie in character, maintaining the Star Trek setting and her role as a holographic bartender."""
    
    def _load_memory_context(self) -> str:
        """
        Load Elsie's core memories and relationships for roleplay context.
        
        This includes:
        - Stardancer log summary
        - Core relationships (Maeve, Marcus, Sif)
        - Self-knowledge about Elsie
        
        Returns:
            Formatted memory context string
        """
        try:
            print(f"      🧠 LOADING CORE MEMORY CONTEXT...")
            
            memory_parts = []
            
            # 1. Load Stardancer log summary
            log_summary = self._get_stardancer_log_summary()
            if log_summary:
                memory_parts.append("STARDANCER RECENT ACTIVITY:")
                memory_parts.append(log_summary)
            
            # 2. Load core relationships
            relationships = self._get_core_relationships()
            if relationships:
                memory_parts.append("\nCORE RELATIONSHIPS:")
                memory_parts.append(relationships)
            
            # 3. Load self-knowledge
            self_knowledge = self._get_elsie_self_knowledge()
            if self_knowledge:
                memory_parts.append("\nELSIE'S SELF-KNOWLEDGE:")
                memory_parts.append(self_knowledge)
            
            if memory_parts:
                result = "\n".join(memory_parts)
                print(f"      ✅ Memory context loaded: {len(result)} characters")
                return result
            else:
                print(f"      ⚠️  No memory context available")
                return ""
                
        except Exception as e:
            print(f"      ❌ Error loading memory context: {e}")
            return ""
    
    def _get_stardancer_log_summary(self) -> str:
        """
        Get a summary of all Stardancer logs using the wisdom engine.
        
        Returns:
            Summary of recent Stardancer activities and events
        """
        try:
            print(f"         📜 Retrieving Stardancer log summary...")
            
            # Import wisdom engine
            from ..service_container import get_wisdom_engine
            wisdom_engine = get_wisdom_engine()
            
            # Create strategy for comprehensive log retrieval
            log_strategy = {
                'approach': 'logs',
                'query': 'stardancer',
                'category': 'logs',
                'subject': 'Stardancer log summary for Elsie roleplay context'
            }
            
            # Get comprehensive log summary
            log_context = wisdom_engine.build_context_for_strategy(log_strategy, 'Get all Stardancer logs')
            
            if log_context and len(log_context) > 100:
                # Limit to reasonable length for context
                if len(log_context) > 2000:
                    log_context = log_context[:2000] + "... [summary continues]"
                print(f"         ✅ Log summary retrieved: {len(log_context)} characters")
                return log_context
            else:
                print(f"         ⚠️  No log summary available")
                return "Recent Stardancer logs: No specific recent activities recorded."
                
        except Exception as e:
            print(f"         ❌ Error retrieving log summary: {e}")
            return "Recent Stardancer logs: Unable to access log data."
    
    def _get_core_relationships(self) -> str:
        """
        Get information about Elsie's core relationships.
        
        Returns:
            Formatted relationship context
        """
        try:
            print(f"         👥 Loading core relationships...")
            
            # Import content retriever
            from ..service_container import get_content_retriever
            content_retriever = get_content_retriever()
            
            relationships = []
            
            # Core relationships to load
            core_people = [
                {
                    'name': 'Maeve Blaine',
                    'context': 'best friend, daughter of Captain Marcus Blaine, mother Niaev in stasis'
                },
                {
                    'name': 'Marcus Blaine', 
                    'context': 'Captain, Elsie respects him, father of Maeve'
                },
                {
                    'name': 'Commander Sif',
                    'context': 'idol, model for photonic lifeforms like Elsie'
                },
                {
                    'name': 'Niaev',
                    'context': 'Maeve\'s mother, in stasis for neurological disease'
                }
            ]
            
            # Try to retrieve database information for each person
            for person in core_people:
                try:
                    person_query = {
                        'type': 'character',
                        'query': person['name'],
                        'category': 'character_info'
                    }
                    
                    results = content_retriever.get_content(person_query)
                    
                    if results and len(results) > 0:
                        db_info = results[0].get('raw_content', '')
                        if db_info and len(db_info) > 50:
                            # Combine context with database info
                            limited_db = db_info[:300] + "..." if len(db_info) > 300 else db_info
                            relationships.append(f"• {person['name']}: {person['context']} | Database: {limited_db}")
                        else:
                            relationships.append(f"• {person['name']}: {person['context']}")
                    else:
                        relationships.append(f"• {person['name']}: {person['context']}")
                        
                except Exception as e:
                    print(f"         ⚠️  Error loading {person['name']}: {e}")
                    relationships.append(f"• {person['name']}: {person['context']}")
            
            if relationships:
                result = "\n".join(relationships)
                print(f"         ✅ Core relationships loaded: {len(core_people)} people")
                return result
            else:
                                # Fallback: Core relationships hardcoded to ensure Elsie always has her personality
                fallback_relationships = [
                    "• Maeve Blaine: best friend, daughter of Captain Marcus Blaine, mother Niaev in stasis for neurological disease",
                    "• Marcus Blaine: Captain, Elsie respects him, father of Maeve Blaine",
                    "• Commander Sif: idol, model for photonic lifeforms like Elsie",
                    "• Niaev: Maeve's mother, in stasis for neurological disease on the Stardancer"
                ]
                print(f"         ⚠️  Using fallback core relationships")
                return "\n".join(fallback_relationships)
                
        except Exception as e:
            print(f"         ❌ Error loading relationships: {e}")
            # Fallback: Ensure Elsie always has core relationships
            fallback_relationships = [
                "• Maeve Blaine: best friend, daughter of Captain Marcus Blaine, mother Niaev in stasis for neurological disease",
                "• Marcus Blaine: Captain, Elsie respects him, father of Maeve Blaine", 
                "• Commander Sif: idol, model for photonic lifeforms like Elsie",
                "• Niaev: Maeve's mother, in stasis for neurological disease on the Stardancer"
            ]
            print(f"         ⚠️  Using fallback core relationships due to error")
            return "\n".join(fallback_relationships)
    
    def _get_elsie_self_knowledge(self) -> str:
        """
        Get information about Elsie herself from the database.
        
        Returns:
            Elsie's self-knowledge context
        """
        try:
            print(f"         🪞 Loading Elsie's self-knowledge...")
            
            # Import content retriever
            from ..service_container import get_content_retriever
            content_retriever = get_content_retriever()
            
            # Query for information about Elsie
            elsie_query = {
                'type': 'character',
                'query': 'Elsie',
                'category': 'character_info'
            }
            
            results = content_retriever.get_content(elsie_query)
            
            if results and len(results) > 0:
                elsie_info = results[0].get('raw_content', '')
                if elsie_info and len(elsie_info) > 50:
                    # Limit to reasonable length
                    if len(elsie_info) > 1000:
                        elsie_info = elsie_info[:1000] + "... [continues]"
                    print(f"         ✅ Self-knowledge loaded: {len(elsie_info)} characters")
                    return elsie_info
            
            # Fallback self-knowledge
            fallback = """Elsie is a holographic bartender and stellar cartographer aboard the USS Stardancer. 
She serves drinks at Dizzy Lizzy's Bar and assists with navigation and stellar mapping. 
As a photonic being, she looks up to Commander Sif as a role model. 
She has formed close friendships with the crew, especially Maeve Blaine."""
            
            print(f"         ⚠️  Using fallback self-knowledge")
            return fallback
            
        except Exception as e:
            print(f"         ❌ Error loading self-knowledge: {e}")
            return "Self-knowledge: Basic holographic bartender and stellar cartographer programming."


def build_roleplay_context(user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
    """
    Build comprehensive roleplay context using the content retriever and LLM processing.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation history
        character_context: Optional character context information
        
    Returns:
        Built roleplay context prompt
    """
    # Get content filter service
    content_filter = get_content_filter_service()
    
    # Import content retriever via service container
    from ..service_container import get_content_retriever
    content_retriever = get_content_retriever()
    
    # Create a basic query structure for roleplay content
    roleplay_query = {
        'type': 'general',
        'query': user_message,
        'category': 'general'
    }
    
    # Retrieve relevant content for roleplay
    retrieval_results = content_retriever.get_content(roleplay_query)
    
    # Check if we have useful content
    has_useful_content = False
    content_text = ""
    
    if retrieval_results and len(retrieval_results) > 0:
        content_text = retrieval_results[0].get('raw_content', '')
        has_useful_content = content_text and not content_filter.is_fallback_response(content_text)
    
    if not has_useful_content:
        print("⚠️ ROLEPLAY CONTEXT: No useful content retrieved, using fallback")
        # Handle fallback scenario
        return _build_fallback_roleplay_context(user_message, conversation_history, character_context)
    
    # Build the full context prompt
    context_parts = []
    
    # Add character context if available
    if character_context:
        context_parts.append(f"Character Context: {character_context}")
    
    # Add retrieved content
    if content_text:
        context_parts.append(f"Relevant Content: {content_text[:1000]}...")  # Limit content length
    
    # Add conversation history
    if conversation_history:
        recent_history = conversation_history[-5:]  # Last 5 messages
        context_parts.append(f"Recent Conversation: {' '.join(recent_history)}")
    
    # Add current message
    context_parts.append(f"Current Message: {user_message}")
    
    return "\n\n".join(context_parts)


def _build_fallback_roleplay_context(user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
    """
    Build a fallback roleplay context when content retrieval fails.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation history
        character_context: Optional character context information
        
    Returns:
        Fallback roleplay context
    """
    fallback_parts = []
    
    # Basic roleplay setup
    fallback_parts.append("Roleplay Context: Star Trek setting aboard the USS Stardancer")
    fallback_parts.append("Character: Elsie - Holographic bartender and stellar cartographer")
    fallback_parts.append("Location: Dizzy Lizzy's Bar")
    
    # Critical formatting instructions
    fallback_parts.append("\n=== RESPONSE FORMATTING REQUIREMENTS ===")
    fallback_parts.append("CRITICAL: Follow these formatting rules exactly:")
    fallback_parts.append("1. Use third-person narration: 'Elsie smiles' not 'I smile'")
    fallback_parts.append("2. Prefix ALL responses with [Elsie]")
    fallback_parts.append("3. Put spoken dialogue in quotes: \"Hello there!\"")
    fallback_parts.append("4. Put actions/emotes in asterisks: *smiles warmly*")
    fallback_parts.append("5. Example: [Elsie] *looks up from cleaning a glass* \"Good evening! What can I get for you?\"")
    fallback_parts.append("6. Location is Dizzy Lizzy's Bar (NOT Ten Forward)")
    fallback_parts.append("7. Be concise and natural - avoid overly dramatic or verbose responses")
    
    # Add character context if available
    if character_context:
        fallback_parts.append(f"Additional Context: {character_context}")
    
    # Add recent conversation
    if conversation_history:
        recent_history = conversation_history[-3:]  # Last 3 messages for fallback
        fallback_parts.append(f"Recent Conversation: {' '.join(recent_history)}")
    
    # Add current message
    fallback_parts.append(f"Current Message: {user_message}")
    
    return "\n\n".join(fallback_parts)


# Legacy function for backward compatibility
def get_enhanced_roleplay_context(user_message: str, conversation_history: List[str], character_context: Dict[str, Any] = None) -> str:
    """
    Legacy function for backward compatibility with enhanced strategy support.
    
    This function now intelligently detects if character_context contains a strategy
    and routes to the appropriate context building method.
    
    Args:
        user_message: The user's message
        conversation_history: Recent conversation history
        character_context: Optional character context information or strategy dictionary
        
    Returns:
        Built roleplay context prompt
    """
    # Enhanced: Check if character_context is actually a strategy from attention engine
    if character_context and isinstance(character_context, dict):
        # If it contains strategy fields, use the new strategy-aware builder
        if 'approach' in character_context or 'reasoning' in character_context:
            print(f"      🔄 LEGACY ADAPTER: Detected strategy in character_context, using strategy-aware builder")
            builder = RoleplayContextBuilder()
            return builder.build_context_for_strategy(character_context, user_message)
    
    # Otherwise, use traditional context building
    print(f"      📚 LEGACY ADAPTER: Using traditional context building")
    return build_roleplay_context(user_message, conversation_history, character_context) 