"""Router chat/agent — mỏng, chỉ I/O; orchestration nằm ở `agent_adapter`."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.agent_adapter import agent_available, run_agent
from interface.backend.db.session import get_session
from interface.backend.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_session)) -> ChatResponse:
    """Chat với AI agent. 503 nếu LangGraph chưa cài."""
    if not agent_available():
        raise HTTPException(status_code=503, detail="Agent chưa sẵn sàng (thiếu langgraph)")
    try:
        result = await run_agent(db, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(
        response=result.get("response", ""),
        analysis=result.get("analysis", ""),
    )


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    ready = agent_available()
    return {"status": "ready" if ready else "disabled", "agent": "LangGraph Agent v1.0"}
