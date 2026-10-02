from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.session import get_session
from interface.backend.repositories import ddi_repo
from interface.backend.schemas.ddi import NormalizeRequest
from interface.backend.services.check_service import normalize_list

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.post("/normalize")
async def normalize(req: NormalizeRequest, db: AsyncSession = Depends(get_session)):
    return {"items": [n.model_dump() for n in await normalize_list(db, req.drugs)]}


@router.get("/search")
async def search(q: str, limit: int = 10, db: AsyncSession = Depends(get_session)):
    if len(q.strip()) < 2:
        return {"items": []}
    return {"items": await ddi_repo.search_drugs(db, q.strip(), limit=limit)}
