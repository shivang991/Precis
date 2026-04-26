from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from alembic import command
from app.documents import router as documents_router
from app.highlights import router as highlights_router
from app.shared import (
    DomainError,
    get_logger,
    get_settings,
    setup_logging,
)
from app.users import auth_router, users_router

_ALEMBIC_DIR = Path(__file__).resolve().parent.parent / "alembic"

settings = get_settings()
setup_logging()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up", app_name=settings.app_name, debug=settings.debug)
    cfg = Config()
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    command.upgrade(cfg, "head")
    yield
    logger.info("shutting_down")


app = FastAPI(
    title="Precis API",
    description=(
        "Cloud backend for Precis — a PDF highlighting and summary app. "
        "Converts PDFs to a structured Standard Format, tracks highlights, "
        "and exports summary views."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_prefix = settings.api_v1_prefix
app.include_router(auth_router, prefix=_prefix)
app.include_router(users_router, prefix=_prefix)
app.include_router(documents_router, prefix=_prefix)
app.include_router(highlights_router, prefix=_prefix)


@app.get("/health", operation_id="health_check")
async def health():
    return {"status": "ok"}
