import pandas as pd

from app.ml.preprocessing.calendar_features import (
    CalendarFeatureBuilder,
)
from app.ml.preprocessing.dataset_preprocessor import DatasetPreprocessor


class XGBPreprocessor(DatasetPreprocessor):
    DEFAULT_LAGS = [1, 2, 3, 7, 14, 30]
    DEFAULT_WINDOWS = [3, 7, 14]

    def __init__(
        self,
        lags=None,
        rolling_windows=None,
    ):
        self.lags = lags or self.DEFAULT_LAGS
        self.rolling_windows = rolling_windows or self.DEFAULT_WINDOWS

        self.calendar_builder = CalendarFeatureBuilder()

    def transform(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ):
        X = X.copy()
        X = self.calendar_builder.transform(X)
        for lag in self.lags:
            X[f"lag_{lag}"] = y.shift(lag)

        for window in self.rolling_windows:
            X[f"roll_mean_{window}"] = y.shift(1).rolling(window).mean()

            X[f"roll_std_{window}"] = y.shift(1).rolling(window).std()

        # X["diff_1"] = (
        #     y.diff(1)
        # )
        X = X.dropna()
        X = X.drop(
            columns=[
                "date",
            ]
        )
        return X, y
