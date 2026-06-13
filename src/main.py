import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
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
from src.presentation.routing_paths import (
    is_wrong_portal_secret_path,
    portal_admin_path,
    portal_results_path,
    portal_secret_prefix,
    portal_trim_mapping_path,
    portal_user_prefix,
)

settings = get_settings()
_secret_prefix = portal_secret_prefix()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Car Deal Opportunity Detection Platform",
    description="Vehicle opportunity detection with pluggable listing and pricing platforms",
    version="0.3.0",
    docs_url=f"{_secret_prefix}/docs",
    redoc_url=f"{_secret_prefix}/redoc",
    openapi_url=f"{_secret_prefix}/openapi.json",
)

# Trust X-Forwarded-* from nginx so /admin static assets use https:// URLs.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


@app.middleware("http")
async def block_guessed_portal_secret_paths(request: Request, call_next) -> Response:
    """Return 404 for /portal/{uuid}/{uuid}/… when UUIDs are not the configured pair."""
    if is_wrong_portal_secret_path(request.url.path):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return await call_next(request)


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
portal_dir = Path(__file__).resolve().parent.parent / "user-portal"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Staff routes (secret UUID prefix) must register before the public /portal static mount.
setup_admin(app, admin_base_url=portal_admin_path())


@app.get("/")
async def root_redirect():
    return RedirectResponse(url=f"{portal_user_prefix()}/", status_code=302)


@app.get(portal_results_path())
async def results_page():
    page = static_dir / "results.html"
    if page.exists():
        return FileResponse(page)
    raise HTTPException(status_code=404, detail="Results page not found")


@app.get(portal_trim_mapping_path())
async def trim_mapping_page():
    page = static_dir / "trim-mapping.html"
    if page.exists():
        return FileResponse(page)
    raise HTTPException(status_code=404, detail="Trim mapping page not found")


@app.get("/results", include_in_schema=False)
@app.get("/trim-mapping", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
@app.get("/admin/{path:path}", include_in_schema=False)
@app.get("/docs", include_in_schema=False)
@app.get("/redoc", include_in_schema=False)
@app.get("/openapi.json", include_in_schema=False)
async def legacy_staff_paths_blocked():
    raise HTTPException(status_code=404, detail="Not found")


if portal_dir.exists():
    app.mount(
        portal_user_prefix(),
        StaticFiles(directory=str(portal_dir), html=True),
        name="user-portal",
    )


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
