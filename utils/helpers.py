import uuid

def generate_short_id() -> str:
    """Generates a unique 8-character string ID."""
    return str(uuid.uuid4())[:8]

def format_number(num: int) -> str:
    """Formats large numbers into compact human-readable representation."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)
