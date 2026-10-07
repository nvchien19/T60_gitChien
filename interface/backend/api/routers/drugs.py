from fastapi import APIRouter, Depends, Query
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


@router.get("/products/search")
async def search_products(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_session),
):
    """Tra tên sản phẩm để đối chiếu OCR; không suy đoán liều/cách dùng."""
    if len(q.strip()) < 2:
        return {"items": []}
    return {"items": await ddi_repo.search_products(db, q.strip(), limit)}
