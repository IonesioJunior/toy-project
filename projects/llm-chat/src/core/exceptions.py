class ChatException(Exception):
    """Base exception for chat-related errors."""
    pass


class SessionNotFoundException(ChatException):
    """Raised when a session is not found."""
    pass


class OpenAIServiceException(ChatException):
    """Raised when OpenAI service encounters an error."""
    pass


class ValidationException(ChatException):
    """Raised when input validation fails."""
    pass