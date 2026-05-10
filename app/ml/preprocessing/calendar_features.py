import numpy as np


class CalendarFeatureBuilder:
    @staticmethod
    def add_features(df):

        df = df.copy()

        df["day_of_year"] = df["date"].dt.dayofyear
        df["weekday"] = df["date"].dt.weekday
        df["month"] = df["date"].dt.month

        # day of year
        df["day_sin"] = np.sin(2 * np.pi * df["day_of_year"] / 365)

        df["day_cos"] = np.cos(2 * np.pi * df["day_of_year"] / 365)

        # weekday
        df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)

        df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)

        # month
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)

        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

        return df
