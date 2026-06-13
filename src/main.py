import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.domain.exceptions import DomainError, EntityNotFoundError, ValidationError
from src.infrastructure.config import get_settings
from src.presentation.admin.setup import setup_admin
from src.presentation.api.routers import (
    auth,
    car_catalog,
    crawl_results,
    crawl_targets,
    crawl_tasks,
    divar_reference,
    flow,
    gateway,
    listing_mappings,
    me,
    metrics,
    opportunities,
    platforms,
    purchase_requests,
    share,
    users,
)

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Car Deal Opportunity Detection Platform",
    description="Vehicle opportunity detection with pluggable listing and pricing platforms",
    version="0.3.0",
)

# Trust X-Forwarded-* from nginx so /admin static assets use https:// URLs.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

_origins = settings.cors_origins
if _origins == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(car_catalog.router, prefix="/api/v1")
app.include_router(platforms.router, prefix="/api/v1")
app.include_router(divar_reference.router, prefix="/api/v1")
app.include_router(listing_mappings.router, prefix="/api/v1")
app.include_router(crawl_targets.router, prefix="/api/v1")
app.include_router(crawl_results.router, prefix="/api/v1")
app.include_router(share.router, prefix="/api/v1")
app.include_router(crawl_tasks.router, prefix="/api/v1")
app.include_router(purchase_requests.router, prefix="/api/v1")
app.include_router(opportunities.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(flow.router, prefix="/api/v1")
app.include_router(gateway.router)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

setup_admin(app)


@app.get("/")
async def landing_page():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Car Opportunity API", "docs": "/docs", "admin": "/admin"}


@app.get("/results")
async def results_page():
    page = static_dir / "results.html"
    if page.exists():
        return FileResponse(page)
    return {"message": "Results page not found"}


@app.get("/trim-mapping")
async def trim_mapping_page():
    page = static_dir / "trim-mapping.html"
    if page.exists():
        return FileResponse(page)
    return {"message": "Trim mapping page not found"}


portal_dir = Path(__file__).resolve().parent.parent / "user-portal"
if portal_dir.exists():
    app.mount("/portal", StaticFiles(directory=str(portal_dir), html=True), name="user-portal")


@app.exception_handler(EntityNotFoundError)
async def not_found_handler(_: Request, exc: EntityNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ValidationError)
async def validation_handler(_: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(DomainError)
async def domain_handler(_: Request, exc: DomainError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
async def health():
    return {"status": "ok"}
