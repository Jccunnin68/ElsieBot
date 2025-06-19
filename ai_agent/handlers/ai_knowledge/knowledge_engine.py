"""
Knowledge Engine - LLM-Powered Log Processor
===========================================

This engine's sole responsibility is to clean raw Discord roleplay logs
using an LLM. It takes messy, multi-user chat data and transforms it into
a clean, third-person sequence of events suitable for summarization.
"""

import time
from typing import List
import google.generativeai as genai
from config import GEMMA_API_KEY
from .log_patterns import SHIP_SPECIFIC_CHARACTER_CORRECTIONS, FALLBACK_CHARACTER_CORRECTIONS, FLEET_SHIP_NAMES

class KnowledgeEngine:
    """A simplified engine for processing log data with an LLM."""

    LLM_MODEL_NAME = 'gemini-2.0-flash-lite'
    MAX_RETRIES = 3

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
        """Creates the prompt to clean up raw Discord logs."""
        character_corrections = self._create_character_corrections_text()
        
        # Calculate line count outside f-string to avoid backslash issue
        line_count = logs.count('\n') + 1
        char_count = len(logs)
        
        return f"""
You are a log cleaning assistant. Your task is to process and clean raw game logs while preserving ALL content. 

⚠️ ABSOLUTELY CRITICAL: You MUST output EVERY SINGLE LINE from the input. DO NOT SKIP, TRUNCATE, OR SUMMARIZE ANY CONTENT.

🔢 INPUT REQUIREMENTS:
- Input has {line_count} lines and {char_count} characters
- Your output MUST have exactly {line_count} lines 
- Your output should have approximately {char_count} characters (after cleaning metadata)

🚫 FORBIDDEN ACTIONS:
- Do NOT stop processing early due to length
- Do NOT truncate or cut off content  
- Do NOT summarize multiple lines into one
- Do NOT skip lines because content seems repetitive

**DGM & CHANNEL RULES:**
- DGM Gamemaster Accounts: liorexus, isis, cygnus, illuice, captain_rien, demoncherub, captain_riens
- DOIC Channels: ALL of these contain valid roleplay content. Remove ONLY the channel tags, but keep ALL the text content that follows them:
  * [DOIC] - Main channel with DGM narration and environmental descriptions.
  * [DOIC1], [DOIC2], [DOIC3], etc. - Character dialogue and actions.
  * [Character] - Character dialogue and actions.
  * (OOC) - OOC comments.
  * Filter out Game Master account @names

{character_corrections}

**MANDATORY PROCESSING RULES:**
1. **PRESERVE EVERY LINE:** Process ALL {line_count} lines. Do not stop early or skip lines.
2. **NO TRUNCATION:** If you feel the content is too long, you MUST still process every line. Truncation is NOT allowed.
3. **Extract Actions:** Identify every action taken by a character and rewrite it in a third-person, past-tense format.
4. **Character Names:** Apply the character name corrections above to ensure consistency.
5. **Remove Metadata Only:** Eliminate timestamps, Channel identifiers, and OOC comments, but keep ALL story content.
6. **Preserve Dialogue:** Keep all dialogue within quotation marks.
7. **Maintain Order:** The output must follow the exact chronological order of the original log.
8. **No Summarization:** Your job is ONLY to clean and reformat. Do not combine or compress actions.

**VERIFICATION:** Your output must contain exactly {line_count} lines.

**RAW LOG DATA TO PROCESS (ALL {line_count} LINES MUST BE PROCESSED):**
---
{logs}
---

**Cleaned and Reformatted Log (MUST CONTAIN ALL {line_count} LINES):**
"""

    def _split_logs_into_chunks(self, raw_logs: str, max_chunk_size: int = 400000) -> List[str]:
        """
        Split very large logs into smaller chunks for processing.
        Tries to split at natural boundaries (double newlines).
        """
        if len(raw_logs) <= max_chunk_size:
            return [raw_logs]
        
        chunks = []
        current_chunk = ""
        lines = raw_logs.split('\n')
        
        for line in lines:
            # Check if adding this line would exceed the chunk size
            if len(current_chunk) + len(line) + 1 > max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n' + line
                else:
                    current_chunk = line
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"      📦 Split large log into {len(chunks)} chunks")
        return chunks

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

        # Check input size and warn if it's very large
        input_lines = raw_logs.count('\n') + 1
        input_chars = len(raw_logs)
        print(f"      📊 Input: {input_lines} lines, {input_chars} characters")
        
        # For very large inputs, use chunked processing
        if input_chars > 500000:  # 500K characters
            print(f"      📦 Large input detected ({input_chars} chars). Using chunked processing.")
            return self._process_logs_chunked(raw_logs)
        
        # Process normally for smaller inputs
        return self._process_single_log(raw_logs)

    def _process_single_log(self, raw_logs: str) -> str:
        """Process a single log block."""
        input_lines = raw_logs.count('\n') + 1
        input_chars = len(raw_logs)
        
        prompt = self._create_log_cleaning_prompt(raw_logs)

        for attempt in range(self.MAX_RETRIES):
            try:
                # Configure for maximum output and consistency
                generation_config = genai.types.GenerationConfig(
                    max_output_tokens=1000000,
                    temperature=0.05,  # Very low temperature for maximum consistency
                    candidate_count=1,
                    top_p=0.8,  # Reduce randomness in token selection
                    top_k=20    # Further limit token choices for consistency
                )
                response = self.client.generate_content(prompt, generation_config=generation_config)
                cleaned_content = response.text.strip()
                
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
                    
                    print(f"✅ KnowledgeEngine successfully cleaned single log.")
                    return cleaned_content
                else:
                    print(f"      ⚠️  KnowledgeEngine returned empty content on attempt {attempt + 1}.")
            
            except Exception as e:
                print(f"      ❌ KnowledgeEngine LLM call failed on attempt {attempt + 1}: {e}")

            if attempt < self.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)

        print("      ❌ All KnowledgeEngine processing attempts failed. Falling back to raw logs.")
        return raw_logs
    
    def _process_logs_chunked(self, raw_logs: str) -> str:
        """Process very large logs by splitting into chunks."""
        chunks = self._split_logs_into_chunks(raw_logs)
        processed_chunks = []
        
        for i, chunk in enumerate(chunks):
            print(f"      🔄 Processing chunk {i+1}/{len(chunks)}")
            processed_chunk = self._process_single_log(chunk)
            processed_chunks.append(processed_chunk)
        
        # Combine all processed chunks
        result = '\n'.join(processed_chunks)
        
        # Final verification
        input_lines = raw_logs.count('\n') + 1
        input_chars = len(raw_logs)
        output_lines = result.count('\n') + 1
        output_chars = len(result)
        line_retention = (output_lines / input_lines) * 100 if input_lines > 0 else 0
        char_retention = (output_chars / input_chars) * 100 if input_chars > 0 else 0
        
        print(f"      📊 Chunked processing complete: {line_retention:.1f}% line retention, {char_retention:.1f}% char retention")
        
        if line_retention < 80 or char_retention < 70:
            print(f"      🔄 Chunked processing had low retention (line: {line_retention:.1f}%, char: {char_retention:.1f}%). Falling back to raw logs.")
            return raw_logs
        
        print(f"✅ KnowledgeEngine successfully processed chunked logs.")
        return result

# Singleton instance
_knowledge_engine = None

def get_knowledge_engine() -> KnowledgeEngine:
    """Provides a global singleton instance of the KnowledgeEngine."""
    global _knowledge_engine
    if _knowledge_engine is None:
        _knowledge_engine = KnowledgeEngine()
    return _knowledge_engine 