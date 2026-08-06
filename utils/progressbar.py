def draw_progress_bar(percentage: float, total_votes: int, width: int = 10) -> str:
    filled_length = int(round(width * percentage / 100))
    bar = '█' * filled_length + '░' * (width - filled_length)
    return f"`{bar}` **{percentage:.1f}%** ({total_votes} {'vote' if total_votes == 1 else 'votes'})"

def draw_battle_bar(votes_a: int, votes_b: int, width: int = 15) -> str:
    total = votes_a + votes_b
    if total == 0:
        return "`" + "░" * width + "`"
    filled_a = int(round(width * votes_a / total))
    filled_b = width - filled_a
    return f"`{'█' * filled_a}{'░' * filled_b}`"
