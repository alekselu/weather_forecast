import numpy as np
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit
from app.ml.models.sarimax_forecaster import SARIMAXForecaster


class SARIMAXObjective:
    def __init__(
        self,
        X,
        y,
        n_splits=3,
    ):
        self.X = X
        self.y = y
        self.n_splits = n_splits

    def __call__(self, trial):
        order = (
            trial.suggest_int("p", 0, 3),
            trial.suggest_int("d", 0, 2),
            trial.suggest_int("q", 0, 3),
        )
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        maes = []
        for train_idx, val_idx in tscv.split(self.X):
            X_train = self.X.iloc[train_idx]
            X_val = self.X.iloc[val_idx]
            y_train = self.y.iloc[train_idx]
            y_val = self.y.iloc[val_idx]
            try:
                model = SARIMAXForecaster(
                    order=order,
                )
                model.fit(
                    X_train,
                    y_train,
                )
                preds = model.predict(
                    X_future=X_val,
                )
                mae = mean_absolute_error(y_val.iloc[: len(preds)], preds)
                maes.append(mae)
            except Exception:
                return 1e9
        return np.mean(maes)
