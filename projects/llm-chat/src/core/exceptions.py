class ChatError(Exception):
    """Base exception for chat-related errors."""

    pass


class SessionNotFoundError(ChatError):
    """Raised when a session is not found."""

    pass


class OpenAIServiceError(ChatError):
    """Raised when OpenAI service encounters an error."""

    pass


class ValidationError(ChatError):
    """Raised when input validation fails."""

    pass


class ExternalServiceError(ChatError):
    """Raised when an external service (like File Manager API) fails."""

    pass
