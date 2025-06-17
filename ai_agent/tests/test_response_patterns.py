#!/usr/bin/env python3

"""
Test script for response-to-Elsie pattern detection
"""

import sys
import os
import re

# Add the ai_agent directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_agent'))

def test_response_patterns():
    """Test the response patterns that should be detected as responses to Elsie"""
    
    print("🧪 TESTING RESPONSE-TO-ELSIE PATTERN DETECTION")
    print("=" * 50)
    
    # Response patterns that should be detected as responses TO Elsie
    elsie_response_patterns = [
        r'\b(?:yes|yeah|yep|yup|uh-huh|mhm),?\s',  # Affirmative responses
        r'\b(?:no|nope|nah|uh-uh),?\s',  # Negative responses
        r'\bthat\'?s\s+(?:right|correct|true|wrong|false|not\s+right)',  # Confirmation/denial
        r'\bi\s+(?:think|believe|guess|suppose)',  # Opinion responses
        r'\bmaybe|perhaps|possibly|probably',  # Uncertain responses
        r'\bwell,?\s',  # Thoughtful responses
        r'\bactually,?\s',  # Clarifying responses
        r'\bof\s+course',  # Obvious responses
        r'\babsolutely|definitely|certainly',  # Strong affirmatives
        r'\bnot\s+really|not\s+exactly|not\s+quite',  # Qualified negatives
    ]
    
    # Test cases that should be detected as responses to Elsie
    test_cases = [
        # Simple affirmative/negative responses
        '[Maeve] "Yes, that is correct."',
        '[Tavi] "No, that\'s not right."',
        '[Zarina] "Yeah, I think so."',
        '[Maeve] "Nope, definitely not."',
        
        # Responses with character mentions (should still be responses to Elsie)
        '[Maeve] "Yes, Tavi is my best friend."',
        '[Tavi] "No, Zarina wasn\'t there."',
        '[Zarina] "That\'s right, Maeve did say that."',
        
        # Thoughtful responses
        '[Maeve] "Well, I suppose that could work."',
        '[Tavi] "Actually, I think you\'re right."',
        '[Zarina] "Maybe, but I\'m not sure."',
        
        # Strong responses
        '[Maeve] "Absolutely! That\'s perfect."',
        '[Tavi] "Of course, that makes sense."',
        '[Zarina] "Definitely not what I expected."',
        
        # Qualified responses
        '[Maeve] "Not really, but close."',
        '[Tavi] "Not exactly what I meant."',
        '[Zarina] "Not quite right, but good try."',
    ]
    
    print("\n✅ TESTING RESPONSE-TO-ELSIE PATTERNS:")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i:2d}. Testing: {test_case}")
        
        # Extract the dialogue part (after the bracket)
        dialogue_match = re.search(r'\[([^\]]+)\]\s*["\']([^"\']+)["\']', test_case)
        if dialogue_match:
            speaker = dialogue_match.group(1)
            dialogue = dialogue_match.group(2)
            
            # Debug output for case #7
            if "That's right" in dialogue:
                print(f"    🔍 DEBUG: dialogue = '{dialogue}'")
            
            # Test each pattern
            matched_patterns = []
            for pattern in elsie_response_patterns:
                if re.search(pattern, dialogue, re.IGNORECASE):
                    matched_patterns.append(pattern)
                    # Debug output for case #7
                    if "That's right" in dialogue:
                        print(f"    🔍 DEBUG: Pattern '{pattern}' MATCHED!")
            
            if matched_patterns:
                print(f"    ✅ DETECTED as response to Elsie: {matched_patterns[0]}")
            else:
                print(f"    ❌ NOT DETECTED as response to Elsie")
                # Debug output for case #7
                if "That's right" in dialogue:
                    print(f"    🔍 DEBUG: No patterns matched for '{dialogue}'")
        else:
            print(f"    ⚠️  Could not parse test case")
    
    print("\n" + "=" * 50)
    print("✅ RESPONSE PATTERN TESTING COMPLETE")

if __name__ == "__main__":
    test_response_patterns() 