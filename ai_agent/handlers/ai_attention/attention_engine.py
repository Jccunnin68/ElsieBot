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
from .state_manager import RoleplayStateManager, get_roleplay_state
from ..ai_emotion.emotion_engine import get_emotion_engine
from ..ai_attention.character_tracking import extract_character_names_from_emotes

class AttentionEngine:
    """
    An engine that uses an LLM to decide on the optimal roleplay strategy.
    """
    def __init__(self, model_name='gemma-3-27b-it'):
        """
        Initializes the AttentionEngine with a powerful model.
        """
        self.model = genai.GenerativeModel(model_name)
        self.emotion_engine = get_emotion_engine()

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
            # 1. Get emotional context
            emotional_analysis = self.emotion_engine.analyze_emotion(user_message)

            # 2. Build the comprehensive prompt
            prompt = self._build_prompt(user_message, conversation_history, rp_state, emotional_analysis)
            
            # 3. Get the strategy from the LLM
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.3 # Higher creativity for strategy
                )
            )
            
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            strategy_decision = json.loads(cleaned_response)

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

    def _build_prompt(self, user_message: str, conversation_history: List[Dict], rp_state: RoleplayStateManager, emotional_analysis: Dict) -> str:
        """Constructs the master prompt for the Roleplay Director LLM."""
        
        history_str = "\\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        
        return f"""
You are the "Roleplay Director" for an advanced AI named Elsie. Your task is to analyze the state of a roleplay conversation and decide on the best course of action for Elsie.

**1. Current State Analysis:**

*   **User's Latest Message:** "{user_message}"
*   **Emotional Analysis of Message:** {json.dumps(emotional_analysis)}
*   **Conversation History:**
    {history_str}
*   **Current Roleplay State:**
    *   Characters present: {rp_state.get_characters_present()}
    *   Last character Elsie addressed: {rp_state.last_character_elsie_addressed}
    *   Is Elsie's response turn overdue?: {rp_state.is_elsie_turn_overdue()}

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

# Global instance for easy access
_attention_engine_instance = None

def get_attention_engine():
    """Singleton accessor for the AttentionEngine."""
    global _attention_engine_instance
    if _attention_engine_instance is None:
        _attention_engine_instance = AttentionEngine()
    return _attention_engine_instance 