from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from typing import AsyncIterator
import json
import logging

from src.models.chat import ChatRequest, ChatResponse
from src.services.chat import chat_service
from src.core.exceptions import SessionNotFoundException


router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


@router.post("/")
async def chat_endpoint(request: ChatRequest, http_request: Request) -> StreamingResponse:
    """Handle chat messages with streaming response."""
    try:
        # Get or create session ID
        session_id = request.session_id
        if not session_id:
            # Try to get from cookies
            session_id = http_request.cookies.get("session_id")
        
        # Get or create session
        session = await chat_service.get_or_create_session(session_id)
        session_id = session.session_id
        
        async def generate() -> AsyncIterator[str]:
            """Generate SSE events."""
            try:
                # Send session ID first
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
                
                # Stream the response
                async for chunk in chat_service.process_message_stream(
                    session_id, 
                    request.message
                ):
                    data = json.dumps({"type": "content", "content": chunk})
                    yield f"data: {data}\n\n"
                
                # Send completion signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                logger.error(f"Error in generate function: {str(e)}")
                error_data = json.dumps({"type": "error", "error": "An internal error occurred."})
                yield f"data: {error_data}\n\n"
        
        response = StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable Nginx buffering
            }
        )
        
        # Set session cookie
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=3600  # 1 hour
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def clear_history(request: Request) -> dict:
    """Clear chat history for the current session."""
    try:
        # Get session ID from cookies
        session_id = request.cookies.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="No session found")
        
        await chat_service.clear_session(session_id)
        
        return {"status": "success", "message": "Chat history cleared"}
        
    except SessionNotFoundException:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Clear history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))