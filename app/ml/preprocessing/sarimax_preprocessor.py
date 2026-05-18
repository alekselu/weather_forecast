import pandas as pd

from app.ml.preprocessing.calendar_features import (
    CalendarFeatureBuilder,
)
from app.ml.preprocessing.dataset_preprocessor import DatasetPreprocessor


class SARIMAXPreprocessor(DatasetPreprocessor):
    def __init__(self):
        self.calendar_builder = CalendarFeatureBuilder()

    def transform(
        self,
        X: pd.DataFrame,
        y: pd.Series = None,
    ):
        X = X.copy()
        X = self.calendar_builder.transform(X)
        X = X.drop(
            columns=[
                "date",
            ]
        )
        return X, y
