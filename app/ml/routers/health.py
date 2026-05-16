from fastapi import APIRouter, Request
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    reg = request.app.state.registry
    return HealthResponse(
        status="ok" if reg.is_ready() else "no_model",
        model_loaded=reg.is_ready(),
        model_version=reg.version,
        retraining_now=reg.retraining,
    )
