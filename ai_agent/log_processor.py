"""Log processing and character parsing functionality

Enhanced Character Dialogue Parser:

This module now handles the advanced gamemaster format for character dialogue in mission logs:

1. Format: characterName@AccountName: [Actual Character] content
   - Extracts the "Actual Character" name from brackets when present
   - Falls back to characterName before @ when no brackets
   - Applies character name corrections from CHARACTER_CORRECTIONS

2. Action vs Dialogue Detection:
   - Lines with * or ** are treated as actions
   - Lines ending with "> >" are emotes
   - Common action verbs are automatically detected and wrapped in *asterisks*
   - Regular speech is treated as dialogue

3. Continuation Lines:
   - Lines from same character@account without new speaker designation
   - Indented lines or lines that don't end with punctuation
   - Short phrases (3 words or less) are treated as continuations

4. Enhanced Processing:
   - Character name corrections applied throughout
   - Text corrections for typos and standardization
   - Proper formatting for actions vs dialogue
   - Maintains speaker context across continuation lines
"""

import re
from models import CHARACTER_CORRECTIONS
from typing import List, Tuple, Dict

SHIP_NAMES = [
    'stardancer', 'adagio', 'pilgrim', 'protector', 'manta', 'sentinel', 
    'caelian', 'gigantes', 'banshee'
]

# Log indicators for query detection
LOG_INDICATORS = [
    'log', 'logs', 'mission log', 'ship log', 'stardancer log', 
    'captain log', 'personal log', 'stardate', 'entry',
    'what happened', 'events', 'mission report', 'incident report',
    'summarize', 'summary', 'recap', 'tell me what',
    'last mission', 'recent mission', 'latest log',
    'captain\'s log', 'first officer\'s log',
    'expedition', 'away mission', 'away team',
    'event log', 'event logs', 'incident', 'incident log',
    'event report', 'occurrence', 'happening',
    # Ship-specific log patterns
    'adagio log', 'pilgrim', 'stardancer log', 'protector log',
    'manta ', 'sentinel', 'caelian','gigantes', 'banshee','adagio'
    # Date-based patterns
    'retrieve', 'show me', 'get the log', 'find the log',
    # Named incidents
    'incident log', 'crisis log', 'affair log', 'operation log'
]

def is_log_query(query: str) -> bool:
    """Determine if the query is asking about logs"""
    query_lower = query.lower()
    return any(indicator in query_lower for indicator in LOG_INDICATORS)

