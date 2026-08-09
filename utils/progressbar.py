def draw_progress_bar(percentage: float, total_votes: int, width: int = 10) -> str:
    """
    Generates a highly polished aesthetic visual progress bar for poll votes.
    
    Args:
        percentage (float): The percentage ratio (0-100).
        total_votes (int): Number of votes for this option.
        width (int): Character block length. Defaults to 10.
        
    Returns:
        str: Custom progress bar block string with ratio, e.g. "████░░░░░░ 40.0% (4 votes)"
    """
    filled_length = int(round(width * percentage / 100))
    # Elegant unicode blocks: filled '█', empty '░'
    bar = '█' * filled_length + '░' * (width - filled_length)
    
    return f"`{bar}` **{percentage:.1f}%** ({total_votes} {'vote' if total_votes == 1 else 'votes'})"

def draw_battle_bar(votes_a: int, votes_b: int, width: int = 15) -> str:
    """
    Draws a head-to-head battle bar representing option A vs option B.
    
    Returns:
        str: e.g. "🔥 ███████░░░░░░░░ 🚀"
    """
    total = votes_a + votes_b
    if total == 0:
        half = width // 2
        return "`" + "░" * width + "`"
    
    filled_a = int(round(width * votes_a / total))
    filled_b = width - filled_a
    
    bar_a = '█' * filled_a
    bar_b = '░' * filled_b
    return f"`{bar_a}{bar_b}`"
