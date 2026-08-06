from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    device_signature: str
    is_banned: bool = False
    is_admin: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class PollOption:
    option_id: int
    poll_id: str
    option_text: str
    vote_count: int = 0
    is_correct: bool = False  # For quiz polls

@dataclass
class Poll:
    poll_id: str
    creator_id: int
    creator_name: str
    question: str
    poll_type: str  # public, private, anonymous, quiz
    is_multiple: bool
    is_closed: bool
    allow_vote_change: bool
    expiry_time: Optional[str]
    created_at: str
    total_votes: int = 0
    winner_option_id: Optional[int] = None
    target_channel_id: Optional[int] = None

@dataclass
class Vote:
    vote_id: int
    poll_id: str
    user_id: int
    option_id: int
    voted_at: str

@dataclass
class Channel:
    channel_id: int
    title: str
    username: Optional[str]
    force_join: bool
    added_at: str

@dataclass
class Favorite:
    user_id: int
    poll_id: str
    added_at: str

@dataclass
class ErrorLog:
    id: int
    user_id: Optional[int]
    error_message: str
    traceback_str: str
    created_at: str
