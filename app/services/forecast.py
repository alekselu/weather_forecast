from app.ml.model_selector import ModelSelector
from datetime import date
import datetime
from pathlib import Path
import pandas as pd
import numpy as np


class Forecast:
    def __init__(self):
        self.model_selector = ModelSelector()

    def _create_features_final(self, df):
        df = df.copy()
        df["target"] = df["temperature_2m_mean"].shift(-1)

        time_periods = {"day_of_year": 365.25, "month": 12, "weekday": 7}
        for col, period in time_periods.items():
            if col == "day_of_year":
                values = df.index.dayofyear
            elif col == "month":
                values = df.index.month
            else:
                values = df.index.weekday

            df[f"{col}_sin"] = np.sin(2 * np.pi * values / period)
            df[f"{col}_cos"] = np.cos(2 * np.pi * values / period)

        for w in [3, 7, 14]:
            df[f"roll_mean_{w}"] = df["temperature_2m_mean"].rolling(w).mean()
            df[f"roll_std_{w}"] = df["temperature_2m_mean"].rolling(w).std()

        df["diff_1"] = df["temperature_2m_mean"].diff(1)
        # df["day_of_year"] = df.index.dayofyear
        # df["month"] = df.index.month
        # df["weekday"] = df.index.weekday
        for lag in [1, 2, 3, 7, 14, 30]:
            df[f"lag_{lag}"] = df["temperature_2m_mean"].shift(lag)

        df = df.dropna()
        return df.drop(columns=["target"]), df["target"]

    def _forecast_with_decay(self, last_values, mean_values, horizon, decay_rate=0.95):
        """
        Создает прогноз экзогенных переменных с затуханием к среднему
        """
        exog_forecast = []
        current_value = last_values.copy()

        for i in range(horizon):
            # Постепенное затухание к среднему
            current_value = current_value * decay_rate + mean_values * (1 - decay_rate)
            exog_forecast.append(current_value.copy())

        return np.array(exog_forecast)

    def predict(self, time: date):
        df = pd.read_csv(
            Path(__file__).parent / "../../experiments/data_2023_2026.csv",
            parse_dates=["time"],
            date_format="%Y-%m-%d",
        )
        df = df.sort_values("time")
        df = df.set_index("time")
        df["temperature_2m_mean"] = df["temperature_2m_mean (°C)"]
        df = df.drop(columns=["temperature_2m_mean (°C)"])
        X, y = self._create_features_final(df)
        if "temperature_2m_mean" not in df.columns:
            raise ValueError("No column temperature_2m_mean")
        self.model_selector.train(X, y)

        last_date = df.index[-1]
        if isinstance(last_date, pd.Timestamp):
            last_date = last_date.date()
        days_diff = (time - last_date).days

        last_exog = df.iloc[-1:].values
        mean_exog = df.mean().values

        exog_forecast = self._forecast_with_decay(
            last_exog, mean_exog, horizon=days_diff, decay_rate=0.9
        )
        return self.model_selector.predict(exog_forecast)
