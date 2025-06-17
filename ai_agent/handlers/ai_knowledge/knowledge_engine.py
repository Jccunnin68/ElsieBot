"""
Knowledge Engine - LLM-Powered Log Processor
===========================================

This engine's sole responsibility is to clean raw Discord roleplay logs
using an LLM. It takes messy, multi-user chat data and transforms it into
a clean, third-person sequence of events suitable for summarization.
"""

import time
import google.generativeai as genai
from config import GEMMA_API_KEY

class KnowledgeEngine:
    """A simplified engine for processing log data with an LLM."""

    LLM_MODEL_NAME = 'gemini-2.0-flash-lite'

    def __init__(self):
        self.client = self._initialize_gemini_client()

    def _initialize_gemini_client(self):
        """Initializes the Gemini client."""
        try:
            genai.configure(api_key=GEMMA_API_KEY)
            model = genai.GenerativeModel(self.LLM_MODEL_NAME)
            print(f"✅ KnowledgeEngine initialized with {self.LLM_MODEL_NAME}")
            return model
        except Exception as e:
            print(f"⚠️  Failed to initialize Gemini client for KnowledgeEngine: {e}")
            return None

    def _create_log_cleaning_prompt(self, logs: str) -> str:
        """Creates the prompt to clean up raw Discord logs."""
        return f"""
You are a log cleaning assistant. Your task is to process and clean raw game logs while preserving ALL content. You must maintain the exact same length and number of lines as the input.

**DGM & CHANNEL RULES:**
- DGM Gamemaster Accounts: liorexus, isis, cygnus, illuice, captain_rien, demoncherub, captain_riens
- DOIC Channels: ALL of these contain valid roleplay content. Remove ONLY the channel tags, but keep ALL the text content that follows them:
  * [DOIC] - Main channel with DGM narration and environmental descriptions.
  * [DOIC1], [DOIC2], [DOIC3], etc. - Character dialogue and actions.
  * [Character] - Character dialogue and actions.
  * (OOC) - OOC comments.
  * Filter out Game Master account @names

**CRITICAL INSTRUCTIONS:**
1. **Preserve ALL Content:** You must maintain the exact same length and number of lines as the input. Do not truncate or summarize.
2. **Extract Actions:** Identify every action taken by a character and rewrite it in a third-person, past-tense format (e.g., "Character A did something," "Character B said...").
3. **Remove Metadata Only:** Eliminate timestamps (e.g., `[8:54]`), Channel identifghers. ([DOIC,] @Captain_Rien:`), and OOC comments in double parentheses `((...))` or after `//`.
4. **Preserve Dialogue:** Keep all dialogue within quotation marks.
5. **Maintain Order:** The output must follow the exact chronological order of the original log.
6. **No Summarization:** Your job is ONLY to clean and reformat the log. Do not add narrative flair, interpretations, or combine actions.
7. **Line Count Check:** After processing, verify that the number of lines in your output matches the input.

**RAW LOG DATA TO PROCESS:**
---
{logs}
---

**Cleaned and Reformatted Log:**
"""
    def process_logs(self, raw_logs: str) -> str:
        """
        Cleans raw Game log data using an LLM.

        Args:
            raw_logs: A string containing the raw log data.

        Returns:
            A string containing the cleaned log data, or the original data if processing fails.
        """

        
        if not self.client:
            print("      ❌ KnowledgeEngine LLM client not available. Falling back to raw logs.")
            return raw_logs

        prompt = self._create_log_cleaning_prompt(raw_logs)

        for attempt in range(self.MAX_RETRIES):
            try:
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=1000000,
                    temperature=0.7
                )
                response = self.client.generate_content(prompt, generation_config=generation_config)
                cleaned_content = response.text.strip()
                
                if cleaned_content:
                    print(f"✅ KnowledgeEngine successfully cleaned logs.")
                    return cleaned_content
                else:
                    print(f"      ⚠️  KnowledgeEngine returned empty content on attempt {attempt + 1}.")
            
            except Exception as e:
                print(f"      ❌ KnowledgeEngine LLM call failed on attempt {attempt + 1}: {e}")

            if attempt < self.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

        print("      ❌ All KnowledgeEngine processing attempts failed. Falling back to raw logs.")
        return raw_logs

# Singleton instance
_knowledge_engine = None

def get_knowledge_engine() -> KnowledgeEngine:
    """Provides a global singleton instance of the KnowledgeEngine."""
    global _knowledge_engine
    if _knowledge_engine is None:
        _knowledge_engine = KnowledgeEngine()
    return _knowledge_engine 