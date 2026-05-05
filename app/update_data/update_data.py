import asyncio
import logging
from app.router.messages.messages import (
    Request,
    TimeRequestParams,
    NecessaryRequestParams,
    ResponseData,
    DailyDataParams,
)
from app.router.router import AsyncRouter

logger = logging.getLogger(__name__)


async def main():
    logger.info("[CRON] script started")

    router = AsyncRouter()
    necessary_params = NecessaryRequestParams(52.52, 13.41)
    time_params = TimeRequestParams(
        TimeRequestParams.str_to_date("2026-05-03"),
        TimeRequestParams.str_to_date("2026-05-05"),
    )
    request = Request(necessary_params, time_params, [DailyDataParams])

    response: ResponseData = await router.send_request(request)
    print(response.data)
    logger.info("[CRON] script finished")


asyncio.run(main())
