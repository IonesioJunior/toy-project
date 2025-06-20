from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
import logging

from ..services.vector_service import VectorService
from ..utils.exceptions import DocumentNotFoundError, ChromaDBError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ui"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="src/app/templates")


def get_vector_service() -> VectorService:
    """Dependency to get vector service instance"""
    return VectorService()


@router.get("/", response_class=HTMLResponse)
async def ui_dashboard(
    request: Request,
    service: VectorService = Depends(get_vector_service)
):
    """Main dashboard page"""
    try:
        # Get basic statistics
        documents, total = service.list_documents(limit=5, offset=0)
        
        # Get recent documents
        recent_docs = documents[:5] if documents else []
        
        context = {
            "request": request,
            "total_documents": total,
            "recent_documents": recent_docs,
            "page_title": "Dashboard"
        }
        
        return templates.TemplateResponse("dashboard.html", context)
        
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        context = {
            "request": request,
            "error": "Failed to load dashboard data",
            "total_documents": 0,
            "recent_documents": [],
            "page_title": "Dashboard"
        }
        return templates.TemplateResponse("dashboard.html", context)


@router.get("/documents", response_class=HTMLResponse)
async def ui_documents(
    request: Request,
    page: int = 1,
    limit: int = 12,
    category: Optional[str] = None,
    search: Optional[str] = None
):
    """Documents management page"""
    context = {
        "request": request,
        "page": page,
        "limit": limit,
        "category_filter": category,
        "search_query": search,
        "page_title": "Documents"
    }
    
    return templates.TemplateResponse("documents.html", context)


@router.get("/search", response_class=HTMLResponse)
async def ui_search(request: Request):
    """Search page"""
    context = {
        "request": request,
        "page_title": "Search"
    }
    
    return templates.TemplateResponse("search.html", context)


@router.get("/upload", response_class=HTMLResponse)
async def ui_upload(request: Request):
    """Upload page"""
    context = {
        "request": request,
        "page_title": "Upload Documents"
    }
    
    return templates.TemplateResponse("upload.html", context)


@router.get("/document/{document_id}", response_class=HTMLResponse)
async def ui_document_detail(
    request: Request,
    document_id: str,
    service: VectorService = Depends(get_vector_service)
):
    """Document detail page"""
    try:
        document = service.get_document(document_id)
        
        # Get similar documents
        similar_docs = []
        try:
            query_result = service.query_documents({
                "query_text": document.content[:200],  # Use first 200 chars as query
                "n_results": 5
            })
            
            # Filter out the current document from similar results
            for i, doc_id in enumerate(query_result.ids):
                if doc_id != document_id:
                    similar_docs.append({
                        "id": doc_id,
                        "content": query_result.documents[i],
                        "distance": query_result.distances[i],
                        "metadata": query_result.metadatas[i]
                    })
                    
        except Exception as e:
            logger.warning(f"Failed to get similar documents: {str(e)}")
        
        context = {
            "request": request,
            "document": document,
            "similar_documents": similar_docs[:4],  # Show top 4 similar docs
            "page_title": f"Document: {document_id}"
        }
        
        return templates.TemplateResponse("document_detail.html", context)
        
    except DocumentNotFoundError:
        context = {
            "request": request,
            "error": f"Document '{document_id}' not found",
            "page_title": "Document Not Found"
        }
        return templates.TemplateResponse("error.html", context)
        
    except Exception as e:
        logger.error(f"Document detail error: {str(e)}")
        context = {
            "request": request,
            "error": "Failed to load document",
            "page_title": "Error"
        }
        return templates.TemplateResponse("error.html", context)