"""
Emotion Engine - LLM-Powered Emotional Analysis
===============================================

This module provides an LLM-based engine for analyzing the emotional
content of text.
"""
from typing import Dict
import json

from config import OLLAMA_EMOTION_MODEL, OLLAMA_EMOTION_URL
from ..local_gemma import LocalGemma

class EmotionEngine:
    """
    An engine that uses an LLM to perform nuanced emotional analysis.
    """
    def __init__(self, model_name=None):
        """
        Initializes the EmotionEngine with the local Gemma emotion container.
        Args:
            model_name: Optional model tag override.
        """
        self.client = LocalGemma(OLLAMA_EMOTION_URL, model_name or OLLAMA_EMOTION_MODEL)

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
        if not text or not self.client.configured:
            return self._default_emotion()

        try:
            prompt = self._build_prompt(text)
            cleaned_response = self.client.generate(
                prompt,
                temperature=0.2,
                json_mode=True,
            ).replace("```json", "").replace("```", "")
            
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

# REMOVED: Global instance replaced by service container
# Use service_container.get_emotion_engine() instead 