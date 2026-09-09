"""
The parts-ordering API.

Backs the "raise a requirement → check availability → order → allocate →
ship → receive" workflow the Parts branch of The Ground describes. The
seven stages here are that graph's own seven node names — see models.py.

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import SessionLocal
from .routers import kits, parts, requirements
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The schema itself is Alembic's job (see alembic/, and the README) —
    # `alembic upgrade head` before the first run, same as any real
    # deployment. This only ever inserts starter rows into tables that
    # migration is assumed to have already created; it does not create
    # tables itself, so the database in front of the app is always exactly
    # what the migration history says it is, never a create_all guess that
    # could silently drift from it.
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Parts Ordering",
    description="The requirement-to-goods-receipt workflow behind The Ground's Parts branch.",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(parts.router)
app.include_router(requirements.router)
app.include_router(kits.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
