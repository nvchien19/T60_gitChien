from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from interface.backend.db.session import get_session
from interface.backend.repositories import ddi_repo

router = APIRouter(tags=["sources"])


@router.get("/sources")
async def sources(db: AsyncSession = Depends(get_session)):
    rows = await ddi_repo.list_sources(db)
    cov = await ddi_repo.count_coverage(db)
    return {
        "items": [
            {"source_id": s.source_id, "name": s.name, "citation": s.citation,
             "url": s.url, "license": s.license,
             "last_updated": str(s.last_updated) if s.last_updated else ""}
            for s in rows
        ],
        "coverage": cov,
        "notice": "DDInter và Patel 2020 chỉ dùng phi thương mại (CC BY-NC); "
                  "PK-DDIP chỉ tham khảo nội bộ.",
    }
