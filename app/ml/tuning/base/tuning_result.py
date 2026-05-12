from dataclasses import dataclass


@dataclass
class TuningResult:
    model_type: str
    target: str
    city: str | None
    best_params: dict
    best_score: float
    metric_name: str
    n_trials: int
    fitted_model: object | None = None
