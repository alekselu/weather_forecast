#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Выполняет команду и выводит статус"""
    print(f"{description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"{description} - успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при {description}:")
        print(e.stderr)
        return False


def main():
    print("Начинаем настройку pre-commit и black...")

    config_path = Path(".pre-commit-config.yaml")
    if not config_path.exists():
        print(f"Файл {config_path} не найден!")
        print("Убедитесь, что файл существует в текущей директории")
        sys.exit(1)
    print(f"Найден {config_path}")

    if not Path(".git").exists():
        print("Текущая директория не является git репозиторием")
        response = input("Хотите инициализировать git репозиторий? (y/n): ")
        if response.lower() == "y":
            if not run_command("git init", "Инициализация git репозитория"):
                sys.exit(1)
        else:
            print("Скрипт требует git репозиторий")
            sys.exit(1)

    if not run_command(
        "pip install --upgrade pre-commit black", "Установка pre-commit и black"
    ):
        sys.exit(1)

    if not run_command("pre-commit install", "Установка pre-commit хуков"):
        sys.exit(1)

    response = input("Запустить pre-commit на всех файлах сейчас? (y/n): ")
    if response.lower() == "y":
        run_command("pre-commit run --all-files", "Запуск pre-commit")

    print("\nНастройка завершена.")
    print("Для ручного запуска: pre-commit run --all-files")


if __name__ == "__main__":
    main()
