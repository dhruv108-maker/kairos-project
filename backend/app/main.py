from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.modules.shared.exceptions import KairosDomainError

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
# The API router owns registration for both legacy and opt-in modular routes.
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(KairosDomainError)
async def kairos_domain_error_handler(request: Request, exc: KairosDomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": str(exc)}})


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.APP_NAME}
