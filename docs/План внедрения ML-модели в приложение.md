# План изменений компонентов для нового API `/forecast`

## Оглавление

1. [Обзор архитектуры](#1-обзор-архитектуры)
2. [Изменения в `app` (FastAPI-контейнер)](#2-изменения-в-app-fastapi-контейнер)
3. [ML-контейнер: структура и API](#3-ml-контейнер-структура-и-api)
4. [Механизм zero-downtime переобучения](#4-механизм-zero-downtime-переобучения)
5. [docker-compose.yml — секция `ml`](#5-docker-composeyml--секция-ml)
6. [Контракт между контейнерами](#6-контракт-между-контейнерами)
7. [Порядок внедрения](#7-порядок-внедрения)

---

## 1. Обзор архитектуры

```
┌──────────────────────────────────────────────────────────────┐
│  Client                                                      │
└────────────────────┬─────────────────────────────────────────┘
                     │ GET /forecast
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  weather_app  (FastAPI, порт 8000)                           │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │  /forecast   │  │ GeoCoder   │  │  MLClient (httpx)    │ │
│  │  endpoint    │─▶│ (внешний)  │  │  POST /predict       │ │
│  └──────────────┘  └────────────┘  └──────────┬───────────┘ │
└───────────────────────────────────────────────┼─────────────┘
                                                │ HTTP
                                                ▼
┌──────────────────────────────────────────────────────────────┐
│  weather_ml  (FastAPI, порт 8001)                            │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │ POST /predict│  │  ModelRegistry  (asyncio.Lock)       │ │
│  │ GET  /health │  │  ForecasterEnsemble  (активная)      │ │
│  │ POST /retrain│  │  ForecasterEnsemble  (staging)       │ │
│  └──────────────┘  └──────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  APScheduler: retrain job (cron)                        │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                     │ SQL
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  weather_db  (PostgreSQL)                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Изменения в `app` (FastAPI-контейнер)

### 2.1 `app/models/responses.py` — обновить `ForecastResponse`

```python
# БЫЛО
class ForecastResponse(BaseModel):
    time: date
    city: str
    country_code: str = "ru"
    params: list[str]
    coords: str
    payload: dict[str, Any]

# СТАЛО
class ForecastPayload(BaseModel):
    hourly: dict[str, list] = {}   # {"temperature_2m": [10.1, 10.4, ...]}
    daily:  dict[str, list] = {}   # {"temperature_2m_mean": [10.2, ...]}

class ForecastResponse(BaseModel):
    start_date:   date
    end_date:     date
    city:         str
    country_code: str = "ru"
    params:       list[str]
    coords:       str
    payload:      ForecastPayload
```

### 2.2 `app/params.py` — новый модуль классификации параметров

```python
"""Справочник параметров Open-Meteo и классификатор hourly/daily."""
from __future__ import annotations

# Источник: https://open-meteo.com/en/docs
# Поддерживать актуальность при изменении Open-Meteo API.
HOURLY_PARAMS: frozenset[str] = frozenset({
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "snowfall",
    "surface_pressure",
    "windspeed_10m",
    "winddirection_10m",
    "windgusts_10m",
    "cloudcover",
    "shortwave_radiation",
    "et0_fao_evapotranspiration",
    # ... дополнить по актуальной документации
})

DAILY_PARAMS: frozenset[str] = frozenset({
    "temperature_2m_mean",
    "temperature_2m_min",
    "temperature_2m_max",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "windspeed_10m_max",
    "windgusts_10m_max",
    "shortwave_radiation_sum",
    "et0_fao_evapotranspiration",
    # ... дополнить по актуальной документации
})


def classify_params(
    params: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """
    Разбивает список параметров на hourly, daily, unknown.

    Returns:
        (hourly, daily, unknown)
    """
    hourly, daily, unknown = [], [], []
    for p in params:
        if p in HOURLY_PARAMS:
            hourly.append(p)
        elif p in DAILY_PARAMS:
            daily.append(p)
        else:
            unknown.append(p)
    return hourly, daily, unknown
```

### 2.3 `app/clients/ml_client.py` — HTTP-клиент к ML-контейнеру

```python
"""Асинхронный клиент для обращения к ML-контейнеру."""
import httpx
from datetime import date
from pydantic import BaseModel

from app.models.responses import ForecastPayload


class MLPredictRequest(BaseModel):
    latitude:   float
    longitude:  float
    start_date: date
    end_date:   date
    hourly:     list[str] = []
    daily:      list[str] = []


class MLClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def predict(self, request: MLPredictRequest) -> ForecastPayload:
        response = await self._client.post(
            "/predict",
            json=request.model_dump(mode="json"),
        )
        response.raise_for_status()
        return ForecastPayload(**response.json())

    async def health(self) -> dict:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()
```

**Dependency injection** (`app/dependencies.py`):

```python
from functools import lru_cache
from app.clients.ml_client import MLClient

@lru_cache
def get_ml_client() -> MLClient:
    from app.config import settings
    return MLClient(base_url=settings.ML_SERVICE_URL)
```

**Lifespan** (`app/main.py`):

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # graceful shutdown
    client = get_ml_client()
    await client.aclose()

app = FastAPI(lifespan=lifespan)
```

### 2.4 `app/routers/forecast.py` — обновлённый эндпоинт

```python
from datetime import date
from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException, Query

from app.clients.ml_client import MLClient, MLPredictRequest
from app.dependencies import get_geo_coder, get_ml_client
from app.models.responses import ForecastResponse, ForecastPayload
from app.params import classify_params
from app.geocoder import GeoCoder, City

router = APIRouter()


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Get weather forecast for a city",
    responses={
        200: {"description": "Successful forecast",  "model": ForecastResponse},
        400: {"description": "Invalid input",         "model": ErrorResponse},
        404: {"description": "City not found",        "model": ErrorResponse},
        503: {"description": "ML model unavailable",  "model": ErrorResponse},
    },
)
async def get_forecast(
    city:         Annotated[str, Query(description="City name")],
    params:       Annotated[list[str], Query(description="Open-Meteo parameter names")] = [],
    start_date:   Annotated[date | None, Query(description="Start of forecast range (YYYY-MM-DD)")] = None,
    end_date:     Annotated[date | None, Query(description="End of forecast range (YYYY-MM-DD)")]   = None,
    time:         Annotated[date | None, Query(deprecated=True, description="Deprecated. Use start_date/end_date.")] = None,
    country_code: str = "ru",
    geocoder:     Annotated[GeoCoder,   Depends(get_geo_coder)]  = ...,
    ml_client:    Annotated[MLClient,   Depends(get_ml_client)]  = ...,
) -> ForecastResponse:
    # ── 1. Нормализация time → (start_date, end_date) ──────────────────────
    if time is not None and start_date is None and end_date is None:
        start_date = end_date = time

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=400,
            detail="Provide start_date and end_date (or the deprecated time parameter).",
        )
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be ≤ end_date.")

    # ── 2. Классификация параметров ─────────────────────────────────────────
    hourly_params, daily_params, unknown = classify_params(params)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown params: {unknown}")

    # ── 3. Геокодирование ───────────────────────────────────────────────────
    try:
        coords = await geocoder.fetch_location_from(City(city, country_code))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoder error: {e}")

    # ── 4. Запрос к ML-контейнеру ───────────────────────────────────────────
    ml_request = MLPredictRequest(
        latitude=coords.lat,
        longitude=coords.lon,
        start_date=start_date,
        end_date=end_date,
        hourly=hourly_params,
        daily=daily_params,
    )
    try:
        payload: ForecastPayload = await ml_client.predict(ml_request)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            raise HTTPException(status_code=503, detail="ML model is not available.")
        raise HTTPException(status_code=502, detail=f"ML service error: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML service unreachable: {e}")

    # ── 5. Ответ ────────────────────────────────────────────────────────────
    return ForecastResponse(
        start_date=start_date,
        end_date=end_date,
        city=city,
        country_code=country_code,
        params=params,
        coords=str(coords),
        payload=payload,
    )
```

---

## 3. ML-контейнер: структура и API

### 3.1 Структура директорий

```
ml_service/
├── Dockerfile
├── requirements.txt
├── app/
│   ├── main.py               # FastAPI app + lifespan (scheduler)
│   ├── config.py             # настройки (pydantic-settings)
│   ├── registry.py           # ModelRegistry — потокобезопасная замена ансамбля
│   ├── routers/
│   │   ├── predict.py        # POST /predict
│   │   ├── health.py         # GET  /health
│   │   └── retrain.py        # POST /retrain  (ручной триггер)
│   ├── schemas.py            # Pydantic-схемы запросов/ответов
│   ├── predictor.py          # оркестрация predict-потока
│   ├── trainer.py            # оркестрация retrain-потока
│   └── ml/                   # перенос существующего кода без изменений
│       ├── models/
│       │   └── xgb_forecaster.py
│       ├── ensemble.py       # ForecasterEnsemble
│       └── tuning/
```

### 3.2 `ml_service/app/schemas.py`

```python
from datetime import date
from pydantic import BaseModel, model_validator


class PredictRequest(BaseModel):
    latitude:   float
    longitude:  float
    start_date: date
    end_date:   date
    hourly:     list[str] = []
    daily:      list[str] = []

    @model_validator(mode="after")
    def check_dates(self) -> "PredictRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be ≤ end_date")
        if not self.hourly and not self.daily:
            raise ValueError("At least one of hourly or daily params must be provided")
        return self


class PredictResponse(BaseModel):
    hourly: dict[str, list] = {}
    daily:  dict[str, list] = {}


class HealthResponse(BaseModel):
    status:          str   # "ok" | "degraded" | "no_model"
    model_loaded:    bool
    model_version:   str
    retraining_now:  bool


class RetrainResponse(BaseModel):
    status:  str   # "started" | "already_running"
    message: str
```

### 3.3 `ml_service/app/registry.py` — потокобезопасный реестр моделей

Ключевой компонент: обеспечивает чтение предсказаний без блокировок,
а замену ансамбля — атомарно через `asyncio.Lock`.

```python
"""
ModelRegistry — zero-downtime замена ForecasterEnsemble.

Принцип:
  - _active  — текущий ансамбль, используется для предсказаний (только чтение).
  - _staging — новый ансамбль, собирается в фоне во время retraining.
  - promote() — атомарно заменяет _active на _staging под asyncio.Lock.

Предсказания (predict) берут _active без блокировки — read-only операция
безопасна даже при конкурентных запросах, т.к. Python GIL и неизменяемость
ссылки гарантируют консистентность снимка ансамбля на момент вызова.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.ml.ensemble import ForecasterEnsemble

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self) -> None:
        self._active:    Optional[ForecasterEnsemble] = None
        self._staging:   Optional[ForecasterEnsemble] = None
        self._lock:      asyncio.Lock = asyncio.Lock()
        self._version:   str  = "none"
        self._retraining: bool = False

    # ── Чтение (без блокировки) ─────────────────────────────────────────────
    @property
    def active(self) -> Optional[ForecasterEnsemble]:
        return self._active

    @property
    def version(self) -> str:
        return self._version

    @property
    def retraining(self) -> bool:
        return self._retraining

    def is_ready(self) -> bool:
        return self._active is not None

    # ── Инициализация при старте ────────────────────────────────────────────
    async def load_from_disk(self, path: str) -> None:
        """Загрузить сохранённый ансамбль при старте контейнера."""
        ensemble = ForecasterEnsemble.load(path)  # см. 3.5
        async with self._lock:
            self._active  = ensemble
            self._version = self._read_version(path)
        logger.info("Model loaded from %s (version=%s)", path, self._version)

    # ── Переобучение и атомарная подмена ───────────────────────────────────
    async def begin_retraining(self) -> bool:
        """Возвращает False, если переобучение уже идёт."""
        async with self._lock:
            if self._retraining:
                return False
            self._retraining = True
        return True

    def set_staging(self, ensemble: ForecasterEnsemble) -> None:
        """Вызывается из потока обучения (executor) — без await."""
        self._staging = ensemble

    async def promote(self, version: str) -> None:
        """Атомарно заменить _active на _staging."""
        async with self._lock:
            if self._staging is None:
                raise RuntimeError("No staging model to promote")
            self._active    = self._staging
            self._staging   = None
            self._version   = version
            self._retraining = False
        logger.info("Model promoted to version=%s", version)

    async def abort_retraining(self) -> None:
        async with self._lock:
            self._staging    = None
            self._retraining = False

    @staticmethod
    def _read_version(path: str) -> str:
        import os, json
        meta = os.path.join(path, "meta.json")
        if os.path.exists(meta):
            with open(meta) as f:
                return json.load(f).get("version", "unknown")
        return datetime.utcnow().strftime("%Y%m%dT%H%M%S")
```

### 3.4 `ml_service/app/predictor.py`

```python
"""Оркестрация predict-потока: данные → ForecasterEnsemble → ответ."""
from datetime import date, timedelta
from typing import Any
import pandas as pd

from app.registry import ModelRegistry
from app.schemas import PredictRequest, PredictResponse


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

        # Формируем X_future для каждого запрошенного таргета
        # Конкретная логика зависит от препроцессора — здесь скелет
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
            result.daily[target] = [
                round(float(v), 2) for v in preds
            ]

        for target in request.hourly:
            # Почасовые аналогично; X_future уже почасовой
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

    # Эти методы реализуются в зависимости от источника исторических данных
    def _build_features(self, lat, lon, dates) -> pd.DataFrame:
        raise NotImplementedError

    def _build_hourly_features(self, lat, lon, dates) -> pd.DataFrame:
        raise NotImplementedError

    def _load_history(self, lat, lon, target) -> tuple[pd.DataFrame, pd.Series]:
        raise NotImplementedError

    def _load_history_hourly(self, lat, lon, target) -> tuple[pd.DataFrame, pd.Series]:
        raise NotImplementedError
```

### 3.5 `ml_service/app/trainer.py` — переобучение без даунтайма

```python
"""Фоновое переобучение + атомарная подмена модели."""
import asyncio
import logging
from datetime import datetime

from app.registry import ModelRegistry
from app.ml.ensemble import ForecasterEnsemble

logger = logging.getLogger(__name__)


class Trainer:
    def __init__(self, registry: ModelRegistry, model_path: str) -> None:
        self._registry   = registry
        self._model_path = model_path

    async def run(self) -> None:
        """Запускается планировщиком (APScheduler) или POST /retrain."""
        started = await self._registry.begin_retraining()
        if not started:
            logger.warning("Retraining already in progress, skipping.")
            return

        logger.info("Retraining started.")
        loop = asyncio.get_running_loop()
        try:
            # Тяжёлая CPU-работа — в пул потоков, чтобы не блокировать event loop
            new_ensemble = await loop.run_in_executor(
                None,                      # ThreadPoolExecutor по умолчанию
                self._train_blocking,
            )
            version = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            self._registry.set_staging(new_ensemble)
            await self._registry.promote(version)
            self._save(new_ensemble, version)
            logger.info("Retraining complete. New version: %s", version)
        except Exception as e:
            logger.exception("Retraining failed: %s", e)
            await self._registry.abort_retraining()

    def _train_blocking(self) -> ForecasterEnsemble:
        """
        Синхронный блок обучения — выполняется в executor.
        Здесь используется существующий ForecasterEnsemble + XGBTuner.
        """
        from app.ml.ensemble import ForecasterEnsemble
        from app.ml.models.xgb_forecaster import XGBForecaster
        from app.ml.tuning.xgb.tuner import XGBTuner
        # ... загрузить данные из БД, обучить, вернуть новый ансамбль
        ensemble = ForecasterEnsemble()
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
```

**Добавить `save`/`load` в `ForecasterEnsemble`:**

```python
# ml_service/app/ml/ensemble.py — дополнение к существующему классу
import joblib, os

class ForecasterEnsemble:
    # ... существующий код ...

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        joblib.dump(self, os.path.join(path, "ensemble.pkl"))

    @classmethod
    def load(cls, path: str) -> "ForecasterEnsemble":
        return joblib.load(os.path.join(path, "ensemble.pkl"))
```

### 3.6 `ml_service/app/main.py`

```python
"""FastAPI-приложение ML-контейнера с планировщиком переобучения."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.registry import ModelRegistry
from app.trainer import Trainer
from app.predictor import Predictor
from app.routers import predict, health, retrain

registry  = ModelRegistry()
trainer   = Trainer(registry, model_path=settings.MODEL_PATH)
predictor = Predictor(registry)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Старт ──────────────────────────────────────────────────────────────
    import os
    ensemble_pkl = os.path.join(settings.MODEL_PATH, "ensemble.pkl")
    if os.path.exists(ensemble_pkl):
        await registry.load_from_disk(settings.MODEL_PATH)
    else:
        # Первый запуск — обучить немедленно
        await trainer.run()

    # ── Планировщик переобучения ────────────────────────────────────────────
    scheduler.add_job(
        trainer.run,
        trigger="cron",
        hour=settings.RETRAIN_HOUR,     # напр. 2 (02:00 UTC)
        minute=settings.RETRAIN_MINUTE, # напр. 0
        id="retrain",
        replace_existing=True,
    )
    scheduler.start()

    yield

    # ── Остановка ──────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)


app = FastAPI(title="Weather ML Service", lifespan=lifespan)

# Внедрение зависимостей через app.state
@app.on_event("startup")
async def attach_state():
    app.state.registry  = registry
    app.state.predictor = predictor
    app.state.trainer   = trainer

app.include_router(predict.router)
app.include_router(health.router)
app.include_router(retrain.router)
```

### 3.7 Роутеры ML-контейнера

**`ml_service/app/routers/predict.py`**

```python
from fastapi import APIRouter, Request, HTTPException
from app.schemas import PredictRequest, PredictResponse

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request) -> PredictResponse:
    predictor = request.app.state.predictor
    if not request.app.state.registry.is_ready():
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    try:
        return predictor.predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**`ml_service/app/routers/health.py`**

```python
from fastapi import APIRouter, Request
from app.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    reg = request.app.state.registry
    return HealthResponse(
        status="ok" if reg.is_ready() else "no_model",
        model_loaded=reg.is_ready(),
        model_version=reg.version,
        retraining_now=reg.retraining,
    )
```

**`ml_service/app/routers/retrain.py`**

```python
from fastapi import APIRouter, Request, BackgroundTasks
from app.schemas import RetrainResponse

router = APIRouter()

@router.post("/retrain", response_model=RetrainResponse)
async def retrain(request: Request, bg: BackgroundTasks) -> RetrainResponse:
    trainer = request.app.state.trainer
    bg.add_task(trainer.run)
    return RetrainResponse(status="started", message="Retraining scheduled in background")
```

### 3.8 `ml_service/app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MODEL_PATH:      str = "/models"
    RETRAIN_HOUR:    int = 2
    RETRAIN_MINUTE:  int = 0
    DB_HOST:         str
    DB_PORT:         int = 5432
    DB_NAME:         str
    DB_USER:         str
    DB_PASSWORD:     str

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 4. Механизм zero-downtime переобучения

```
t=0   Запрос предсказания → берётся _active (v1), без блокировки
      │
t=1   Планировщик / POST /retrain → begin_retraining() → _retraining=True
      │
t=2   run_in_executor(_train_blocking) запускается в ThreadPool
      │  (event loop свободен — /predict продолжает обслуживать запросы из _active v1)
      │
t=N   Обучение завершено → set_staging(new_ensemble)
      │
t=N+ε promote() под asyncio.Lock:
      │   _active = _staging   ← атомарная замена ссылки
      │   _staging = None
      │   _version = "20250515T020000"
      │   _retraining = False
      │
t=N+ε+1 Новые запросы предсказания → берётся _active (v2)
         Запросы, начавшиеся в t<N — завершаются на v1 (Python-ссылка стабильна)
```

**Почему это безопасно без RWLock:**
- `_active` — простая ссылка на объект; Python GIL гарантирует атомарность присваивания ссылки.
- `promote()` выполняется в единственном event loop под `asyncio.Lock` — не может выполниться дважды параллельно.
- `predict()` читает `self._active` один раз в начале вызова и держит локальную ссылку; даже если `promote()` сработает в середине — текущий запрос дочитает v1, следующий получит v2.

---

## 5. docker-compose.yml — секция `ml`

```yaml
  ml:
    build:
      context: ml_service
      dockerfile: Dockerfile
    container_name: weather_ml
    restart: always
    depends_on:
      db:
        condition: service_healthy
    environment:
      DB_HOST:        db
      DB_PORT:        ${POSTGRES_PORT}
      DB_NAME:        ${POSTGRES_DB}
      DB_USER:        ${POSTGRES_USER}
      DB_PASSWORD:    ${POSTGRES_PASSWORD}
      MODEL_PATH:     /models
      RETRAIN_HOUR:   ${ML_RETRAIN_HOUR:-2}
      RETRAIN_MINUTE: ${ML_RETRAIN_MINUTE:-0}
      LOG_LEVEL:      ${LOG_LEVEL:-INFO}
    volumes:
      - ml_models:/models          # персистентное хранилище весов
    ports:
      - "8001:8001"                # не публиковать наружу в prod (internal only)
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s            # время на первичную загрузку/обучение модели
```

Добавить `ml_models` в раздел `volumes` корневого `docker-compose.yml`:

```yaml
volumes:
  postgres_data:
  ml_models:        # ← добавить
```

Обновить зависимость `app`:

```yaml
  app:
    depends_on:
      db:
        condition: service_healthy
      ml:
        condition: service_healthy   # ← добавить
    environment:
      ML_SERVICE_URL: http://ml:8001  # ← добавить
```

### `ml_service/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### `ml_service/requirements.txt`

```
fastapi>=0.111
uvicorn[standard]>=0.29
httpx>=0.27
pydantic>=2.7
pydantic-settings>=2.2
apscheduler>=3.10
xgboost>=2.0
scikit-learn>=1.4
pandas>=2.2
optuna>=3.6
joblib>=1.4
psycopg2-binary>=2.9
sqlalchemy>=2.0
```

---

## 6. Контракт между контейнерами

### Запрос `app` → `ml` (`POST /predict`)

```json
{
  "latitude":   55.75,
  "longitude":  37.62,
  "start_date": "2025-05-15",
  "end_date":   "2025-05-21",
  "hourly":     ["temperature_2m", "precipitation"],
  "daily":      ["temperature_2m_mean", "temperature_2m_max"]
}
```

### Ответ `ml` → `app`

```json
{
  "hourly": {
    "temperature_2m":  [12.1, 13.4, 14.0, ...],   // 7 дней × 24 ч = 168 значений
    "precipitation":   [0.0,  0.1,  0.0,  ...]
  },
  "daily": {
    "temperature_2m_mean": [13.2, 14.1, 12.8, 11.5, 10.9, 12.3, 13.7],
    "temperature_2m_max":  [17.1, 18.3, 16.9, 15.2, 14.8, 16.1, 17.5]
  }
}
```

---

## 7. Порядок внедрения

| Шаг | Что делаем | Блокирует |
|-----|-----------|-----------|
| **1** | Создать `ml_service/` со скелетом (schemas, registry, health) — ML отвечает на `/health` | — |
| **2** | Добавить `ml` в docker-compose, проверить healthcheck | Шаг 1 |
| **3** | Реализовать `ForecasterEnsemble.save/load`, базовый `Trainer._train_blocking` | Шаг 1 |
| **4** | Реализовать `Predictor.predict` + роутер `/predict` | Шаги 1–3 |
| **5** | Обновить `ForecastResponse`, добавить `app/params.py` | — |
| **6** | Реализовать `MLClient`, обновить эндпоинт `/forecast` | Шаги 4–5 |
| **7** | Настроить `APScheduler` в `ml/main.py` | Шаг 3 |
| **8** | Написать интеграционные тесты (`app` ↔ mock ML, ML ↔ mock DB) | Шаги 4–6 |
| **9** | Load test: `/predict` под нагрузкой во время `POST /retrain` | Шаги 4, 7 |
