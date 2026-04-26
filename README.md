# Weather Forecast API — v0

Сервис прогноза средней температуры воздуха на следующий день.  
**Текущая версия** использует заглушку (seasonal stub) вместо реальной ML-модели.

---

## Быстрый старт

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить сервер
uvicorn app.main:app --reload

# 3. Проверить в браузере
open http://localhost:8000/docs
```

---

## API

### `GET /forecast`

| Параметр | Тип    | Обязательный | Описание                              |
|----------|--------|:------------:|---------------------------------------|
| `city`   | string | ✅           | Название города                       |
| `date`   | string | ❌           | Дата в формате `YYYY-MM-DD` (по умолчанию: завтра) |

**Пример запроса:**
```
GET /forecast?city=Saint+Petersburg&date=2026-05-01
```

**Пример ответа:**
```json
{
  "city": "Saint Petersburg",
  "date": "2026-05-01",
  "avg_temperature_c": 8.3,
  "model_version": "stub-v0",
  "confidence": null
}
```

**Коды ошибок:**

| HTTP | code                | Причина                            |
|------|---------------------|------------------------------------|
| 400  | `INVALID_INPUT`     | Пустая строка города               |
| 404  | `CITY_NOT_FOUND`    | Город не найден                    |
| 422  | `VALIDATION_ERROR`  | Неверный формат параметров         |
| 503  | `MODEL_UNAVAILABLE` | Модель не загружена                |
| 500  | `INTERNAL_ERROR`    | Непредвиденная ошибка сервера      |

### `GET /health`

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_version": "stub-v0"
}
```

Полная документация: http://localhost:8000/docs

---

## CLI

```bash
# Прогноз на завтра
python weather_cli.py --city "Saint Petersburg"

# Прогноз на конкретную дату
python weather_cli.py --city Moscow --date 2026-07-15

# JSON-вывод
python weather_cli.py --city Kazan --json

# Другой сервер
python weather_cli.py --city Moscow --url http://myserver:8080
```

---

## Тестирование

### pytest (рекомендуется)

```bash
# Все тесты
pytest

# С отчётом о покрытии
pytest --cov=app --cov-report=term-missing

# Только юнит-тесты
pytest tests/unit/

# Только интеграционные тесты API
pytest tests/integration/

# Конкретный модуль
pytest tests/unit/test_geo_service.py -v
```

### curl

```bash
# Прогноз (default date = завтра)
curl "http://localhost:8000/forecast?city=Saint+Petersburg"

# Прогноз на конкретную дату
curl "http://localhost:8000/forecast?city=Moscow&date=2026-07-15"

# Через v1-префикс
curl "http://localhost:8000/api/v1/forecast?city=Kazan"

# Health check
curl "http://localhost:8000/health"

# Ошибка: неизвестный город
curl "http://localhost:8000/forecast?city=NonexistentCity"

# Ошибка: неверный формат даты
curl "http://localhost:8000/forecast?city=Moscow&date=15-07-2026"
```

### Postman

Импортировать файл `tests/weather_forecast.postman_collection.json` в Postman.  
Убедитесь, что переменная `base_url` = `http://localhost:8000`.  
Запустить `Run Collection` для прогона всех сценариев.

---

## Структура проекта

```
weather_forecast/
├── app/
│   ├── main.py                  # Точка входа, создание FastAPI-приложения
│   ├── api/
│   │   └── routes.py            # Эндпоинты: /forecast, /health
│   ├── core/
│   │   ├── config.py            # Настройки (pydantic-settings)
│   │   ├── exceptions.py        # Доменные исключения
│   │   └── logging.py           # Структурированные логи
│   ├── ml/
│   │   └── model_registry.py    # Реестр моделей + ModelStub + интерфейс BaseModel
│   ├── schemas/
│   │   └── forecast.py          # Pydantic схемы запроса/ответа
│   └── services/
│       ├── forecast_service.py  # Оркестрация: geo → features → predict
│       └── geo_service.py       # Геокодирование города → (lat, lon)
├── tests/
│   ├── conftest.py              # Shared fixtures (TestClient, mock services)
│   ├── unit/
│   │   ├── test_geo_service.py
│   │   ├── test_model_registry.py
│   │   └── test_forecast_service.py
│   ├── integration/
│   │   └── test_api.py          # End-to-end тесты через TestClient
│   └── weather_forecast.postman_collection.json
├── weather_cli.py               # CLI-клиент
├── architecture.md              # Диаграммы (Mermaid)
├── requirements.txt
└── .env.example
```

---

## Замена заглушки на реальную модель (v1)

1. Реализовать `class XGBoostModel(BaseModel)` в `app/ml/model_registry.py`
2. Загрузить артефакт модели при старте в `lifespan()` вместо `ModelStub()`
3. Реализовать `FeatureEngineer` для получения лагов из БД
4. Раскомментировать вызов к БД в `ForecastService.get_forecast()`

Интерфейс `BaseModel` и `ModelRegistry` не меняются — API остаётся совместимым.
