import time
import hashlib
from typing import Dict
from telegram import Update
import config

class AntiSpamManager:
    def __init__(self, rate_limit_seconds: int = 2, max_requests: int = 5):
        self.rate_limit_seconds = rate_limit_seconds
        self.max_requests = max_requests
        self.user_requests: Dict[int, list] = {}

    def is_rate_limited(self, user_id: int) -> bool:
        now = time.time()
        if user_id not in self.user_requests:
            self.user_requests[user_id] = [now]
            return False

        timestamps = [t for t in self.user_requests[user_id] if now - t < self.rate_limit_seconds]
        timestamps.append(now)
        self.user_requests[user_id] = timestamps

        return len(timestamps) > self.max_requests

    def generate_device_signature(self, update: Update) -> str:
        """
        Generates a non-IP device signature derived from Telegram User attributes
        (user_id, language_code, is_premium) to protect against vote manipulation bots.
        """
        user = update.effective_user
        if not user:
            return "unknown_device"
        raw_sig = f"{user.id}:{user.language_code}:{getattr(user, 'is_premium', False)}"
        return hashlib.sha256(raw_sig.encode()).hexdigest()[:16]

    def validate_callback(self, callback_data: str) -> bool:
        """Validates string callback structure to prevent callback injection attacks."""
        if not callback_data or len(callback_data) > 128:
            return False
        allowed_prefixes = ("vote:", "refresh:", "stats:", "share:", "fav:", "prev:", "next:", "close:", "join_check:")
        return callback_data.startswith(allowed_prefixes)

anti_spam = AntiSpamManager()
