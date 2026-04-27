#!/usr/bin/env python3

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Execute command and output status."""
    print(f"{description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print(f"{description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR AT {description}:")
        print(e.stderr)
        return False


def main():
    print("Begin pre-commit and black configuration...")

    config_path = Path(".pre-commit-config.yaml")
    if not config_path.exists():
        print(f"File {config_path} not found!")
        print("Confirm that the file exists in the current dir.")
        sys.exit(1)
    print(f"Found {config_path}")

    if not Path(".git").exists():
        print("Current dir is not a git repo.")
        response = input("Init git repo? (y/n): ")
        if response.lower() == "y":
            if not run_command("git init", "Init git repo"):
                sys.exit(1)
        else:
            print("Script demands git repo.")
            sys.exit(1)

    if not run_command(
        "pip install --upgrade pre-commit black", "Install pre-commit and black"
    ):
        sys.exit(1)

    if not run_command("pre-commit install", "Install pre-commit hooks"):
        sys.exit(1)

    response = input("Run pre-commit for all files now? (y/n): ")
    if response.lower() == "y":
        run_command("pre-commit run --all-files", "Start pre-commit")

    print("\nSetup finished.")
    print("For independent run: pre-commit run --all-files")


if __name__ == "__main__":
    main()
