from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from src.api.routes import characters, generation, health
from src.core.config import get_settings

settings = get_settings()

# API Key authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Depends(api_key_header)) -> str:
    """Verify API key for protected endpoints."""
    if not settings.api_key:
        # No API key configured - allow access (dev mode)
        return ""
    if not api_key or api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Character Generation API",
    description="API for AI character image and video generation with LoRA-based character system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration - use allowed_origins from settings
allowed_origins = (
    settings.allowed_origins.split(",") if settings.allowed_origins else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    characters.router,
    prefix="/characters",
    tags=["Characters"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    generation.router,
    tags=["Generation"],
    dependencies=[Depends(verify_api_key)],
)
