from app.ml.preprocessing.calendar_features import (
    CalendarFeatureBuilder,
)


class SARIMAXPreprocessor:
    def transform(self, df):
        df = CalendarFeatureBuilder.add_features(df)
        return df
