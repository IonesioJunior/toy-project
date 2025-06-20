from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, timezone
from typing import List, Optional, Literal
from uuid import UUID, uuid4


class ChatMessage(BaseModel):
    """Single chat message."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    id: UUID = Field(default_factory=uuid4)
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(BaseModel):
    """Chat request from user."""
    
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response."""
    
    message: str
    session_id: str


class ChatSession(BaseModel):
    """Chat session with message history."""
    
    session_id: str
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_message(self, role: Literal["user", "assistant"], content: str) -> None:
        """Add message to history maintaining max length."""
        message = ChatMessage(role=role, content=content)
        self.messages.append(message)
        self.last_accessed = datetime.now(timezone.utc)
        
        # Keep only last max_history_length messages
        from src.core.config import get_settings
        settings = get_settings()
        if len(self.messages) > settings.max_history_length:
            self.messages = self.messages[-settings.max_history_length:]
    
    def get_openai_messages(self) -> List[dict]:
        """Convert messages to OpenAI format."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages
        ]