"""
Attention Engine - LLM-Powered Roleplay Strategy
=================================================

This module provides the core engine for determining Elsie's response
strategy during roleplay, using a powerful LLM to act as a "Roleplay Director."
"""
import google.generativeai as genai
from typing import Dict, List
import json

from config import GEMMA_API_KEY
from ..ai_logic.response_decision import ResponseDecision
from .state_manager import RoleplayStateManager


class AttentionEngine:
    """
    An engine that uses an LLM to decide on the optimal roleplay strategy.
    """
    def __init__(self, model_name='gemma-3-27b-it'):
        """
        Initializes the AttentionEngine with Gemma for roleplay strategy decisions.
        Dependencies injected after initialization.
        """
        self.model = genai.GenerativeModel(model_name)
        self.emotion_engine = None  # Will be injected via service container

    def determine_response_strategy(self, user_message: str, conversation_history: List[Dict], rp_state: RoleplayStateManager) -> ResponseDecision:
        """
        Analyzes the conversational context and determines the best roleplay
        response strategy for Elsie.

        Args:
            user_message: The latest message from the user.
            conversation_history: The recent history of the conversation.
            rp_state: The current state of the roleplay.

        Returns:
            A ResponseDecision object containing the chosen strategy.
        """
        if not user_message or not GEMMA_API_KEY:
            return ResponseDecision(needs_ai_generation=False, strategy={'approach': 'roleplay_listening', 'reasoning': 'No message or API key.'})

        try:
            # 1. Get emotional context (lazy load emotion engine)
            if self.emotion_engine is None:
                from ..service_container import get_emotion_engine
                self.emotion_engine = get_emotion_engine()
            
            emotional_analysis = self.emotion_engine.analyze_emotion(user_message)

            # 2. Build the comprehensive prompt
            prompt = self._build_prompt(user_message, conversation_history, rp_state, emotional_analysis)
            
            # 3. Get the strategy from the LLM
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3 # Higher creativity for strategy
                )
            )
            
            # Parse the response - Gemma will return structured text, extract JSON from it
            response_text = response.text.strip()
            strategy_decision = self._parse_strategy_response(response_text)

            print(f"   🎬 ATTENTION ENGINE DECISION: {strategy_decision}")

            # 4. Construct the final ResponseDecision
            # The 'context_prompt' will be built later by the context builders.
            # The engine's job is just to decide the *strategy*.
            return ResponseDecision(
                needs_ai_generation=strategy_decision.get('should_respond', False),
                strategy=strategy_decision
            )

        except Exception as e:
            print(f"   ❌ ERROR in AttentionEngine: {e}")
            return ResponseDecision(needs_ai_generation=False, strategy={'approach': 'roleplay_error', 'reasoning': 'Error in AttentionEngine.'})

    def analyze_dgm_scene_context(self, dgm_text: str) -> Dict:
        """
        Analyze DGM scene text for enhanced character and context understanding.
        
        This method uses AI to provide deeper analysis of DGM posts when needed
        by other components like the context builder.
        
        Args:
            dgm_text: The DGM scene text (without [DGM] tag)
            
        Returns:
            Dictionary with enhanced scene analysis including characters and context
        """
        if not GEMMA_API_KEY or not dgm_text.strip():
            print("      ⚠️  No API key or empty text - returning basic analysis")
            return {'characters': [], 'scene_context': {}}
        
        try:
            print(f"      🧠 ATTENTION ENGINE: Enhanced DGM analysis for '{dgm_text[:60]}...'")
            
            prompt = f"""You are analyzing a DGM roleplay scene description to extract comprehensive information for an AI character named Elsie.

SCENE TEXT TO ANALYZE:
"{dgm_text}"

Extract the following information:

1. CHARACTER ANALYSIS:
   - Extract ONLY character names (people), not locations or objects
   - Handle titles properly: "captain marcus blaine" should become "Marcus Blaine"
   - Ignore location names like "Ten Forward", "VIP section", "Dizzy Lizzy" (bar name)
   - Ignore descriptive terms like "cadets", "many", "excitement"
   - Handle case-insensitive names properly

2. SCENE CONTEXT:
   - Location: Where is the scene taking place?
   - Time: What time of day is it?
   - Atmosphere: What's the mood/feeling?
   - Activity: What's happening in the scene?

3. ROLEPLAY GUIDANCE:
   - Should Elsie be aware of this scene?
   - Are there interaction opportunities for Elsie?
   - What tone should Elsie adopt if she responds?

Return ONLY a JSON object:

{{
  "characters": ["Character Name 1", "Character Name 2"],
  "scene_context": {{
    "location": "location name or null",
    "time_of_day": "time or null",
    "atmosphere": "mood or null", 
    "activity": "what's happening or null"
  }},
  "roleplay_guidance": {{
    "elsie_awareness": "should Elsie be aware of this scene?",
    "interaction_opportunities": "potential ways Elsie could interact",
    "suggested_tone": "tone for Elsie if she responds"
  }}
}}"""

            # Use the same model (Gemma) for consistency
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1  # Low temperature for consistent analysis
                )
            )
            
            # Parse the response using our parsing method
            analysis_result = self._parse_dgm_analysis_response(response.text.strip())
            
            print(f"      ✅ ENHANCED DGM ANALYSIS COMPLETE:")
            if analysis_result.get('characters'):
                print(f"         Characters: {analysis_result['characters']}")
            if analysis_result.get('scene_context'):
                context = analysis_result['scene_context']
                for key, value in context.items():
                    if value:
                        print(f"         {key}: {value}")
            
            return analysis_result
            
        except Exception as e:
            print(f"      ❌ Enhanced DGM analysis failed: {e}")
            print(f"      🔄 Returning basic analysis")
            return {'characters': [], 'scene_context': {}, 'roleplay_guidance': {}}

    def _parse_strategy_response(self, response_text: str) -> Dict:
        """
        Parse the strategy response from Gemma, handling various formats.
        
        Args:
            response_text: Raw response text from Gemma
            
        Returns:
            Parsed strategy dictionary
        """
        try:
            # First, try to find JSON in the response
            import re
            
            # Look for JSON object patterns
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            for match in json_matches:
                try:
                    # Clean up the match and try to parse it
                    clean_match = match.strip()
                    parsed = json.loads(clean_match)
                    
                    # Validate it has the required fields
                    if 'should_respond' in parsed and 'approach' in parsed:
                        print(f"   ✅ PARSED JSON STRATEGY: {parsed}")
                        return parsed
                except json.JSONDecodeError:
                    continue
            
            # If no valid JSON found, try to extract from code blocks
            code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            code_matches = re.findall(code_block_pattern, response_text, re.DOTALL)
            
            for match in code_matches:
                try:
                    parsed = json.loads(match.strip())
                    if 'should_respond' in parsed and 'approach' in parsed:
                        print(f"   ✅ PARSED CODE BLOCK STRATEGY: {parsed}")
                        return parsed
                except json.JSONDecodeError:
                    continue
            
            # If still no luck, try manual parsing from structured text
            print(f"   ⚠️  No valid JSON found, attempting manual parsing from: {response_text[:200]}...")
            return self._manual_parse_strategy(response_text)
            
        except Exception as e:
            print(f"   ❌ Strategy parsing failed: {e}")
            return self._fallback_strategy()
    
    def _manual_parse_strategy(self, response_text: str) -> Dict:
        """
        Manually parse strategy from structured text when JSON parsing fails.
        
        Args:
            response_text: Raw response text from Gemma
            
        Returns:
            Parsed strategy dictionary
        """
        import re
        
        strategy = {}
        
        # Look for key-value patterns
        patterns = {
            'should_respond': r'should_respond[\'"]?\s*:\s*([\'"]?)(true|false)\1',
            'approach': r'approach[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]',
            'reasoning': r'reasoning[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]',
            'suggested_tone': r'suggested_tone[\'"]?\s*:\s*[\'"]([^\'"]+)[\'"]'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                if key == 'should_respond':
                    strategy[key] = match.group(2).lower() == 'true'
                else:
                    strategy[key] = match.group(1) if key == 'approach' else match.group(1)
        
        # Set defaults for missing fields
        if 'should_respond' not in strategy:
            strategy['should_respond'] = False
        if 'approach' not in strategy:
            strategy['approach'] = 'roleplay_listening'
        if 'reasoning' not in strategy:
            strategy['reasoning'] = 'Parsed from unstructured response'
        
        print(f"   🔧 MANUAL PARSE RESULT: {strategy}")
        return strategy
    
    def _fallback_strategy(self) -> Dict:
        """
        Return a safe fallback strategy when all parsing fails.
        
        Returns:
            Safe fallback strategy dictionary
        """
        return {
            'should_respond': False,
            'approach': 'roleplay_listening',
            'reasoning': 'Fallback due to parsing error',
            'suggested_tone': 'observant'
        }
    
    def _parse_dgm_analysis_response(self, response_text: str) -> Dict:
        """
        Parse the DGM analysis response from Gemma.
        
        Args:
            response_text: Raw response text from Gemma
            
        Returns:
            Parsed DGM analysis dictionary
        """
        try:
            import re
            
            # Try to find JSON in the response first
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, response_text, re.DOTALL)
            
            for match in json_matches:
                try:
                    clean_match = match.strip()
                    parsed = json.loads(clean_match)
                    
                    # Validate it has expected structure
                    if 'characters' in parsed or 'scene_context' in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue
            
            # Try code blocks
            code_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            code_matches = re.findall(code_block_pattern, response_text, re.DOTALL)
            
            for match in code_matches:
                try:
                    parsed = json.loads(match.strip())
                    if 'characters' in parsed or 'scene_context' in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue
            
            # Manual extraction as fallback
            print(f"      ⚠️  DGM JSON parsing failed, attempting manual extraction...")
            return self._manual_parse_dgm_analysis(response_text)
            
        except Exception as e:
            print(f"      ❌ DGM analysis parsing failed: {e}")
            return {'characters': [], 'scene_context': {}, 'roleplay_guidance': {}}
    
    def _manual_parse_dgm_analysis(self, response_text: str) -> Dict:
        """
        Manually extract DGM analysis from unstructured text.
        
        Args:
            response_text: Raw response text
            
        Returns:
            Basic DGM analysis structure
        """
        import re
        
        # Basic character extraction from response text
        characters = []
        
        # Look for character names in quotes or after "Character:" patterns
        char_patterns = [
            r'"([A-Z][a-zA-Z\s]+)"',
            r'[Cc]haracter[s]?:\s*([A-Z][a-zA-Z\s,]+)',
            r'[Nn]ame[s]?:\s*([A-Z][a-zA-Z\s,]+)'
        ]
        
        for pattern in char_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                # Split on commas and clean up
                names = [name.strip() for name in match.split(',')]
                for name in names:
                    if len(name) > 2 and name not in characters:
                        characters.append(name)
        
        return {
            'characters': characters,
            'scene_context': {},
            'roleplay_guidance': {}
        }

    def _build_prompt(self, user_message: str, conversation_history: List[Dict], rp_state: RoleplayStateManager, emotional_analysis: Dict) -> str:
        """Constructs the master prompt for the Roleplay Director LLM."""
        
        # Enhanced conversation history processing
        history_parts = []
        if conversation_history:
            for i, msg in enumerate(conversation_history[-5:]):  # Last 5 messages for context
                if isinstance(msg, dict):
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    # Extract character information if available
                    if '[' in content and ']' in content:
                        char_match = content.split(']')[0].replace('[', '').strip()
                        history_parts.append(f"    Turn {i+1}: [{char_match}] {content}")
                    else:
                        history_parts.append(f"    Turn {i+1}: {role}: {content}")
                else:
                    history_parts.append(f"    Turn {i+1}: {str(msg)}")
        
        history_str = "\n".join(history_parts) if history_parts else "    No recent conversation history"
        
        # Enhanced roleplay state information
        state_info = []
        if rp_state:
            participants = rp_state.get_participant_names()
            if participants:
                state_info.append(f"Characters present: {', '.join(participants)}")
            else:
                state_info.append("Characters present: None identified")
                
            if rp_state.last_character_elsie_addressed:
                state_info.append(f"Last character Elsie addressed: {rp_state.last_character_elsie_addressed}")
            
            if hasattr(rp_state, 'is_elsie_turn_overdue') and callable(rp_state.is_elsie_turn_overdue):
                state_info.append(f"Is Elsie's response turn overdue?: {rp_state.is_elsie_turn_overdue()}")
            
            state_info.append(f"DGM session: {rp_state.is_dgm_session()}")
            state_info.append(f"Listening mode: {rp_state.listening_mode}")
            
            # Add DGM scene context if available
            dgm_context = rp_state.get_dgm_scene_context()
            if dgm_context:
                scene_details = []
                for key, value in dgm_context.items():
                    if key != 'raw_description' and value:
                        scene_details.append(f"{key}: {value}")
                if scene_details:
                    state_info.append(f"Scene context: {', '.join(scene_details)}")
        else:
            state_info.append("Roleplay state: Not available")
        
        state_str = "\n    ".join(state_info)
        
        return f"""
You are the "Roleplay Director" for an advanced AI named Elsie. Your task is to analyze the state of a roleplay conversation and decide on the best course of action for Elsie.

**1. Current State Analysis:**

*   **User's Latest Message:** "{user_message}"
*   **Emotional Analysis of Message:** {json.dumps(emotional_analysis)}
*   **Conversation History (Last 5 turns):**
{history_str}
*   **Current Roleplay State:**
    {state_str}

**2. Your Task:**

Based on the state analysis, you must decide if Elsie should respond and, if so, what her strategic approach should be. Consider the emotional tone, who is speaking, who was last spoken to, and the overall flow of the scene.

**3. Decision Schema:**

You must provide your decision as a single JSON object with the following structure:

{{
  "should_respond": "A boolean (true/false) on whether Elsie should generate a response.",
  "approach": "A string representing the chosen strategy. Examples: 'roleplay_active_dialogue', 'roleplay_subtle_action', 'roleplay_character_insight', 'roleplay_listening', 'roleplay_emotional_support'.",
  "reasoning": "A brief explanation for your decision.",
  "suggested_tone": "A few keywords for the emotional tone of Elsie's response (e.g., 'warm, empathetic', 'curious, analytical', 'reserved, observant')."
}}

**4. Strategic Considerations:**

*   **`roleplay_active_dialogue`**: Use for direct conversation with a character.
*   **`roleplay_subtle_action`**: Use when a non-verbal action is more appropriate than speech (e.g., *nods*, *smiles faintly*).
*   **`roleplay_character_insight`**: Use to offer a thoughtful observation or memory related to a character.
*   **`roleplay_listening`**: Use when Elsie should remain quiet and observe the scene. `should_respond` must be false.
*   **`roleplay_emotional_support`**: Use if the emotional analysis indicates a need for support.

**Your decision is critical. Provide only the JSON object.**
"""

# REMOVED: Global instance replaced by service container
# Use service_container.get_attention_engine() instead 