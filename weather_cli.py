#!/usr/bin/env python3
"""
weather_cli.py — CLI для Weather Forecast API.

Использование:
    python weather_cli.py --city "Saint Petersburg"
    python weather_cli.py --city Moscow --date 2026-07-15
    python weather_cli.py --city Moscow --url http://myserver:8000
"""

import argparse
import sys
from datetime import date, datetime

try:
    import httpx
except ImportError:
    print("Ошибка: требуется httpx. Выполните: pip install httpx", file=sys.stderr)
    sys.exit(1)

DEFAULT_BASE_URL = "http://localhost:8000"


def build_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="weather_cli",
        description="Получить прогноз температуры для города.",
    )
    parser.add_argument(
        "--city", "-c",
        required=True,
        help="Название города, например 'Saint Petersburg'",
    )
    parser.add_argument(
        "--date", "-d",
        default=None,
        help="Дата прогноза в формате ГГГГ-ММ-ДД (по умолчанию: завтра)",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help=f"Базовый URL сервера API (по умолчанию: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вывести сырой JSON вместо форматированного текста",
    )
    return parser


def format_temperature(temp: float) -> str:
    """Форматирует температуру со знаком и градусами Цельсия."""
    sign = "+" if temp >= 0 else ""
    return f"{sign}{temp:.1f}°C"


def fetch_forecast(base_url: str, city: str, target_date: str | None) -> dict:
    """Запрашивает прогноз с API и возвращает данные в виде словаря."""
    params: dict = {"city": city}
    if target_date:
        params["date"] = target_date

    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{base_url}/forecast", params=params)

    if response.status_code == 200:
        return response.json()

    # Показываем пользователю ошибку API
    try:
        err = response.json()
        detail = err.get("detail", err)
        if isinstance(detail, dict):
            raise SystemExit(
                f"Ошибка [{detail.get('code', response.status_code)}]: "
                f"{detail.get('detail', 'Неизвестная ошибка')}"
            )
    except (ValueError, KeyError):
        pass
    raise SystemExit(f"API вернул HTTP {response.status_code}: {response.text}")


def main() -> None:
    """Главная функция: парсит аргументы, получает прогноз и выводит результат."""
    parser = build_parser()
    args = parser.parse_args()

    # Проверяем формат даты, если она указана
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"Ошибка: неверный формат даты '{args.date}'. Используйте ГГГГ-ММ-ДД.", file=sys.stderr)
            sys.exit(1)

    try:
        data = fetch_forecast(
            base_url=args.url.rstrip("/"),
            city=args.city,
            target_date=args.date,
        )
    except httpx.ConnectError:
        print(f"Ошибка: не удалось подключиться к API по адресу {args.url}", file=sys.stderr)
        print("Убедитесь, что сервер запущен: uvicorn app.main:app", file=sys.stderr)
        sys.exit(1)
    except httpx.TimeoutException:
        print("Ошибка: превышено время ожидания запроса", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json
        print(json.dumps(data, indent=2))
        return

    city = data["city"]
    forecast_date = data["date"]
    temp = data["avg_temperature_c"]
    model = data.get("model_version", "unknown")

    print(f"\n{city}")
    print(f"  {forecast_date}")
    print(f"   {format_temperature(temp)}")
    print(f"   (модель: {model})\n")


if __name__ == "__main__":
    main()
