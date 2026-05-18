import optuna
from app.ml.tuning.base.tuner import BaseTuner
from app.ml.tuning.base.tuning_result import TuningResult
from app.ml.tuning.sarimax.objective import SARIMAXObjective


class SARIMAXTuner(BaseTuner):
    def __init__(
        self,
        target,
        city,
        n_trials=30,
    ):
        self.target = target
        self.city = city
        self.n_trials = n_trials

    def tune(
        self,
        X,
        y,
    ):
        objective = SARIMAXObjective(
            X,
            y,
        )
        study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(
                seed=42,
            ),
        )
        study.optimize(
            objective,
            n_trials=self.n_trials,
        )
        return TuningResult(
            model_type="sarimax",
            target=self.target,
            city=self.city,
            best_params=study.best_params,
            best_score=study.best_value,
            metric_name="MAE",
            n_trials=self.n_trials,
        )
