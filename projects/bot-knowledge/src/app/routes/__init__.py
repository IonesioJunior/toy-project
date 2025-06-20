from .documents import router as documents_router
from .health import router as health_router
from .ui import router as ui_router

__all__ = ["documents_router", "health_router", "ui_router"]