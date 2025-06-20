"""Common exception classes for shared libraries."""


class BaseApplicationError(Exception):
    """Base exception class for application errors."""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ValidationError(BaseApplicationError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.field = field


class AuthenticationError(BaseApplicationError):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, error_code="AUTH_ERROR")


class AuthorizationError(BaseApplicationError):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Authorization failed"):
        super().__init__(message, error_code="AUTHZ_ERROR")


class NotFoundError(BaseApplicationError):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource: str, identifier: str = None):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, error_code="NOT_FOUND")
        self.resource = resource
        self.identifier = identifier


class ConfigurationError(BaseApplicationError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str):
        super().__init__(message, error_code="CONFIG_ERROR")


class ExternalServiceError(BaseApplicationError):
    """Raised when an external service call fails."""
    
    def __init__(self, service: str, message: str):
        full_message = f"External service error ({service}): {message}"
        super().__init__(full_message, error_code="EXTERNAL_SERVICE_ERROR")
        self.service = service