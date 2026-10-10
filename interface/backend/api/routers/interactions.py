import logging

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from langchain_core.language_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.session import get_session
from interface.backend.repositories import ddi_repo
from interface.backend.schemas.chat import InteractionCheckRequest, InteractionCheckResponse
from interface.backend.schemas.ddi import CheckRequest, CheckResponse
from interface.backend.services.check_service import normalize_list, run_check
from src.core.guardrails import NO_RECORD_MSG
from src.services.ddi_check import check_interactions
from src.services.ddi_repository import DDIRepository, get_repository
from src.services.llm import get_explainer_llm

log = logging.getLogger(__name__)

router = APIRouter(tags=["interactions"])


@router.post("/interactions/check", response_model=CheckResponse)
async def check(req: CheckRequest, db: AsyncSession = Depends(get_session)):
    return await run_check(db, req.drugs, include_food=req.include_food)


@router.post("/interactions/explain", response_model=InteractionCheckResponse)
async def explain(
    request: InteractionCheckRequest,
    repo: DDIRepository = Depends(get_repository),
    llm: BaseChatModel | None = Depends(get_explainer_llm),
) -> InteractionCheckResponse:
    """Giải thích từng cặp tương tác bằng tiếng Việt (DeepSeek), từng câu được kiểm chứng với bản ghi CSDL.

    Chưa có DEEPSEEK_API_KEY, LLM lỗi hoặc viết ngoài bằng chứng thì trả bản mẫu soạn sẵn từ CSDL.
    """
    try:
        result = await check_interactions(request.drugs, repo, llm=llm if request.explain else None)
    except psycopg.Error as e:
        log.exception("Lỗi truy vấn CSDL tương tác")
        raise HTTPException(status_code=503, detail=f"Không truy vấn được CSDL tương tác thuốc: {e}") from e
    if request.explain and llm is None and result.pairs:
        result.notes.append("Chưa cấu hình DEEPSEEK_API_KEY nên phần giải thích dùng mẫu soạn sẵn từ CSDL.")
    return result


@router.get("/interactions/pair")
async def pair(a: str, b: str, db: AsyncSession = Depends(get_session)):
    normed = await normalize_list(db, [a, b])
    oks = [n for n in normed if n.status == "ok"]
    if len(oks) < 2:
        return {"pair": [a, b], "match_type": "no_record", "note": NO_RECORD_MSG,
                "normalized": [n.model_dump() for n in normed]}
    recs = await ddi_repo.get_pair_interactions(db, oks[0].drug_id, oks[1].drug_id)
    if not recs:
        return {"pair": [a, b], "match_type": "no_record", "note": NO_RECORD_MSG}
    return {"pair": [a, b], "match_type": "exact", "items": recs}
