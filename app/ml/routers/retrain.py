from fastapi import APIRouter, Request, BackgroundTasks
from app.schemas.forecast import RetrainResponse

router = APIRouter()


@router.post("/retrain", response_model=RetrainResponse)
async def retrain(request: Request, bg: BackgroundTasks) -> RetrainResponse:
    trainer = request.app.state.trainer
    bg.add_task(trainer.run)
    return RetrainResponse(
        status="started", message="Retraining scheduled in background"
    )
