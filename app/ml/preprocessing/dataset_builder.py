import pandas as pd
from app.ml.preprocessing.feature_builder import FeatureBuilder


class DatasetBuilder:
    def __init__(self, target_column: str):
        self.target_column = target_column

    def build(self, df: pd.DataFrame):
        builder = FeatureBuilder(target_column=self.target_column)

        df = builder.transform(df)

        exclude = [
            "date",
            self.target_column,
        ]

        X = df.drop(columns=exclude)
        y = df[self.target_column]

        return X, y
