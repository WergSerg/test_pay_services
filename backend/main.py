from fastapi import FastAPI
from contextlib import asynccontextmanager

from backend.api.routers import payments, health
from backend.core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        pass
    yield
    await engine.dispose()


app = FastAPI(
    title="Payment Processing Service",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False
)

app.include_router(payments.router)
app.include_router(health.router)


@app.get("/")
async def root():
    return {
        "service": "Payment Processing Service",
        "version": "1.0.0",
        "status": "running"
    }