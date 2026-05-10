import joblib

from statsmodels.tsa.statespace.sarimax import (
    SARIMAX,
)

from app.ml.preprocessing.sarimax_preprocessor import (
    SARIMAXPreprocessor,
)


class SARIMAXForecaster:
    def __init__(
        self,
        target_column,
        order=(1, 1, 1),
        seasonal_order=(1, 1, 1, 365),
    ):

        self.target_column = target_column

        self.order = order
        self.seasonal_order = seasonal_order

        self.preprocessor = SARIMAXPreprocessor()

        self.model = None
        self.results = None

    def fit(self, df):

        df = self.preprocessor.transform(df)

        y = df[self.target_column]

        X = df[
            [
                "day_sin",
                "day_cos",
                "weekday_sin",
                "weekday_cos",
                "month_sin",
                "month_cos",
            ]
        ]

        self.model = SARIMAX(
            endog=y,
            exog=X,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )

        self.results = self.model.fit(disp=False)

    def predict(
        self,
        future_covariates,
    ):

        future_covariates = self.preprocessor.transform(future_covariates)

        X_future = future_covariates[
            [
                "day_sin",
                "day_cos",
                "weekday_sin",
                "weekday_cos",
                "month_sin",
                "month_cos",
            ]
        ]

        forecast = self.results.forecast(
            steps=len(X_future),
            exog=X_future,
        )

        return forecast.tolist()

    def save(self, path):

        self.results.save(path)

    @classmethod
    def load(cls, path):

        obj = cls(target_column="unknown")

        obj.results = joblib.load(path)

        return obj
