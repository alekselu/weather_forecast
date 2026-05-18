"""Background retraining + atomic model swap."""
import asyncio
import logging
import datetime
from app.ml.registry import ModelRegistry
from app.ml.models.forecaster_ensemble import ForecasterEnsemble
from app.db.session import ConnectionParams, get_db_connections
from app.db.models.city import City
from app.db.models.weather_daily import WeatherDaily
from app.ml.models.sarimax_forecaster import SARIMAXForecaster
from app.ml.models.xgb_forecaster import XGBForecaster
from sqlalchemy import select
from app.params import DAILY_PARAMS
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class Trainer:
    def __init__(self, registry: ModelRegistry, model_path: str) -> None:
        self._registry = registry
        self._model_path = model_path

    async def run(self) -> None:
        """Launched by planner (APScheduler) or POST /retrain."""
        started = await self._registry.begin_retraining()
        if not started:
            logger.warning("Retraining already in progress, skipping.")
            return
        logger.info("Retraining started.")
        loop = asyncio.get_running_loop()
        try:
            new_ensemble = await loop.run_in_executor(
                None,  # ThreadPoolExecutor by default
                self._train_blocking,
            )
            version = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y%m%dT%H%M%S"
            )
            self._registry.set_staging(new_ensemble)
            await self._registry.promote(version)
            self._save(new_ensemble, version)
            logger.info("Retraining complete. New version: %s", version)
        except Exception as e:
            logger.exception("Retraining failed: %s", e)
            await self._registry.abort_retraining()

    def _train_blocking(self) -> ForecasterEnsemble:
        """
        WARNING: Сейчас без настройки параметров.

        Sync training block - run in executor.
        Uses existing ForecasterEnsemble + XGBTuner.
        """
        from app.ml.models.forecaster_ensemble import ForecasterEnsemble
        from app.ml.models.xgb_forecaster import XGBForecaster
        from app.ml.tuning.xgb.tuner import XGBTuner

        # ... загрузить данные из БД, обучить, вернуть новый ансамбль
        # WARNING берем данные из файла, пока их нет в БД
        # conn = get_db_connections()
        # with conn.session_scope() as session:
        #     stmt = select(
        #         WeatherDaily.date,
        #         # информация о городе
        #         City.id.label("city_id"),
        #         City.name.label("city_name"),
        #         City.latitude,
        #         City.longitude,
        #         # погодные данные
        #         WeatherDaily.temperature_2m_mean,
        #         WeatherDaily.temperature_2m_min,
        #         WeatherDaily.temperature_2m_max,
        #         WeatherDaily.precipitation_sum,
        #         WeatherDaily.rain_sum,
        #         WeatherDaily.snowfall_sum,
        #         WeatherDaily.precipitation_hours,
        #         WeatherDaily.wind_speed_10m_max,
        #         WeatherDaily.relative_humidity_2m_mean,
        #         WeatherDaily.sunshine_duration,
        #     ).join(City, WeatherDaily.city_id == City.id)
        #     df = pd.read_sql(stmt, session.bind)
        print("Training...")
        df = pd.read_csv(
            Path(__file__).parent.parent.parent / "tests/fixtures/data_2023_2026.csv",
            parse_dates=["time"],
            date_format="%Y-%m-%d",
        ).rename(columns={"time": "date"})
        df["city_name"] = "Saint Petersburg"

        # Далее без изменений
        city_dfs = {
            city: group.reset_index(drop=True)
            for city, group in df.groupby("city_name")
        }

        ensemble = ForecasterEnsemble()
        for city, city_df in city_dfs:
            for target in DAILY_PARAMS:
                X = city_df[["date", "latitude", "longitude"]]
                y = city_df[target]
                lat = city_df.iloc[0]["latitude"]
                lon = city_df.iloc[0]["longitude"]
                model = SARIMAXForecaster()
                model.fit(X, y)
                # WARNING заменить на название города или его id?
                ensemble.register_model(target=target, model=model, city=f"{lat},{lon}")
        # пример:
        # for target in TARGETS:
        #     X, y = load_training_data(target)
        #     tuner = XGBTuner(target=target, n_trials=50)
        #     result = tuner.tune(X, y)
        #     model = XGBForecaster(params=result.best_params)
        #     model.fit(X, y)
        #     ensemble.register_model(target, model)
        return ensemble

    def _save(self, ensemble: ForecasterEnsemble, version: str) -> None:
        import os, json, joblib

        path = self._model_path
        os.makedirs(path, exist_ok=True)
        joblib.dump(ensemble, os.path.join(path, "ensemble.pkl"))
        with open(os.path.join(path, "meta.json"), "w") as f:
            json.dump({"version": version}, f)
