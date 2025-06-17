"""
Emotion Engine - LLM-Powered Emotional Analysis
===============================================

This module provides an LLM-based engine for analyzing the emotional
content of text.
"""
import google.generativeai as genai
from typing import Dict
import json

from config import GEMMA_API_KEY

class EmotionEngine:
    """
    An engine that uses an LLM to perform nuanced emotional analysis.
    """
    def __init__(self, model_name='gemini-1.5-flash-latest'):
        """
        Initializes the EmotionEngine with a specific model.
        Args:
            model_name: The name of the generative model to use (defaults to a fast model).
        """
        self.model = genai.GenerativeModel(model_name)

    def analyze_emotion(self, text: str) -> Dict:
        """
        Analyzes the given text to determine its emotional content.

        Args:
            text: The input text to analyze.

        Returns:
            A dictionary containing the emotional analysis, including tone,
            primary emotion, intensity, and whether it suggests a need for support.
            Returns a default neutral analysis on failure.
        """
        if not text or not GEMMA_API_KEY:
            return self._default_emotion()

        try:
            prompt = self._build_prompt(text)
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2 # Low temperature for consistent JSON output
                )
            )
            
            # Clean the response to ensure it's valid JSON
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            
            analysis = json.loads(cleaned_response)
            print(f"   🧠 EMOTION ANALYSIS: {analysis}")
            return analysis

        except Exception as e:
            print(f"   ❌ ERROR in EmotionEngine: {e}")
            return self._default_emotion()

    def _build_prompt(self, text: str) -> str:
        """Constructs the prompt for the LLM."""
        return f"""
Analyze the emotional content of the following user message. Your analysis must be in the form of a JSON object.

USER MESSAGE:
---
{text}
---
END OF MESSAGE

Based on the message, provide a JSON object with the following structure:
{{
  "primary_emotion": "The single most dominant emotion (e.g., 'joy', 'anger', 'sadness', 'curiosity', 'neutral').",
  "tone": "A one or two-word description of the overall tone (e.g., 'formal', 'casual', 'wistful', 'urgent').",
  "intensity": "A float from 0.0 (very weak) to 1.0 (very strong) representing the emotion's intensity.",
  "needs_support": "A boolean (true/false) indicating if the user seems to be expressing a need for emotional support."
}}

Provide only the JSON object in your response.
"""

    def _default_emotion(self) -> Dict:
        """Returns a default, neutral emotional analysis."""
        return {
            "primary_emotion": "neutral",
            "tone": "neutral",
            "intensity": 0.5,
            "needs_support": False
        }

# Global instance for easy access
_emotion_engine_instance = None

def get_emotion_engine():
    """Singleton accessor for the EmotionEngine."""
    global _emotion_engine_instance
    if _emotion_engine_instance is None:
        _emotion_engine_instance = EmotionEngine()
    return _emotion_engine_instance 