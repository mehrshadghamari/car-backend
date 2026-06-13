from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from src.application.use_cases.gateway_preview import GatewayPreviewUseCase
from src.application.use_cases.gateway_redirect import GatewayRedirectUseCase
from src.domain.exceptions import EntityNotFoundError
from src.presentation.dependencies import get_gateway_preview_use_case, get_gateway_use_case

router = APIRouter(tags=["gateway"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _render_preview_page(result) -> str:
    km = f"{result.kilometer:,}" if result.kilometer else "—"
    year = result.production_year or "—"
    district = result.district or "—"
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>فرصت خرید خودرو</title>
  <style>
    body {{ font-family: Tahoma, sans-serif; background: #f4f6f8; margin: 0; padding: 24px; }}
    .card {{ max-width: 520px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 4px 16px rgba(0,0,0,.08); }}
    h1 {{ font-size: 1.2rem; margin: 0 0 16px; }}
    .price {{ font-size: 1.1rem; color: #0b6; font-weight: bold; }}
    .meta {{ color: #555; line-height: 1.8; }}
    .btn {{ display: block; margin-top: 20px; text-align: center; background: #2563eb; color: #fff; text-decoration: none; padding: 12px; border-radius: 8px; }}
    .stats {{ margin-top: 16px; font-size: .85rem; color: #888; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{result.title}</h1>
    <p class="price">قیمت آگهی: {result.listing_price:,} تومان</p>
    <p class="meta">
      سال: {year} · کارکرد: {km} km<br>
      محله: {district}<br>
      کف بازار: {result.market_price_down:,} · سقف: {result.market_price_up:,}<br>
      تخفیف تقریبی: {result.discount_pct}%
    </p>
    <a class="btn" href="{result.redirect_path}">مشاهده آگهی در دیوار</a>
    <p class="stats">بازدید: {result.total_views} (یکتا: {result.unique_views})</p>
  </div>
</body>
</html>"""


@router.get("/g/{token}", response_class=HTMLResponse)
async def gateway_preview(
    token: str,
    request: Request,
    use_case: GatewayPreviewUseCase = Depends(get_gateway_preview_use_case),
):
    try:
        result = await use_case.execute(token, _client_ip(request))
        return HTMLResponse(content=_render_preview_page(result))
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/g/{token}/go")
async def gateway_redirect(
    token: str,
    use_case: GatewayRedirectUseCase = Depends(get_gateway_use_case),
):
    try:
        result = await use_case.execute(token)
        return RedirectResponse(url=result.redirect_url, status_code=302)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