def is_ship_log_title(title: str) -> bool:
    """Enhanced ship log title detection supporting multiple formats:
    - Ship Name Date
    - Date Ship Name Log  
    - Date Ship Name
    - Ship Name Date Log
    - Something like 'The Anevian Incident' Log
    """
    title_lower = title.lower().strip()
    
    # Basic log patterns for any ship name
    for ship in SHIP_NAMES:
        ship_lower = ship.lower()
        
        # Pattern 1: Ship Name Date (e.g., "Adagio 2024/01/06")
        date_patterns = [
            f"^{ship_lower}\\s+\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}",  # ship 2024/01/06
            f"^{ship_lower}\\s+\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}",   # ship 1/6/2024
            f"^{ship_lower}\\s+\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}",   # ship 2024-01-06
            f"^{ship_lower}\\s+\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}",   # ship 1-6-2024
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, title_lower):
                return True
        
        # Pattern 2: Date Ship Name (e.g., "2024/01/06 Adagio")
        date_ship_patterns = [
            f"^\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}\\s+{ship_lower}",   # 2024/01/06 ship
            f"^\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}\\s+{ship_lower}",   # 1/6/2024 ship
            f"^\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}\\s+{ship_lower}",   # 2024-01-06 ship
            f"^\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}\\s+{ship_lower}",   # 1-6-2024 ship
        ]
        
        for pattern in date_ship_patterns:
            if re.match(pattern, title_lower):
                return True
        
        # Pattern 3: Ship Name Date Log (e.g., "Adagio 2024/01/06 Log")
        date_log_patterns = [
            f"^{ship_lower}\\s+\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}\\s+log",
            f"^{ship_lower}\\s+\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}\\s+log",
            f"^{ship_lower}\\s+\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}\\s+log",
            f"^{ship_lower}\\s+\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}\\s+log",
        ]
        
        for pattern in date_log_patterns:
            if re.match(pattern, title_lower):
                return True
        
        # Pattern 4: Date Ship Name Log (e.g., "2024/01/06 Adagio Log") 
        date_ship_log_patterns = [
            f"^\\d{{4}}/\\d{{1,2}}/\\d{{1,2}}\\s+{ship_lower}\\s+log",
            f"^\\d{{1,2}}/\\d{{1,2}}/\\d{{4}}\\s+{ship_lower}\\s+log",
            f"^\\d{{4}}-\\d{{1,2}}-\\d{{1,2}}\\s+{ship_lower}\\s+log",
            f"^\\d{{1,2}}-\\d{{1,2}}-\\d{{4}}\\s+{ship_lower}\\s+log",
        ]
        
        for pattern in date_ship_log_patterns:
            if re.match(pattern, title_lower):
                return True
    
    # Pattern 5: Named incidents/events ending with "Log" (e.g., "The Anevian Incident Log")
    if title_lower.endswith(' log') and len(title_lower) > 4:
        # Check if it contains words that suggest it's an event/incident
        event_indicators = ['incident', 'event', 'mission', 'encounter', 'crisis', 'affair', 'operation']
        if any(indicator in title_lower for indicator in event_indicators):
            return True
        
        # Check if it contains "the" at the beginning, suggesting a named event
        if title_lower.startswith('the ') and len(title_lower.split()) >= 3:
            return True
    
    # Pattern 6: Any title with ship name and "log" anywhere
    for ship in SHIP_NAMES:
        ship_lower = ship.lower()
        if ship_lower in title_lower and 'log' in title_lower:
            return True
    
    return False


def correct_character_name(name: str) -> str:
    """Apply character corrections and rank/title fixes"""
    if not name:
        return name
        
    name_lower = name.lower().strip()
    
    # Direct lookup first
    if name_lower in CHARACTER_CORRECTIONS:
        return CHARACTER_CORRECTIONS[name_lower]
    
    # Check for partial matches (last name only)
    for key, corrected in CHARACTER_CORRECTIONS.items():
        if ' ' in key:  # Full name entries
            last_name = key.split()[-1]
            if name_lower == last_name:
                return corrected
    
    # If no correction found, return original with proper capitalization
    return ' '.join(word.capitalize() for word in name.split())

def apply_text_corrections(text: str) -> str:
    """Apply character name corrections to free text"""
    corrected_text = text
    
    # Replace character references in text
    for incorrect, correct in CHARACTER_CORRECTIONS.items():
        # Case-insensitive replacement while preserving case
        pattern = re.compile(re.escape(incorrect), re.IGNORECASE)
        corrected_text = pattern.sub(correct, corrected_text)
    
    return corrected_text

