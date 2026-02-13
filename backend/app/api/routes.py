"""FastAPI routes for interview endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_interview_service
from app.api.schemas import (
    EndRequest,
    EndResponse,
    ErrorResponse,
    MessageRequest,
    StartRequest,
)
from app.interview.service import (
    InterviewService,
    SessionAlreadyCompletedError,
    SessionNotFoundError,
)

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/start")
async def start_interview(
    request: StartRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Starts a new interview and streams the opening question via SSE.

    SSE Events:
    - text-delta: Token chunks of the opening question
    - text-done: Opening question complete
    - metadata: session_id for further requests
    - error: On LLM errors
    """

    async def event_generator():
        async for sse_data in service.start(request.anonymous_id):
            yield {"data": sse_data}

    return EventSourceResponse(event_generator())


@router.post("/message")
async def send_message(
    request: MessageRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Sends a message and streams the interviewer response via SSE.

    SSE Events:
    - text-delta: Token chunks of the response
    - text-done: Response complete
    - error: On LLM errors
    """
    try:
        service._validate_session(request.session_id)
    except SessionNotFoundError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="Session not found",
                detail=f"No active session with id {request.session_id}",
            ).model_dump(),
        )
    except SessionAlreadyCompletedError:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error="Session already completed",
                detail=f"Session {request.session_id} has already been completed",
            ).model_dump(),
        )

    async def event_generator():
        async for sse_data in service.message(request.session_id, request.message):
            yield {"data": sse_data}

    return EventSourceResponse(event_generator())


@router.post("/end")
async def end_interview(
    request: EndRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Ends an interview and returns a placeholder summary.

    Returns:
        EndResponse with summary and message_count.
    """
    try:
        result = await service.end(request.session_id)
    except SessionNotFoundError:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="Session not found",
                detail=f"No active session with id {request.session_id}",
            ).model_dump(),
        )
    except SessionAlreadyCompletedError:
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error="Session already completed",
                detail=f"Session {request.session_id} has already been completed",
            ).model_dump(),
        )

    return EndResponse(
        summary=result["summary"],
        message_count=result["message_count"],
    )
