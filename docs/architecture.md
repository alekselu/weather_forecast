# Weather Forecast System — Architecture

## Процессы системы

| # | Процесс | Триггер | Участники |
|---|---------|---------|-----------|
| P1 | **Forecast Request** | Пользователь / внешняя система | CLI / REST API → ForecastService → ModelRegistry → DB |
| P2 | **Daily Data Ingestion** | Cron 06:00 UTC+3 | Scheduler → Open-Meteo API → DataIngestionService → DB |
| P3 | **Weekly Retraining** | Cron Sunday 02:00 UTC+3 | Scheduler → TrainingService → DB → ModelRegistry |
| P4 | **Model Hot-Swap** | После обучения | TrainingService → ModelRegistry (atomic replace) |
| P5 | **Quality Monitoring** | После каждого прогноза | MonitoringService → DB (MAE log) → Alert (log warning) |
| P6 | **Geo Resolution** | При первом упоминании города | GeoService → geopy → DB (cache) |

---

## Диаграмма компонентов

```mermaid
graph TB
    subgraph USER["👤 Пользователи"]
        CLI["CLI Client<br/>(weather_cli.py)"]
        EXT["Внешние системы<br/>(HTTP clients)"]
    end

    subgraph API["🌐 API Layer — FastAPI"]
        EP_FORECAST["GET /forecast<br/>?city=&date="]
        EP_HEALTH["GET /health"]
        EP_METRICS["GET /metrics"]
        MW["Middleware<br/>(validation, error handling)"]
    end

    subgraph CORE["⚙️ Core Services"]
        FS["ForecastService"]
        GS["GeoService"]
        MS["MonitoringService"]
        TS["TrainingService"]
        DIS["DataIngestionService"]
    end

    subgraph ML["🤖 ML Layer"]
        MR["ModelRegistry<br/>(hot-swap)"]
        STUB["ModelStub<br/>(заглушка v0)"]
        XGBM["XGBoost/LightGBM<br/>(v1+)"]
        FE["FeatureEngineer<br/>(лаги, скользящие средние)"]
        BL["BaselineModel<br/>(tomorrow = today)"]
    end

    subgraph DATA["🗄️ Data Layer"]
        PG[("PostgreSQL<br/>weather_observations<br/>forecast_log<br/>model_versions<br/>geo_cache")]
        OME["Open-Meteo API<br/>(Historical + Daily)"]
        GEOPY["geopy<br/>(geocoding)"]
    end

    subgraph SCHED["⏰ Scheduler"]
        CRON_D["Daily 06:00<br/>Data Ingestion"]
        CRON_W["Weekly Sunday 02:00<br/>Model Retraining"]
    end

    CLI -->|HTTP| EP_FORECAST
    EXT -->|HTTP| EP_FORECAST
    EXT -->|HTTP| EP_HEALTH

    EP_FORECAST --> MW
    MW --> FS
    FS --> GS
    FS --> MR
    FS --> FE
    FS --> MS

    GS --> GEOPY
    GS --> PG

    MR --> STUB
    MR --> XGBM

    FE --> PG

    MS --> PG

    CRON_D --> DIS
    DIS --> OME
    DIS --> PG

    CRON_W --> TS
    TS --> PG
    TS --> FE
    TS --> MR
    TS --> BL

    style USER fill:#1a1a2e,stroke:#e94560,color:#fff
    style API fill:#16213e,stroke:#0f3460,color:#fff
    style CORE fill:#0f3460,stroke:#533483,color:#fff
    style ML fill:#533483,stroke:#e94560,color:#fff
    style DATA fill:#1a1a2e,stroke:#0f3460,color:#fff
    style SCHED fill:#16213e,stroke:#533483,color:#fff
```

---

## Диаграмма последовательности — P1: Forecast Request

```mermaid
sequenceDiagram
    actor User
    participant CLI
    participant API as FastAPI /forecast
    participant FS as ForecastService
    participant GS as GeoService
    participant FE as FeatureEngineer
    participant MR as ModelRegistry
    participant DB as PostgreSQL
    participant MON as MonitoringService

    User->>CLI: weather_cli --city "Saint Petersburg"
    CLI->>API: GET /forecast?city=Saint+Petersburg

    API->>FS: get_forecast(city, date=tomorrow)

    FS->>GS: resolve_city("Saint Petersburg")
    GS-->>DB: SELECT FROM geo_cache WHERE city=...
    alt кэш пуст
        GS->>GS: geopy.geocode(city)
        GS-->>DB: INSERT INTO geo_cache
    end
    GS-->>FS: {lat, lon}

    FS->>FE: build_features(lat, lon, date)
    FE-->>DB: SELECT last 30 days observations
    FE-->>FS: feature_vector

    FS->>MR: predict(feature_vector)
    MR-->>FS: avg_temperature_c

    FS->>MON: log_forecast(city, date, prediction)
    MON-->>DB: INSERT INTO forecast_log

    FS-->>API: ForecastResponse
    API-->>CLI: 200 JSON
    CLI-->>User: "Saint Petersburg, 2026-04-27: +8.3°C"
```

