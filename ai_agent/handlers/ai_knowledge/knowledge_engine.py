"""
Knowledge Engine - LLM-Powered Log Processor
===========================================

This engine's sole responsibility is to clean raw Discord roleplay logs
using an LLM. It takes messy, multi-user chat data and transforms it into
a clean, third-person sequence of events suitable for summarization.
"""

import time
from config import OLLAMA_KNOWLEDGE_MODEL, OLLAMA_KNOWLEDGE_URL
from handlers.local_gemma import LocalGemma
from .log_patterns import SHIP_SPECIFIC_CHARACTER_CORRECTIONS, FALLBACK_CHARACTER_CORRECTIONS, FLEET_SHIP_NAMES

class KnowledgeEngine:
    """A simplified engine for processing log data with an LLM."""

    MAX_RETRIES = 1

    def __init__(self):
        self.client = LocalGemma(OLLAMA_KNOWLEDGE_URL, OLLAMA_KNOWLEDGE_MODEL)
        self.max_output_tokens = 8192
        if self.client.configured:
            print(f"✅ KnowledgeEngine initialized with {OLLAMA_KNOWLEDGE_MODEL} at {OLLAMA_KNOWLEDGE_URL}")
        else:
            print("⚠️  KnowledgeEngine local model is not configured")

    def _create_character_corrections_text(self) -> str:
        """Creates the character corrections section for the prompt."""
        corrections_text = "\n**CHARACTER NAME CORRECTIONS:**\n"
        corrections_text += "When processing character names, apply these corrections to ensure consistency:\n\n"
        
        # Ship-specific corrections
        corrections_text += "**Ship-Specific Character Corrections:**\n"
        for ship, corrections in SHIP_SPECIFIC_CHARACTER_CORRECTIONS.items():
            corrections_text += f"- {ship.upper()}:\n"
            for incorrect, correct in corrections.items():
                corrections_text += f"  * '{incorrect}' → '{correct}'\n"
        
        corrections_text += "\n**General Character Corrections (when ship context is unclear):**\n"
        for incorrect, correct in FALLBACK_CHARACTER_CORRECTIONS.items():
            corrections_text += f"- '{incorrect}' → '{correct}'\n"
        
        corrections_text += f"\n**Fleet Ship Names to Watch For:**\n"
        corrections_text += f"{', '.join(FLEET_SHIP_NAMES)}\n"
        
        return corrections_text

    def _create_log_cleaning_prompt(self, logs: str) -> str:
        """Creates the prompt to clean up raw game logs."""
        # Use a more compact prompt for the faster model
        line_count = logs.count('\n') + 1
        char_count = len(logs)
        
        return f"""
Reformat roleplay logs by:
- Remove timestamps, channel tags, @mentions, OOC text
- Convert first-person to third-person past tense
- Keep ALL dialogue in quotes
- Preserve ALL actions and story content
- Do NOT summarize or shorten content

Input: {char_count} chars, {line_count} lines
Output should preserve all story content (~{char_count} chars after removing metadata)

Raw log:
---
{logs}
---

Reformatted:
"""

    def process_logs(self, raw_logs: str) -> str:
        """
        Cleans raw log data using an LLM.

        Args:
            raw_logs: A string containing the raw log data (pre-chunked if needed).

        Returns:
            A string containing the cleaned log data, or the original data if processing fails.
        """
        
        if not self.client.configured:
            print("      ❌ KnowledgeEngine LLM client not available. Falling back to raw logs.")
            return raw_logs

        # Check input size 
        input_lines = raw_logs.count('\n') + 1
        input_chars = len(raw_logs)
        print(f"      📊 Input: {input_lines} lines, {input_chars} characters")
        
        prompt = self._create_log_cleaning_prompt(raw_logs)

        for attempt in range(self.MAX_RETRIES):
            try:
                print(f"      🔄 KnowledgeEngine attempt {attempt + 1}/{self.MAX_RETRIES} - Calling {OLLAMA_KNOWLEDGE_MODEL}...")

                start_time = time.time()
                cleaned_content = self.client.generate(
                    prompt,
                    temperature=0.05,
                    max_tokens=self.max_output_tokens,
                    top_p=0.8,
                    top_k=20,
                )
                end_time = time.time()
                
                print(f"      ⏱️  LLM call completed in {end_time - start_time:.2f} seconds")
                
                # If call took too long, warn but continue
                if end_time - start_time > 30:
                    print(f"      ⚠️  KnowledgeEngine call took {end_time - start_time:.2f}s - consider bypassing for speed")
                
                if cleaned_content:
                    output_lines = cleaned_content.count('\n') + 1
                    output_chars = len(cleaned_content)
                    print(f"      📊 Output: {output_lines} lines, {output_chars} characters")
                    
                    # Check for significant truncation
                    line_retention = (output_lines / input_lines) * 100 if input_lines > 0 else 0
                    char_retention = (output_chars / input_chars) * 100 if input_chars > 0 else 0
                    
                    if line_retention < 90 or char_retention < 85:
                        print(f"      ⚠️  POTENTIAL TRUNCATION DETECTED!")
                        print(f"      📉 Line retention: {line_retention:.1f}%, Char retention: {char_retention:.1f}%")
                        
                        # If significant truncation detected, fall back to raw logs
                        # Check BOTH line and character retention for fallback decision
                        if line_retention < 50 or char_retention < 60:
                            print(f"      🔄 Severe truncation detected (line: {line_retention:.1f}%, char: {char_retention:.1f}%). Falling back to raw logs.")
                            return raw_logs
                    
                    print(f"✅ KnowledgeEngine successfully processed content.")
                    return cleaned_content
                else:
                    print(f"      ⚠️  KnowledgeEngine returned empty content on attempt {attempt + 1}.")
            
            except Exception as e:
                print(f"      ❌ KnowledgeEngine LLM call failed on attempt {attempt + 1}: {e}")

            if attempt < self.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

        print("      ❌ All KnowledgeEngine processing attempts failed. Falling back to raw logs.")
        return raw_logs

# REMOVED: Global instance replaced by service container
# Use service_container.get_knowledge_engine() instead 