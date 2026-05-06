import asyncio
import logging
from app.router.messages.messages import (
    Request,
    TimeRequestParams,
    RequiredRequestParams,
    ResponseData,
    DailyDataParams,
    HourlyDataParams,
    TimePeriod,
)
from app.router.router import AsyncRouter

from app.core.logging import setup_logging

setup_logging()

default_logger = logging.getLogger(__name__)


class CronLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[CRON] {msg}", kwargs


logger = CronLoggerAdapter(default_logger)


async def _process_request(
    router: AsyncRouter,
    necessary_params: RequiredRequestParams,
    time_params: TimeRequestParams,
) -> None:
    request = Request(
        necessary_params, time_params, [TimePeriod.DAILY, TimePeriod.HOURLY]
    )

    response: ResponseData = await router.send_request(request)
    logger.info(response.data)


async def main():
    logger.info("script started")

    router = AsyncRouter()
    necessary_params = RequiredRequestParams(52.52, 13.41)
    time_params = TimeRequestParams(
        TimeRequestParams.str_to_date("2026-05-03"),
        TimeRequestParams.str_to_date("2026-05-05"),
    )

    try:
        await _process_request(router, necessary_params, time_params)
    except Exception as e:
        logger.error(str(e))

    logger.info("script finished")

    await router.aclose()


asyncio.run(main())
