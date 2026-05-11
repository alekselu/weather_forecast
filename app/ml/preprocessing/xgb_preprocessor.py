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
        df = self.calendar_builder.transform(X.copy())
        print("Before target", len(X), len(y))
        df["target"] = y.values
        for lag in self.lags:
            df[f"lag_{lag}"] = df.groupby("city_id")["target"].shift(lag)
        for window in self.rolling_windows:
            group = df.groupby("city_id")["target"]
            df[f"roll_mean_{window}"] = group.shift(1).transform(
                lambda x: x.rolling(window).mean()
            )
            df[f"roll_std_{window}"] = group.shift(1).transform(
                lambda x: x.rolling(window).std()
            )
        # Encoding city_id as LabelEncoding or category type
        # df['city_id'] = df['city_id'].astype('category')
        df["diff_1"] = y.shift(1).diff(1)
        return df.dropna().drop(columns=["target", "date"], errors="ignore")
