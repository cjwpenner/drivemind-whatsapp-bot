"""
Data models matching DriveMind Android app structure
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Message:
    """Message in a conversation"""
    content: str
    role: str  # "user" or "assistant"
    timestamp: datetime
    model: Optional[str] = None  # "haiku" or "sonnet"
    tokens: int = 0

    def to_dict(self):
        return {
            "content": self.content,
            "role": self.role,
            "timestamp": self.timestamp,
            "model": self.model,
            "tokens": self.tokens
        }


@dataclass
class Conversation:
    """Conversation with message history"""
    id: Optional[str] = None
    user_id: str = ""  # WhatsApp phone number for WhatsApp bot
    title: str = "WhatsApp Conversation"
    created_at: datetime = None
    updated_at: datetime = None
    is_active: bool = True
    token_count: int = 0
    messages: List[Message] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.messages is None:
            self.messages = []

    def to_dict(self):
        return {
            "userId": self.user_id,
            "title": self.title,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "isActive": self.is_active,
            "tokenCount": self.token_count,
            "messages": [msg.to_dict() for msg in self.messages]
        }


class ModelType:
    """Model type constants"""
    CLAUDE = "claude"
    OPENAI = "openai"


class ClaudeModel:
    """Claude model options"""
    HAIKU = {
        "id": "claude-haiku-4-5",
        "displayName": "Claude 4.5 Haiku",
        "contextWindow": 200000,
        "maxOutput": 8192
    }

    SONNET = {
        "id": "claude-sonnet-4-5",
        "displayName": "Claude 4.5 Sonnet",
        "contextWindow": 200000,
        "maxOutput": 8192
    }


class OpenAIModel:
    """OpenAI model options"""
    GPT4O_MINI = {
        "id": "gpt-4o-mini",
        "displayName": "GPT-4o Mini",
        "contextWindow": 128000,
        "maxOutput": 16384
    }

    GPT4O = {
        "id": "gpt-4o",
        "displayName": "GPT-4o",
        "contextWindow": 128000,
        "maxOutput": 16384
    }
