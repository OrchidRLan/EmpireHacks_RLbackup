from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.database import create_all_tables
import app.models  # noqa: F401 - ensures all models are registered with SQLAlchemy

from app.routers import (
    users,
    preferences,
    apartments,
    neighborhoods,
    matches,
    agent_logs,
    messages,
    notifications,
)
from app.routers import agents

# v1 bridge routers
from app.routers.v1 import auth as v1_auth
from app.routers.v1 import preferences as v1_preferences
from app.routers.v1 import listings as v1_listings
from app.routers.v1 import negotiations as v1_negotiations
from app.routers.v1 import agent as v1_agent
from app.routers.v1 import notifications as v1_notifications
from app.routers.v1 import tours as v1_tours

from app.agents.agent1_image import run_agent1_batch
from app.constants import CORS_ORIGINS


@asynccontextmanager
async def lifespan(application: FastAPI):
    await create_all_tables()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_agent1_batch, "interval", hours=2, id="agent1_batch")
    scheduler.start()
    yield
    scheduler.shutdown()


# ---------------------------------------------------------------------------
# Rate limiter (slowapi) — shared limiter instance used by agent routers.
# OWASP API4:2023 Unrestricted Resource Consumption.
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Rento API",
    description="NYC apartment search automation backend",
    version="1.0.0",
    lifespan=lifespan,
)

# Register the slowapi 429 handler so rate-limit errors return proper JSON.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — restrict to an explicit allow-list instead of "*".
# Read a comma-separated CORS_ORIGINS env var; fall back to localhost:3000.
# OWASP A05:2021 Security Misconfiguration.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(preferences.router)
app.include_router(apartments.router)
app.include_router(neighborhoods.router)
app.include_router(matches.router)
app.include_router(agent_logs.router)
app.include_router(messages.router)
app.include_router(notifications.router)
app.include_router(agents.router)

# ---------------------------------------------------------------------------
# v1 bridge layer — all routes under /api/v1
# ---------------------------------------------------------------------------
_V1_PREFIX = "/api/v1"

app.include_router(v1_auth.router, prefix=_V1_PREFIX)
app.include_router(v1_preferences.router, prefix=_V1_PREFIX)
app.include_router(v1_listings.router, prefix=_V1_PREFIX)
app.include_router(v1_negotiations.router, prefix=_V1_PREFIX)
app.include_router(v1_agent.router, prefix=_V1_PREFIX)
app.include_router(v1_notifications.router, prefix=_V1_PREFIX)
app.include_router(v1_tours.router, prefix=_V1_PREFIX)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
