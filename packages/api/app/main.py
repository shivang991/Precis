from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.shared import get_settings, engine, Base, DomainError
from app.users import auth_router, users_router
from app.documents import router as documents_router
from app.highlights import router as highlights_router
# Import models so SQLAlchemy registers them before create_all
import app.users.models  # noqa: F401
import app.documents.models  # noqa: F401
import app.highlights.models  # noqa: F401

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


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


@app.get("/health")
async def health():
    return {"status": "ok"}
