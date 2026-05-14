import optuna
from app.ml.tuning.xgb.objective import XGBObjective


def test_xgb_objective_with_real_optuna(
    X,
    y,
):
    print(f"{X.columns = }")
    objective = XGBObjective(X=X, y=y, n_splits=2)
    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective, n_trials=2)
    assert len(study.trials) == 2
    assert study.best_value >= 0
    assert isinstance(
        study.best_params,
        dict,
    )
    assert "n_estimators" in study.best_params
    assert "max_depth" in study.best_params
