#!/usr/bin/env python3
"""
weather_cli.py — Command-line client for the Weather Forecast API.

Usage:
    python weather_cli.py --city "Saint Petersburg"
    python weather_cli.py --city Moscow --date 2026-07-15
    python weather_cli.py --city Moscow --url http://myserver:8000
"""

import argparse
import sys
from datetime import date, datetime
from app.core.logging import setup_logging

setup_logging()
import logging

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)

DEFAULT_BASE_URL = "http://localhost:8000"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weather_cli",
        description="Get temperature forecast for a city.",
    )
    parser.add_argument(
        "--city",
        "-c",
        required=True,
        help="City name, e.g. 'Saint Petersburg'",
    )
    parser.add_argument(
        "--date",
        "-d",
        default=None,
        help="Forecast date in YYYY-MM-DD format (default: tomorrow)",
    )
    parser.add_argument("--params", "-p", nargs="*", type=str)
    parser.add_argument(
        "--url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of the API server (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text",
    )
    return parser


def format_temperature(temp: float) -> str:
    sign = "+" if temp >= 0 else ""
    return f"{sign}{temp:.1f}°C"


def fetch_forecast(
    base_url: str, city: str, target_date: str | None, target_params: list[str]
) -> dict:
    params: dict = {"city": city}
    if target_date:
        params["time"] = target_date
    if target_params:
        params["params"] = target_params

    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{base_url}/forecast", params=params)

    if response.status_code == 200:
        return response.json()

    # Surface API error to user
    try:
        err = response.json()
        detail = err.get("detail", err)
        if isinstance(detail, dict):
            raise SystemExit(
                f"Error [{detail.get('code', response.status_code)}]: "
                f"{detail.get('detail', 'Unknown error')}"
            )
    except (ValueError, KeyError):
        pass
    raise SystemExit(f"API returned HTTP {response.status_code}: {response.text}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate date format if provided
    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(
                f"Error: invalid date format '{args.date}'. Use YYYY-MM-DD.",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        data = fetch_forecast(
            base_url=args.url.rstrip("/"),
            city=args.city,
            target_date=args.date,
            target_params=args.params,
        )
    except httpx.ConnectError:
        print(f"Error: cannot connect to API at {args.url}", file=sys.stderr)
        print("Make sure the server is running: uvicorn app.main:app", file=sys.stderr)
        sys.exit(1)
    except httpx.TimeoutException:
        print("Error: request timed out", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json

        print(json.dumps(data, indent=2))
        return

    logger.info(data)


if __name__ == "__main__":
    main()
