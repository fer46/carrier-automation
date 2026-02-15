from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.analytics.router import router as analytics_router
from app.database import connect_db, disconnect_db
from app.loads.router import router as loads_router

DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(loads_router)
app.include_router(analytics_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Serve dashboard SPA — must be after API routes
if DASHBOARD_DIR.exists():
    app.mount(
        "/dashboard/assets",
        StaticFiles(directory=DASHBOARD_DIR / "assets"),
        name="dashboard-assets",
    )

    @app.get("/dashboard")
    async def dashboard_root():
        return FileResponse(DASHBOARD_DIR / "index.html")

    @app.get("/dashboard/{full_path:path}")
    async def serve_dashboard(full_path: str = ""):
        return FileResponse(DASHBOARD_DIR / "index.html")
