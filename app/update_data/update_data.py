import asyncio
import logging
from datetime import datetime, timedelta
from app.router.messages.messages import (
    Request,
    TimeRequestParams,
    RequiredRequestParams,
    PlacedResponseData,
    ResponseData,
)
from app.router.router import AsyncRouter
from app.db.utils import ApiDbProxy
from app.core.logging import setup_logging
from app.utils.structures import TimePeriod, Place, City, Coordinates
from app.core.logging import LoggerAdapter
from app.utils.geolocation import get_geo_coder, GeoCoder

setup_logging()

default_logger = logging.getLogger(__name__)

logger = LoggerAdapter("CRON", default_logger)

INTERNAL_DB_FIELDS = {"id", "city_id", "date"}


def _verify_requets(request: Request, db_proxy: ApiDbProxy) -> None:
    request_fields = request.requested_params()
    for time_period, params in request_fields.items():
        db_fields = set(db_proxy.get_period_table_params(time_period))
        db_fields -= INTERNAL_DB_FIELDS
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
) -> PlacedResponseData:
    request = Request(necessary_params, time_params, [TimePeriod.DAILY])

    _verify_requets(request, db_proxy)
    response: PlacedResponseData = await router.send_request(request)
    logger.debug(response.data)
    return response


def _get_tme_period_for_update() -> TimeRequestParams:
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    return TimeRequestParams(start_date=yesterday.date(), end_date=today.date())


async def main():
    logger.info("script started")

    router = AsyncRouter()
    db_proxy = ApiDbProxy()

    cities: list[Place] = db_proxy.get_all_cities()

    # FOR DEBUG. TODO: need to think, how organize new cities insertion
    if len(cities) == 0:
        city = City("Saint Petersburg", "ru")
        geo_coder: GeoCoder = get_geo_coder()
        coords: Coordinates = await geo_coder.fetch_location_from(city)

        db_proxy.insert_city(city, coords)
        cities = db_proxy.get_all_cities()

    for city in cities:
        necessary_params = RequiredRequestParams(coords=city.coords)
        time_params = _get_tme_period_for_update()

        try:
            response = await _process_request(
                router, necessary_params, time_params, db_proxy
            )
            db_proxy.insert_into_table(city.city, response)
        except Exception as e:
            logger.error(str(e))

    logger.info("script finished")

    await router.aclose()


asyncio.run(main())
