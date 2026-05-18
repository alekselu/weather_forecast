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
        city_column: str = "city_id",
        lags=None,
        rolling_windows=None,
    ):
        self.city_column = city_column
        self.lags = lags or self.DEFAULT_LAGS
        self.rolling_windows = rolling_windows or self.DEFAULT_WINDOWS
        self.calendar_builder = CalendarFeatureBuilder()

    def transform(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ):
        df = self.calendar_builder.transform(X.copy())
        print("Before target", len(X), len(y))
        df["target"] = pd.to_numeric(y.values, errors="coerce")
        print(f"{df['target'].dtype = }")
        grouped = df.groupby(self.city_column)
        for lag in self.lags:
            df[f"lag_{lag}"] = grouped["target"].shift(lag)
        for window in self.rolling_windows:
            df[f"roll_mean_{window}"] = (
                grouped["target"]
                .shift(1)
                .rolling(window)
                .mean()
                .reset_index(level=0, drop=True)
            )
            df[f"roll_std_{window}"] = (
                grouped["target"]
                .shift(1)
                .rolling(window)
                .std()
                .reset_index(level=0, drop=True)
            )
        # df["diff_1"] = grouped["target"].shift(1).diff(1)
        df["diff_1"] = grouped["target"].shift(1).diff(1)
        dropped = df.dropna().drop(columns=["date"], errors="ignore")
        return dropped.drop(columns=["target"]), dropped["target"]
