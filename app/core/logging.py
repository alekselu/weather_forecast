import os
import logging
import sys
from once import once

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
print(log_level)


@once
def setup_logging():
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(levelname)s | %(asctime)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(
        self,
        prefix: str,
        logger: logging.Logger = logging.getLogger(__name__),
        extra=None,
    ):
        super().__init__(logger, extra)
        self.prefix = prefix

    def process(self, msg, kwargs):
        return f"[{self.prefix}] {msg}", kwargs
