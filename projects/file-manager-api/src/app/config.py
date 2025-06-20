from pathlib import Path
from typing import Optional, Protocol, Set, Union

from pydantic_settings import BaseSettings
from syft_core import Client
from syft_core.exceptions import SyftBoxException


# Define protocol for syft_client interface
class SyftClientProtocol(Protocol):
    email: str

    def app_data(self, name: str) -> Path: ...
    def makedirs(self, path: Path) -> None: ...
    def to_syft_url(self, file_path: Path) -> str: ...


class Settings(BaseSettings):
    # Environment configuration
    APP_ENV: str = "production"  # production, development, testing

    # File storage configuration
    FILE_STORAGE_PATH: str = "./files"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB default

    # Syft core integration
    SYFT_USER_EMAIL: Optional[str] = None

    # Allowed file types
    ALLOWED_EXTENSIONS: Set[str] = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".pdf",
        ".txt",
        ".doc",
        ".docx",
        ".csv",
        ".xlsx",
        ".xls",
        ".json",
    }

    ALLOWED_MIME_TYPES: Set[str] = {
        # Images
        "image/jpeg",
        "image/png",
        "image/gif",
        # Documents
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        # Spreadsheets
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # Data files
        "application/json",
    }

    # API configuration
    API_PREFIX: str = "/api"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Mock implementation for dev/test
class MockSyftClient:
    """Mock syft_core client for development and testing."""

    def __init__(self, email: str = "dev@test.local"):
        self.email = email
        self._base_path = Path("/tmp/syftbox_mock")
        # Add my_datasite property
        self.my_datasite = self._base_path / "datasites" / self.email
        # Add datasites property to match real Client
        self.datasites = self._base_path / "datasites"

    def app_data(self, name: str) -> Path:
        """Return app data path."""
        return self._base_path / "datasites" / self.email / "app_data" / name

    def makedirs(self, path: Path) -> None:
        """Create directories."""
        path.mkdir(parents=True, exist_ok=True)

    def to_syft_url(self, file_path: Path) -> str:
        """Generate mock syft URL."""
        return f"syft://{self.email}/apis/file_management/storage/{file_path.name}"


settings = Settings()

# Declare syft_client with union type
syft_client: Union[Client, MockSyftClient]

# Initialize based on environment
if settings.APP_ENV == "production":
    # Production: require real syft_core
    try:
        syft_client = Client.load()

        # Create app-specific storage paths
        APP_DATA_PATH = syft_client.app_data("file_management")
        FILE_STORAGE_PATH = APP_DATA_PATH / "storage"
        METADATA_PATH = APP_DATA_PATH / "metadata"

        # Ensure directories exist
        syft_client.makedirs(FILE_STORAGE_PATH)
        syft_client.makedirs(METADATA_PATH)

        # Store user email for syft URL generation
        settings.SYFT_USER_EMAIL = syft_client.email

        print(f"Syft core initialized. Storage path: {FILE_STORAGE_PATH}")
    except SyftBoxException as e:
        raise RuntimeError(
            f"Failed to initialize syft_core: {e}. "
            "SyftBox must be properly configured. "
            "Please run 'syftbox init' or check your configuration."
        )
else:
    # Development/Testing: use mock
    syft_client = MockSyftClient()
    print(f"Running in {settings.APP_ENV} mode with mock syft_core")

    # Set paths based on mock client
    APP_DATA_PATH = syft_client.app_data("file_management")
    FILE_STORAGE_PATH = APP_DATA_PATH / "storage"
    METADATA_PATH = APP_DATA_PATH / "metadata"

    # Ensure directories exist
    syft_client.makedirs(FILE_STORAGE_PATH)
    syft_client.makedirs(METADATA_PATH)

    # Store user email for syft URL generation
    settings.SYFT_USER_EMAIL = syft_client.email
