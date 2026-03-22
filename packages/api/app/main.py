from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.routers import auth, documents, highlights, export, users

# Import models so SQLAlchemy registers them before create_all
import app.models.user       # noqa: F401
import app.models.document   # noqa: F401
import app.models.highlight  # noqa: F401

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_prefix = settings.api_v1_prefix
app.include_router(auth.router,       prefix=_prefix)
app.include_router(users.router,      prefix=_prefix)
app.include_router(documents.router,  prefix=_prefix)
app.include_router(highlights.router, prefix=_prefix)
app.include_router(export.router,     prefix=_prefix)


@app.get("/health")
async def health():
    return {"status": "ok"}
