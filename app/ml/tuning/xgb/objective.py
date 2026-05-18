import numpy as np

from sklearn.metrics import mean_absolute_error

from sklearn.model_selection import TimeSeriesSplit

from app.ml.models.xgb_forecaster import XGBForecaster


class XGBObjective:
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
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": (trial.suggest_float("colsample_bytree", 0.5, 1.0)),
            "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 1.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 1.0, log=True),
        }
        tscv = TimeSeriesSplit(n_splits=self.n_splits)
        maes = []
        for train_idx, val_idx in tscv.split(self.X):
            X_train = self.X.iloc[train_idx]
            X_val = self.X.iloc[val_idx]
            y_train = self.y.iloc[train_idx]
            y_val = self.y.iloc[val_idx]
            model = XGBForecaster(
                params=params,
            )
            model.fit(
                X_train,
                y_train,
            )
            preds = model.predict(
                X_future=X_val,
                X_history=X_train,
                y_history=y_train,
            )
            mae = mean_absolute_error(
                y_val.iloc[: len(preds)],
                preds,
            )
            maes.append(mae)
        return np.mean(maes)
