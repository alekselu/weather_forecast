import pandas as pd

from app.ml.preprocessing.cyclic_features import (
    CyclicFeatureEncoder,
)


class CalendarFeatureBuilder:
    def transform(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:

        df = df.copy()

        df["month"] = df["date"].dt.month
        df["weekday"] = df["date"].dt.weekday
        df["day_of_year"] = df["date"].dt.dayofyear

        df = CyclicFeatureEncoder.encode(
            df,
            "month",
            12,
        )

        df = CyclicFeatureEncoder.encode(
            df,
            "weekday",
            7,
        )

        df = CyclicFeatureEncoder.encode(
            df,
            "day_of_year",
            365,
        )

        return df
