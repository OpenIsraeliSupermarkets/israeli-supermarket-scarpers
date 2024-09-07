
import re

def is_valid_chain_name(input_string):
    # Regular expression pattern to match only letters (a-z, case insensitive) and hyphens (-)
    pattern = r'^[a-zA-Z-]+$'
    
    # Use re.match to check if the entire string matches the pattern
    return bool(re.match(pattern, input_string))
    