import optuna

from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit

from app.ml.models.xgb_forecaster import XGBForecaster


class XGBTuner:
    def __init__(
        self,
        target_column,
        df,
    ):
        self.target_column = target_column
        self.df = df

    def objective(self, trial):

        params = {
            "n_estimators": trial.suggest_int(
                "n_estimators",
                100,
                1000,
            ),
            "max_depth": trial.suggest_int(
                "max_depth",
                3,
                10,
            ),
            "learning_rate": trial.suggest_float(
                "learning_rate",
                0.001,
                0.1,
                log=True,
            ),
            "subsample": trial.suggest_float(
                "subsample",
                0.5,
                1.0,
            ),
            "colsample_bytree": trial.suggest_float(
                "colsample_bytree",
                0.5,
                1.0,
            ),
        }

        model = XGBForecaster(
            target_column=self.target_column,
            params=params,
        )

        scores = []

        tscv = TimeSeriesSplit(n_splits=3)

        for train_idx, test_idx in tscv.split(self.df):

            train_df = self.df.iloc[train_idx]
            test_df = self.df.iloc[test_idx]

            model.fit(train_df)

            preds = model.predict(
                history=train_df,
                horizon=len(test_df),
            )

            score = mean_absolute_error(
                test_df[self.target_column],
                preds,
            )

            scores.append(score)

        return sum(scores) / len(scores)

    def tune(self, n_trials=50):

        study = optuna.create_study(direction="minimize")

        study.optimize(
            self.objective,
            n_trials=n_trials,
        )

        return study.best_params
