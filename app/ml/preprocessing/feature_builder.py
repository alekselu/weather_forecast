import pandas as pd


DEFAULT_LAGS = [1, 2, 3, 7, 14, 30]
DEFAULT_WINDOWS = [3, 7, 14]


class FeatureBuilder:
    def __init__(
        self,
        target_column: str,
        lags=None,
        rolling_windows=None,
    ):
        self.target_column = target_column
        self.lags = lags or DEFAULT_LAGS
        self.rolling_windows = rolling_windows or DEFAULT_WINDOWS

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # лаги
        for lag in self.lags:
            df[f"{self.target_column}_lag_{lag}"] = df[self.target_column].shift(lag)

        # rolling
        for window in self.rolling_windows:
            df[f"{self.target_column}_roll_mean_{window}"] = (
                df[self.target_column].shift(1).rolling(window).mean()
            )

            df[f"{self.target_column}_roll_std_{window}"] = (
                df[self.target_column].shift(1).rolling(window).std()
            )

        # diff
        df[f"{self.target_column}_diff_1"] = df[self.target_column].diff(1)

        # календарь
        df["month"] = df["date"].dt.month
        df["weekday"] = df["date"].dt.weekday
        df["day_of_year"] = df["date"].dt.dayofyear

        return df.dropna()
