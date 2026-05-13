import optuna
from app.ml.tuning.base.tuner import BaseTuner
from app.ml.tuning.base.tuning_result import TuningResult
from app.ml.tuning.xgb.objective import XGBObjective


class XGBTuner(BaseTuner):
    def __init__(
        self,
        target,
        city=None,
        n_trials=50,
    ):
        self.target = target
        self.city = city
        self.n_trials = n_trials

    def tune(
        self,
        X,
        y,
    ):
        objective = XGBObjective(
            X,
            y,
        )
        study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=42),
        )
        study.optimize(
            objective,
            n_trials=self.n_trials,
        )
        return TuningResult(
            model_type="xgboost",
            target=self.target,
            city=self.city,
            best_params=study.best_params,
            best_score=study.best_value,
            metric_name="MAE",
            n_trials=self.n_trials,
        )
