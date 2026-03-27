from fastapi import FastAPI
from contextlib import asynccontextmanager

from backend.api.routers import payments, health
from backend.core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        # Create tables if not exists (for dev)
        # In production use Alembic migrations
        pass
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="Payment Processing Service",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

# Include routers
app.include_router(payments.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "service": "Payment Processing Service",
        "version": "1.0.0",
        "status": "running"
    }