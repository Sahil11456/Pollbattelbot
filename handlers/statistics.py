import os
import logging
from telegram import Update
from telegram.ext import ContextTypes
import database

logger = logging.getLogger("bot.handlers.statistics")

async def statistics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Compiles global database statistics and generates a visual report."""
    user = update.effective_user
    if not user or not update.message:
        return

    stats = await database.get_system_stats()
    total_users = stats.get("total_users", 0)
    total_polls = stats.get("total_polls", 0)
    total_votes = stats.get("total_votes", 0)
    active_polls = stats.get("active_polls", 0)
    closed_polls = max(0, total_polls - active_polls)

    avg_votes = (total_votes / total_polls) if total_polls > 0 else 0

    stats_report_text = (
        f"📊 **Global Platform Statistics**\n"
        f"—————————————————————\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"🟢 **Active Polls:** `{active_polls}`\n"
        f"🔴 **Closed Polls:** `{closed_polls}`\n"
        f"🗳️ **Total Votes Cast:** `{total_votes}`\n"
        f"📈 **Average Votes per Poll:** `{avg_votes:.1f}`\n\n"
    )

    # Attempt to render a visual chart using matplotlib
    os.makedirs("assets", exist_ok=True)
    chart_path = "assets/stats_graph.png"
    chart_generated = False
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        categories = ['Users', 'Active Polls', 'Closed Polls', 'Total Votes']
        values = [total_users, active_polls, closed_polls, total_votes]

        plt.figure(figsize=(6, 4))
        plt.bar(categories, values, color=['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'])
        plt.title("Platform Activity Summary", fontsize=12, fontweight='bold', pad=15)
        plt.ylabel("Count")
        plt.grid(axis='y', linestyle='--', alpha=0.5)
        plt.tight_layout()
        
        plt.savefig(chart_path, dpi=150)
        plt.close()
        chart_generated = True
    except Exception as e:
        logger.warning(f"Could not generate visual chart: {e}")

    if chart_generated and os.path.exists(chart_path):
        with open(chart_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=stats_report_text,
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text(
            text=stats_report_text,
            parse_mode="Markdown"
        )
