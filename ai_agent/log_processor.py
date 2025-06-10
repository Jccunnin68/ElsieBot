"""Log processing and character parsing functionality"""

import re
from config import LOG_INDICATORS, SHIP_NAMES
from models import CHARACTER_CORRECTIONS

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

def is_ship_log_page(page_title: str) -> bool:
    """Legacy function - now uses enhanced is_ship_log_title"""
    return is_ship_log_title(page_title)

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
    """Parse log content to identify speaking characters and add context with rank/title corrections"""
    
    lines = log_content.split('\n')
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