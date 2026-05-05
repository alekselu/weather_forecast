from datetime import datetime, timezone
import logging


logger = logging.getLogger(__name__)


def update_data():
    logger.info(
        f"[CRON] update_data called",
        flush=True,
    )


if __name__ == "__main__":
    logger.info(f"[CRON] script started", flush=True)
    update_data()
    logger.info(
        f"[CRON] script finished",
        flush=True,
    )
