import pandas as pd

from app.ml.preprocessing.calendar_features import (
    CalendarFeatureBuilder,
)


class XGBPreprocessor:

    LAGS = [1, 2, 3, 7, 14, 30]
    WINDOWS = [3, 7, 14]

    def __init__(self, target_column):
        self.target_column = target_column

    def transform(self, df):

        df = df.copy()

        df = CalendarFeatureBuilder.add_features(df)

        for lag in self.LAGS:
            df[f"lag_{lag}"] = df[self.target_column].shift(lag)

        for window in self.WINDOWS:

            df[f"roll_mean_{window}"] = (
                df[self.target_column].shift(1).rolling(window).mean()
            )

            df[f"roll_std_{window}"] = (
                df[self.target_column].shift(1).rolling(window).std()
            )

        df["diff_1"] = df[self.target_column].diff()

        return df.dropna()