def parse_log_characters(log_content: str) -> str:
    """Parse log content to identify speaking characters and add context with rank/title corrections
    
    Enhanced to handle new gamemaster format:
    - characterName@AccountName: [Actual Character] - Extract actual character from brackets
    - If no [Actual Character], use characterName before @
    - Things with * or in ** ** are actions, not dialogue
    - Lines ending with > > or continuation from same character@account are follow ups with dialogue having \"
    """
    
    # First apply the new enhanced character dialogue parsing
    enhanced_content = parse_character_dialogue(log_content)
    
    lines = enhanced_content.split('\n')
    parsed_lines = []
    current_speaker = None
    
    for line in lines:
        original_line = line
        
        # Check for playername.tag pattern followed by [<Name>] or direct speech
        playername_pattern = r'^([^@:]+)@([^:]+):'
        playername_match = re.match(playername_pattern, line)
        
        if playername_match:
            player_name = playername_match.group(1)
            tag = playername_match.group(2)
            
            # Check if this is @Captain_Riens (game master)
            if '@Captain_Rien' in line:
                # Mark as Game Master
                line = line.replace('@Captain_Rien:', '[GAME MASTER]:')
                current_speaker = "Game Master"
            else:
                # Look for [<Character Name>] pattern in the rest of the line
                remaining_line = line[playername_match.end():]
                character_pattern = r'\[([^\]]+)\]'
                character_match = re.search(character_pattern, remaining_line)
                
                if character_match:
                    character_name = correct_character_name(character_match.group(1))
                    current_speaker = character_name
                    # Replace the line to show character clearly
                    clean_dialogue = remaining_line.replace(character_match.group(0), '').strip()
                    clean_dialogue = apply_text_corrections(clean_dialogue)
                    line = f"[{character_name}]: {clean_dialogue}"
                else:
                    # No character designation, use corrected player name or last speaker
                    if current_speaker:
                        clean_dialogue = apply_text_corrections(remaining_line.strip())
                        line = f"[{current_speaker}]: {clean_dialogue}"
                    else:
                        corrected_player = correct_character_name(player_name)
                        current_speaker = corrected_player
                        clean_dialogue = apply_text_corrections(remaining_line.strip())
                        line = f"[{corrected_player}]: {clean_dialogue}"
        
        # Check for standalone [<Character Name>] pattern
        elif re.match(r'^\[([^\]]+)\]:', line):
            character_match = re.match(r'^\[([^\]]+)\]:', line)
            corrected_name = correct_character_name(character_match.group(1))
            current_speaker = corrected_name
            # Update the line with corrected name
            rest_of_line = line[character_match.end():].strip()
            rest_of_line = apply_text_corrections(rest_of_line)
            line = f"[{corrected_name}]: {rest_of_line}"
        
        # If no speaker designation but we have a current speaker, and line looks like dialogue
        elif current_speaker and line.strip() and not line.startswith(('*', '/', '#', '=', '-')):
            # Check if it's a continuation of speech (starts with quote or lowercase)
            stripped = line.strip()
            if (stripped.startswith('"') or 
                stripped.startswith("'") or 
                (stripped and stripped[0].islower()) or
                stripped.startswith('*')):
                corrected_line = apply_text_corrections(line)
                line = f"[{current_speaker}]: {corrected_line}"
        
        # Apply corrections to any remaining text
        else:
            line = apply_text_corrections(line)
        
        parsed_lines.append(line)
    
    return '\n'.join(parsed_lines)

