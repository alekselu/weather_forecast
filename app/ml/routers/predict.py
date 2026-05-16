from fastapi import APIRouter, Request, HTTPException
from app.schemas import PredictRequest, PredictResponse

router = APIRouter()


@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request) -> PredictResponse:
    predictor = request.app.state.predictor
    if not request.app.state.registry.is_ready():
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    try:
        return predictor.predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
