import asyncio
import logging
from app.router.messages.messages import (
    Request,
    TimeRequestParams,
    RequiredRequestParams,
    ResponseData,
)
from app.router.router import AsyncRouter
from app.db.utils import ApiDbProxy
from app.core.logging import setup_logging
from app.utils.structures import TimePeriod
from app.utils.uitls import LoggerAdapter

setup_logging()

default_logger = logging.getLogger(__name__)

logger = LoggerAdapter("CRON", default_logger)


def _verify_requets(request: Request, db_proxy: ApiDbProxy) -> None:
    request_fields = request.requested_params()
    for time_period, params in request_fields.items():
        db_fields = set(db_proxy.get_period_table_params(time_period))
        params_set = set(params)

        if params_set == db_fields:
            continue
        diff = db_fields - params_set
        if diff != set():
            logger.warning(
                f"Request process less fields than DB provided for {time_period}: {diff}"
            )
        diff = params_set - db_fields
        if diff != set():
            logger.error(
                f"Request process extra more fields than DB provided for {time_period}: {diff}"
            )
            raise ValueError("Incorrect request structure")


async def _process_request(
    router: AsyncRouter,
    necessary_params: RequiredRequestParams,
    time_params: TimeRequestParams,
    db_proxy: ApiDbProxy,
) -> None:
    request = Request(necessary_params, time_params, [TimePeriod.DAILY])

    _verify_requets(request, db_proxy)
    response: ResponseData = await router.send_request(request)
    logger.info(response.data)


async def main():
    logger.info("script started")

    router = AsyncRouter()
    db_proxy = ApiDbProxy()

    necessary_params = RequiredRequestParams(52.52, 13.41)
    time_params = TimeRequestParams(
        TimeRequestParams.str_to_date("2026-05-03"),
        TimeRequestParams.str_to_date("2026-05-05"),
    )

    try:
        await _process_request(router, necessary_params, time_params, db_proxy)
    except Exception as e:
        logger.error(str(e))

    logger.info("script finished")

    await router.aclose()


asyncio.run(main())
