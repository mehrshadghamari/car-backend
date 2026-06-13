from fastapi import APIRouter, Depends, Query

from src.presentation.api.schemas import DivarCarModelResponse, DivarCityResponse
from src.presentation.dependencies import get_platform_repo

router = APIRouter(prefix="/divar", tags=["divar"])


@router.get("/cities", response_model=list[DivarCityResponse])
async def list_divar_cities(
    q: str | None = Query(None, description="Filter by slug or display name"),
    limit: int = Query(500, ge=1, le=2000),
    repo=Depends(get_platform_repo),
):
    cities = await repo.list_divar_cities(q=q, limit=limit)
    return [DivarCityResponse(id=c.id, slug=c.slug, display=c.display) for c in cities]


@router.get("/car-models", response_model=list[DivarCarModelResponse])
async def list_divar_car_models(
    q: str | None = Query(None, description="Filter by slug or display name"),
    limit: int = Query(50, ge=1, le=2500),
    repo=Depends(get_platform_repo),
):
    models = await repo.list_divar_car_models(q=q, limit=limit)
    return [DivarCarModelResponse(id=m.id, slug=m.slug, display=m.display) for m in models]
