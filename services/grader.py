import re

def normalize_answers(input_str: str) -> str:
    """
    Normalizes answer strings.
    Supported formats:
    1. "ABCD..." (letters only)
    2. "1A 2b 3C..." (indexed)
    
    Removes spaces, digits (if mixed), and converts to uppercase.
    """
    if not input_str:
        return ""
        
    s = input_str.upper()
    
    # Check if it looks like indexed format (contains digits)
    if any(char.isdigit() for char in s):
        # Regex to find letter following a digit (ignoring logic for now, just extract all letters)
        # Actually spec says: "extract letters after digits"
        # 1A2a3c -> Aac -> AAC
        # Regex: find all [A-Z]
        # Wait, if user types "12*1A2B", the "12*" is removed before calling this.
        # So input is "1A2B".
        # We just want the letters.
        # BUT, if the user types "1. A  2. B", we want A, B.
        # Simple approach: remove all non-letters? 
        # CAREFUL: What if the valid answer is "1A" (meaning 'A' for q1)?
        # If I just strip non-letters, "1A2B" -> "AB". Correct.
        # "A B C D" -> "ABCD". Correct.
        # "1-A, 2-B" -> "AB". Correct.
        
        # Is there any ambiguity? 
        # If I have valid answer key "A" (1 question).
        # User input "1 A". -> "A". Correct.
        
        # So simply stripping everything except A-Z seems robust for the spec "ABCD..." and "1A2a...".
        # Spec says: "index letter pairs... extract letters after digits"
        return "".join(c for c in s if c.isalpha())
    else:
        # Letters only format, possibly with spaces
        return "".join(c for c in s if c.isalpha())

def grade_submission(normalized_submission: str, answer_key: str):
    """
    Compares normalized submission against answer key.
    Returns (correct_count, wrong_count, percentage)
    Assuming length validation is done before calling this?
    No, let's just grade up to the length of the answer key or submission, whichever is shorter?
    Spec says: "length must equal N". So we assume caller checks length.
    """
    total = len(answer_key)
    if total == 0:
        return 0, 0, 0.0
        
    correct = 0
    # Iterate over both
    for sub_char, key_char in zip(normalized_submission, answer_key):
        if sub_char == key_char:
            correct += 1
            
    wrong = total - correct # Assuming full length submission
    percent = (correct / total) * 100.0
    
    return correct, wrong, round(percent, 2)