def parse_character_dialogue(log_content: str) -> str:
    """
    Parse mission log content to extract proper character names and format dialogue/actions.
    
    Rules:
    - characterName@AccountName: [Actual Character] - Extract actual character from brackets
    - If no [Actual Character], use characterName before @
    - Things with * or in ** ** are actions, not dialogue
    - Lines ending with > > or continuation from same character@account are emotes
    """
    if not log_content:
        return log_content
    
    lines = log_content.split('\n')
    processed_lines = []
    last_speaker = None
    last_account = None
    
    # Pattern to match characterName@AccountName: format
    speaker_pattern = r'^([^@\s]+)@([^:\s]+):\s*(.*)$'
    # Pattern to match [Actual Character] in the content
    actual_character_pattern = r'^\[([^\]]+)\]\s*(.*)$'
    
    for line in lines:
        # Skip empty lines and preserve them
        if not line.strip():
            processed_lines.append(line)
            continue
        
        # Check if this line matches the character@account: format
        speaker_match = re.match(speaker_pattern, line.strip())
        
        if speaker_match:
            character_name = speaker_match.group(1)
            account_name = speaker_match.group(2)
            content = speaker_match.group(3)
            
            # Check if content starts with [Actual Character]
            actual_char_match = re.match(actual_character_pattern, content)
            
            if actual_char_match:
                # Use the actual character name from brackets
                actual_speaker = correct_character_name(actual_char_match.group(1))
                remaining_content = actual_char_match.group(2)
            else:
                # Use the character name before @
                actual_speaker = correct_character_name(character_name)
                remaining_content = content
            
            # Apply text corrections to content
            remaining_content = apply_text_corrections(remaining_content)
            
            # Update tracking for continuation lines
            last_speaker = actual_speaker
            last_account = account_name
            
            # Process the content to identify actions vs dialogue
            formatted_content = format_content_type(remaining_content)
            
            # Create the formatted line
            if formatted_content:
                processed_lines.append(f"{actual_speaker}: {formatted_content}")
            else:
                processed_lines.append(f"{actual_speaker}:")
        
        elif line.strip().endswith('> >'):
            # This is an emote line, likely a continuation
            emote_content = line.strip()[:-3].strip()  # Remove > >
            if last_speaker:
                formatted_emote = format_content_type(emote_content, is_emote=True)
                processed_lines.append(f"{last_speaker}: {formatted_emote}")
            else:
                processed_lines.append(line)
        
        elif last_speaker and last_account and not re.match(speaker_pattern, line.strip()):
            # This might be a continuation line from the same speaker
            # Check if it looks like a continuation (starts with space, indented, or doesn't end with period)
            stripped_line = line.strip()
            is_continuation = (
                line.startswith(' ') or 
                line.startswith('\t') or 
                not stripped_line.endswith('.') or
                not stripped_line.endswith('!') or
                not stripped_line.endswith('?') or
                len(stripped_line.split()) <= 3  # Short phrases are likely continuations
            )
            
            if is_continuation and stripped_line:
                # Apply text corrections before formatting
                corrected_content = apply_text_corrections(stripped_line)
                formatted_content = format_content_type(corrected_content)
                if formatted_content:
                    processed_lines.append(f"{last_speaker}: {formatted_content}")
                else:
                    processed_lines.append(line)
            else:
                # Not a continuation, reset speaker tracking
                last_speaker = None
                last_account = None
                processed_lines.append(line)
        
        else:
            # Regular line, not matching any patterns
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def format_content_type(content: str, is_emote: bool = False) -> str:
    """
    Format content to distinguish between actions and dialogue.
    
    Rules:
    - Content starting with * or in ** ** brackets are actions
    - Everything else is dialogue
    - Emotes are formatted as actions
    """
    if not content.strip():
        return content
    
    content = content.strip()
    
    # Check if it's already in action format (starts with * or wrapped in **)
    if content.startswith('*') or (content.startswith('**') and content.endswith('**')):
        return f"*{content.strip('*').strip()}*"  # Normalize to single asterisks
    
    # Check if it's an emote
    if is_emote:
        return f"*{content}*"
    
    # Check for common action verbs and patterns
    action_patterns = [
        r'^(walks?|runs?|sits?|stands?|looks?|turns?|moves?|enters?|exits?|approaches?)',
        r'^(nods?|smiles?|frowns?|laughs?|sighs?|shrugs?)',
        r'^(grabs?|picks? up|puts? down|places?|holds?|drops?)',
        r'^(points?|gestures?|waves?|raises?|lowers?)',
        r'^\*.*\*$',  # Already wrapped in asterisks
        r'^.*\btaps?\b.*',
        r'^.*\bpresses?\b.*',
        r'^.*\bactivates?\b.*'
    ]
    
    # Check if content matches action patterns
    for pattern in action_patterns:
        if re.match(pattern, content.lower()):
            # Don't double-wrap if already wrapped
            if content.startswith('*') and content.endswith('*'):
                return content
            return f"*{content}*"
    
    # Check for action indicators within the content
    if any(indicator in content.lower() for indicator in ['*action*', '*emote*', '*does*', '*performs*']):
        return f"*{content}*"
    
    # Otherwise, treat as dialogue
    return content 