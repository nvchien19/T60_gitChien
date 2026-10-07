from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interface.backend.api.routers import auth, drugs, evaluation, interactions, prescriptions, sources
from interface.backend.api.routes import router as agent_router
from interface.backend.config import get_settings
from interface.backend.db.base import Base
from interface.backend.db.models import tables  # noqa: F401  (dang ky models)
from interface.backend.db.session import engine
from interface.backend.services.auth_service import current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting {settings.app_name} in {settings.app_env} mode")
    # P0: tu tao bang khi chay (thay Alembic cho dev/test; prod van co migration)
    if settings.app_env in ("development", "test"):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:  # DB chua chay (CI) -> API van boot, endpoint bao loi DB
            print(f"WARN create_all failed: {e}")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Rả thuốc — DDI Safety API",
    description="Tra cứu tương tác thuốc & cảnh báo an toàn (grounded từ CSDL thật)",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(drugs.router, prefix="/api/v1", dependencies=[Depends(current_user)])
app.include_router(interactions.router, prefix="/api/v1", dependencies=[Depends(current_user)])
app.include_router(sources.router, prefix="/api/v1", dependencies=[Depends(current_user)])
app.include_router(prescriptions.router, prefix="/api/v1", dependencies=[Depends(current_user)])
app.include_router(evaluation.router, prefix="/api/v1", dependencies=[Depends(current_user)])
app.include_router(agent_router, prefix="/api/v1", dependencies=[Depends(current_user)])


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