---

## Диаграмма последовательности — P2: Daily Data Ingestion

```mermaid
sequenceDiagram
    participant CRON as Scheduler (06:00)
    participant DIS as DataIngestionService
    participant OME as Open-Meteo API
    participant DB as PostgreSQL
    participant MON as MonitoringService

    CRON->>DIS: run_daily_ingestion()
    DIS->>DB: SELECT last ingested date
    DIS->>OME: GET /archive?lat=&lon=&start=yesterday&end=yesterday
    
    alt API доступен
        OME-->>DIS: {date, temperature_mean}
        DIS-->>DB: UPSERT weather_observations
        DIS->>MON: update_mae_metrics()
        MON-->>DB: SELECT forecast_log WHERE date=yesterday
        MON-->>DB: UPDATE mae_log
        alt MAE > 3.5°C
            MON->>MON: LOG WARNING "MAE threshold exceeded"
        end
    else API недоступен
        DIS->>DIS: LOG ERROR, retry next run
        Note over DIS: API не блокирует forecast endpoint
    end
```

---

## Диаграмма последовательности — P3: Weekly Retraining

```mermaid
sequenceDiagram
    participant CRON as Scheduler (Sunday 02:00)
    participant TS as TrainingService
    participant DB as PostgreSQL
    participant FE as FeatureEngineer
    participant BL as BaselineModel
    participant MR as ModelRegistry

    CRON->>TS: run_weekly_retraining()
    TS->>DB: SELECT ALL weather_observations (3+ years)
    TS->>FE: build_full_feature_matrix(observations)
    FE-->>TS: X_train, y_train, X_test, y_test

    TS->>TS: train XGBoost/LightGBM
    TS->>BL: evaluate_baseline(X_test, y_test)
    BL-->>TS: baseline_mae

    TS->>TS: evaluate_model(X_test, y_test) → model_mae
    
    alt model_mae < baseline_mae
        TS->>MR: swap_model(new_model)  ← atomic
        MR-->>DB: INSERT model_versions (metrics, path)
        Note over MR: Hot-swap: старая модель<br/>не останавливается
    else model хуже baseline
        TS->>TS: LOG WARNING "New model worse than baseline, keeping old"
        TS-->>DB: INSERT model_versions (failed=true)
    end
```

---

## Схема базы данных

```mermaid
erDiagram
    GEO_CACHE {
        string city_name PK
        float latitude
        float longitude
        timestamp cached_at
    }

    WEATHER_OBSERVATIONS {
        uuid id PK
        string city_name FK
        date obs_date
        float temperature_mean
        timestamp ingested_at
    }

    FORECAST_LOG {
        uuid id PK
        string city_name FK
        date forecast_date
        float predicted_temp
        float actual_temp "nullable до факта"
        float error "nullable"
        timestamp created_at
    }

    MAE_LOG {
        uuid id PK
        string city_name FK
        date window_end
        float mae_7d
        float baseline_mae_7d
        boolean threshold_exceeded
        timestamp calculated_at
    }

    MODEL_VERSIONS {
        uuid id PK
        string model_type
        string artifact_path
        float test_mae
        float baseline_mae
        boolean is_active
        boolean failed
        timestamp trained_at
    }

    GEO_CACHE ||--o{ WEATHER_OBSERVATIONS : "city"
    GEO_CACHE ||--o{ FORECAST_LOG : "city"
    GEO_CACHE ||--o{ MAE_LOG : "city"
```

---

## Границы масштабируемости

| Ось | Текущий дизайн (v1) | Предел v1 | Путь масштабирования |
|-----|--------------------|-----------|--------------------|
| Города | 1 (config-driven) | ~50 городов без изменений кода | Партиционирование по city в PG |
| RPS | Single-process FastAPI | ~200 rps (uvicorn, 1 worker) | uvicorn workers / gunicorn |
| Данные | 3 года × 1 город ≈ 1 095 строк | До 10 млн строк в PG без шардинга | TimescaleDB / PG партиции |
| Переобучение | 1 сервер, ~5 сек для 3 лет | До ~100k строк комфортно | Ray / distributed training |
| Горизонт прогноза | +1 день | Расширяется добавлением таргетов | Multi-output регрессия |
| Параметры | Только avg temp | Добавить min/max/precipitation как доп. столбцы | Мультитаргетный XGBoost |
