"""Orchestration of predict-flow: data -> ForecasterEnsemble -> Response."""
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
from app.params import classify_params
from app.ml.registry import ModelRegistry
from app.schemas.forecast import PredictRequest, PredictResponse


def _date_range(start: date, end: date) -> list[date]:
    delta = (end - start).days + 1
    return [start + timedelta(days=i) for i in range(delta)]


class Predictor:
    def __init__(self, registry: ModelRegistry) -> None:
        self._registry = registry

    def predict(self, request: PredictRequest) -> PredictResponse:
        ensemble = self._registry.active
        if ensemble is None:
            raise RuntimeError("Model not loaded")
        dates = _date_range(request.start_date, request.end_date)
        X_future = self._build_features(request.latitude, request.longitude, dates)
        result = PredictResponse()
        for target in request.daily:
            X_history, y_history = self._load_history(
                request.latitude, request.longitude, target
            )
            preds = ensemble.predict(
                city=f"{request.latitude},{request.longitude}",
                target=target,
                X_future=X_future,
                X_history=X_history,
                y_history=y_history,
            )
            result.daily[target] = [round(float(v), 2) for v in preds]
        for target in request.hourly:
            X_future_h = self._build_hourly_features(
                request.latitude, request.longitude, dates
            )
            X_history_h, y_history_h = self._load_history_hourly(
                request.latitude, request.longitude, target
            )
            preds = ensemble.predict(
                city=f"{request.latitude},{request.longitude}",
                target=target,
                X_future=X_future_h,
                X_history=X_history_h,
                y_history=y_history_h,
            )
            result.hourly[target] = [round(float(v), 2) for v in preds]

        return result

    def _build_features(self, lat, lon, dates) -> pd.DataFrame:
        df = pd.DataFrame()
        df["date"] = dates
        df["lat"] = lat
        df["lon"] = lon
        return df

    def _build_hourly_features(self, lat, lon, dates) -> pd.DataFrame:
        return self._build_features(lat=lat, lon=lon, dates=dates)

    def _load_history(self, lat, lon, target) -> tuple[pd.DataFrame, pd.Series]:
        """WARNING: Заглушка до тех пор, пока данные не будут положены в БД."""
        df = pd.read_csv(
            Path(__file__).parent.parent.parent / "tests/fixtures/data_2023_2026.csv",
            parse_dates=["time"],
            date_format="%Y-%m-%d",
        ).rename(columns={"time": "date"})
        df["lat"] = lat
        df["lon"] = lon
        return df.drop(columns=[target]), df[target]

    def _load_history_hourly(self, lat, lon, target) -> tuple[pd.DataFrame, pd.Series]:
        raise NotImplementedError
