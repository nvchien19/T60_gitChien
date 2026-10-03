import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from langchain_core.language_models import BaseChatModel

from src.agents.graph import agent
from src.models.schemas import ChatRequest, ChatResponse, InteractionCheckRequest, InteractionCheckResponse
from src.services.ddi_check import check_interactions
from src.services.ddi_repository import DDIRepository, get_repository
from src.services.llm import get_explainer_llm

log = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Chat với AI agent."""
    try:
        result = await agent.ainvoke({"query": request.message})
        return ChatResponse(
            response=result.get("response", ""),
            analysis=result.get("analysis", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def agent_status():
    """Kiểm tra trạng thái agent."""
    return {"status": "ready", "agent": "LangGraph Agent v1.0"}


@router.post("/interactions/check", response_model=InteractionCheckResponse)
async def check_drug_interactions(
    request: InteractionCheckRequest,
    repo: DDIRepository = Depends(get_repository),
    llm: BaseChatModel | None = Depends(get_explainer_llm),
) -> InteractionCheckResponse:
    """Kiểm tra tương tác thuốc - thuốc trong danh sách thuốc; giải thích từng cặp bằng DeepSeek nếu đã cấu hình."""
    try:
        result = await check_interactions(request.drugs, repo, llm=llm if request.explain else None)
    except psycopg.Error as e:
        log.exception("Lỗi truy vấn CSDL tương tác")
        raise HTTPException(status_code=503, detail=f"Không truy vấn được CSDL tương tác thuốc: {e}") from e
    if request.explain and llm is None and result.pairs:
        result.notes.append("Chưa cấu hình DEEPSEEK_API_KEY nên phần giải thích dùng mẫu soạn sẵn từ CSDL.")
    return result
