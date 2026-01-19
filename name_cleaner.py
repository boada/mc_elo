"""
Clean player names: normalize casing and remove parentheticals.
"""
import re


def clean_player_name(name: str) -> str:
    """
    Clean a player name:
    - Remove parenthetical comments like "(rolling ones)"
    - Title case (capitalize first letter of each word)
    - Handle special cases like "Mc", "O'", etc.
    
    Args:
        name: Raw player name from BCP
        
    Returns:
        Cleaned name
    """
    # Remove anything in parentheses
    name = re.sub(r'\s*\([^)]*\)', '', name)
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    # Title case
    name = name.title()
    
    # Handle special cases
    # "Mcdonald" -> "McDonald", "O'brien" -> "O'Brien"
    name = re.sub(r'\bMc([a-z])', lambda m: 'Mc' + m.group(1).upper(), name)
    name = re.sub(r"\bO'([a-z])", lambda m: "O'" + m.group(1).upper(), name)
    
    return name


if __name__ == "__main__":
    # Test cases
    test_names = [
        "caelan (rolling ones) Fulkerson",
        "GREGORY BURBAN",
        "Mason Mutz",
        "kevin MORRISON",
        "James O'brien",
        "John McDonald"
    ]
    
    print("Name cleaning tests:")
    for name in test_names:
        cleaned = clean_player_name(name)
        print(f"  {name:45} -> {cleaned}")
