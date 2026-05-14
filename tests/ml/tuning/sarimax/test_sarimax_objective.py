import optuna
from app.ml.tuning.sarimax.objective import SARIMAXObjective


def test_sarimax_objective_with_real_optuna(
    X,
    y,
):
    objective = SARIMAXObjective(X=X, y=y, n_splits=2)
    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(objective, n_trials=2)
    assert len(study.trials) == 2
    assert study.best_value >= 0
    assert isinstance(
        study.best_params,
        dict,
    )
    assert "p" in study.best_params
    assert "d" in study.best_params
    assert "q" in study.best_params
