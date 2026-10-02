from fastapi import APIRouter, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.session import get_session
from interface.backend.repositories import ddi_repo
from interface.backend.schemas.ddi import CheckRequest, CheckResponse
from interface.backend.services.check_service import normalize_list, run_check
from src.core.guardrails import NO_RECORD_MSG

router = APIRouter(tags=["interactions"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/normalize", response_model=dict)
async def normalize(req: CheckRequest, db: AsyncSession = Depends(get_session)):
    items = await normalize_list(db, req.drugs)
    return {"items": [n.model_dump() for n in items]}


@router.post("/interactions/check", response_model=CheckResponse)
async def check(req: CheckRequest, db: AsyncSession = Depends(get_session)):
    return await run_check(db, req.drugs, include_food=req.include_food)


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
