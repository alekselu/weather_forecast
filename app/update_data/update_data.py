from datetime import datetime, timezone


def update_data():
    print(
        f"[CRON] update_data called at {datetime.now(timezone.utc).isoformat()}",
        flush=True,
    )


if __name__ == "__main__":
    print(
        f"[CRON] script started at {datetime.now(timezone.utc).isoformat()}", flush=True
    )
    update_data()
    print(
        f"[CRON] script finished at {datetime.now(timezone.utc).isoformat()}",
        flush=True,
    )
