from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.errors.exceptions import AppError, app_error_handler
from app.middleware.correlation import CorrelationIdMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.fulfilment import router as fulfilment_router
from app.api.v1.availability import router as availability_router
from app.api.v1.allocation import router as allocation_router
from app.api.v1.order import fulfilment_router as order_fulfilment_router, order_router as order_router
from app.api.v1.shipment import router as shipment_router
from app.api.v1.service_jobs import router as service_jobs_router
from app.api.v1.quote_request import router as quote_request_router

from app.api.v1.part_enrichment import router as part_enrichment_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.dealers import router as dealers_router
from app.modules.transport.router import router as transport_router
from app.db.neo4j.connection import get_neo4j_driver, close_driver
from app.db.neo4j.schema import apply_schema
from app.logging_config.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown lifecycle."""
    logger.info("Starting HCME After-Sales Platform API (Neo4j-only backend)")
    try:
        driver = get_neo4j_driver()
        db = getattr(settings, "NEO4J_DATABASE", None) or None
        session_kwargs = {}
        if db:
            session_kwargs["database"] = db
        with driver.session(**session_kwargs) as session:
            apply_schema(session)
    except Exception as e:
        logger.error(f"Neo4j startup initialisation failed: {e}")
        raise

    yield

    logger.info("Shutting down HCME After-Sales Platform API")
    close_driver()


app = FastAPI(
    title="HCME OEM After-Sales Parts & Services Platform API",
    description=(
        "Python FastAPI backend — Neo4j graph database, Phase 4 Availability Engine, "
        "Phase 5 Fulfilment Options, allocation concurrency safety."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Correlation Middleware
app.add_middleware(CorrelationIdMiddleware)

# Exception Handlers
app.add_exception_handler(AppError, app_error_handler)

# Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(fulfilment_router, prefix="/api/v1")
app.include_router(availability_router, prefix="/api/v1")
app.include_router(allocation_router, prefix="/api/v1")
app.include_router(order_fulfilment_router, prefix="/api/v1")
app.include_router(order_router, prefix="/api/v1")
app.include_router(shipment_router, prefix="/api/v1")
app.include_router(service_jobs_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(dealers_router, prefix="/api/v1")
app.include_router(transport_router, prefix="/api/v1")

app.include_router(quote_request_router, prefix="/api/v1")
app.include_router(part_enrichment_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "system": "HCME After-Sales Platform API",
        "version": "1.0.0",
        "database": "Neo4j",
        "status": "RUNNING",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
