from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import connect_db, disconnect_db
from app.loads.router import router as loads_router
from app.negotiations.router import router as negotiations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="Carrier Load Automation",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(loads_router)
app.include_router(negotiations_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
