Сервис прогнозирования средней температуры на следующий день для заданного города.
Реализован на FastAPI с использованием PostgreSQL и Docker.

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/alekselu/weather_forecast.git
cd weather_forecast
```

---

### 2. Настроить переменные окружения

В проекте есть файл `.env.example` с примером конфигурации.

Скопируйте его:

```bash
cp .env.example .env
```

И при необходимости измените значения (например, логин/пароль БД).

Рекомендуется использовать собственный `.env`, а не `.env.example`.

---

### 3. Запуск через Docker Compose

```bash
docker-compose up --build
```

Docker Compose поднимает:

* backend (FastAPI)
* PostgreSQL

Контейнеры запускаются вместе как единая система.

---

### 4. Проверка работы

Откройте в браузере:

* API:

  ```
  http://localhost:8000
  ```

* Проверка БД:

  ```
  http://localhost:8000/health/db
  ```

---

## Структура проекта

```bash
.
├── app/             
│   ├── main.py
│   ├── db.py
│   └── __init__.py
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Технологии

* FastAPI
* PostgreSQL
* Docker / Docker Compose

---

## 🛠 Основные команды

```bash
# запуск
docker-compose up --build

# остановка
docker-compose down

# логи
docker-compose logs
```

---

## Примечания

* При первом запуске база данных инициализируется автоматически
* Данные БД сохраняются в volume и не теряются при перезапуске
* Для разработки используется hot-reload (изменения кода применяются без пересборки контейнера)

---

## Предложение изменений

При нахождении ошибки в работе приложения или необходимости внедрения новой функциональности, откройте [issue](https://github.com/alekselu/weather_forecast/issues).
