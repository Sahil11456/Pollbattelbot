def generate_progress_bar(percentage: float, length: int = 10) -> str:
    """Generates an ASCII/Unicode visual progress bar."""
    filled_length = int(round(length * percentage / 100))
    bar = "█" * filled_length + "░" * (length - filled_length)
    return f"[{bar}] {percentage:.1f}%"
