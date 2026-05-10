import joblib
import pandas as pd

from xgboost import XGBRegressor

from app.ml.preprocessing.xgb_preprocessor import (
    XGBPreprocessor,
)


class XGBForecaster:
    def __init__(
        self,
        target_column,
        params=None,
    ):
        self.target_column = target_column

        self.preprocessor = XGBPreprocessor(target_column)

        self.params = params or {}

        self.model = XGBRegressor(**self.params)

    def fit(self, df):

        df = self.preprocessor.transform(df)

        X = df.drop(
            columns=[
                "date",
                self.target_column,
            ]
        )

        y = df[self.target_column]

        self.model.fit(X, y)

    def predict(
        self,
        history,
        future_covariates,
    ):

        history = history.copy()

        predictions = []

        for i in range(len(future_covariates)):

            combined = pd.concat(
                [
                    history,
                    future_covariates.iloc[: i + 1],
                ]
            )

            processed = self.preprocessor.transform(combined)

            latest = processed.iloc[-1:]

            X = latest.drop(
                columns=[
                    "date",
                    self.target_column,
                ]
            )

            pred = self.model.predict(X)[0]

            predictions.append(pred)

            next_row = future_covariates.iloc[i : i + 1].copy()

            next_row[self.target_column] = pred

            history = pd.concat([history, next_row])

        return predictions

    def save(self, path):

        joblib.dump(
            {
                "model": self.model,
                "target_column": self.target_column,
                "params": self.params,
            },
            path,
        )

    @classmethod
    def load(cls, path):

        data = joblib.load(path)

        obj = cls(
            target_column=data["target_column"],
            params=data["params"],
        )

        obj.model = data["model"]

        return obj
