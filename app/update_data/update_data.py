from datetime import datetime, timezone
import logging


logger = logging.getLogger(__name__)


def update_data():
    logger.info(
        f"[CRON] update_data called at {datetime.now(timezone.utc).isoformat()}",
        flush=True,
    )


if __name__ == "__main__":
    logger.info(
        f"[CRON] script started at {datetime.now(timezone.utc).isoformat()}", flush=True
    )
    update_data()
    logger.info(
        f"[CRON] script finished at {datetime.now(timezone.utc).isoformat()}",
        flush=True,
    )
