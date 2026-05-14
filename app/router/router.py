import httpx
from httpx import AsyncClient, HTTPStatusError
from typing import Dict, Any

from app.router.messages.messages import (
    Request,
    ResponseData,
    DataParams,
    ResponseParams,
    ResponseSpecificParams,
    PlacedResponseData,
    data_params_by_period,
)
from app.utils.structures import TimePeriod


def dict_of_lists_to_list_of_dicts(
    data: Dict[str, Any], key: str
) -> list[Dict[str, Dict[str, Any]]]:
    """
    Example:
      data["daily"] = {
        "time": ["2024-01-01", "2024-01-02"],
        "temperature_2m_mean": [10.0, 11.0],
      }
    ->
      [
        {"daily": {"time": "2024-01-01", "temperature_2m_mean": 10.0}},
        {"daily": {"time": "2024-01-02", "temperature_2m_mean": 11.0}},
      ]
    """
    values = data[key]
    keys = list(values.keys())
    rows = zip(*(values[k] for k in keys))
    return [{key: {k: v for k, v in zip(keys, row)}} for row in rows]


class AsyncRouter:
    def __init__(
        self, url: str = "https://archive-api.open-meteo.com/v1/archive"
    ) -> None:
        self._url = url
        self._client: AsyncClient = AsyncClient(base_url=self._url)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _build_request_params(self, request: Request) -> dict[str, Any]:
        params: Dict[str, Any] = {}
        params |= request.provided_params()

        requested_params = request.requested_params()
        formatted_params = {str(k): ",".join(v) for k, v in requested_params.items()}
        params |= formatted_params
        return params

    def _build_request(self, request: Request) -> httpx.Request:
        params = self._build_request_params(request)

        url = request.url_continuation or ""
        return self._client.build_request(method=request.type, url=url, params=params)

    async def _send_request(self, request: httpx.Request) -> httpx.Response:
        return await self._client.send(request)

    def _build_response(
        self, request: Request, response: httpx.Response
    ) -> PlacedResponseData:
        payload = response.json()
        requested_params = request.requested_params()
        periods = requested_params.keys()

        parsed_items: list[ResponseParams] = []

        for period in periods:
            if period not in payload:
                continue

            rows = dict_of_lists_to_list_of_dicts(payload, period)
            wanted_by_data_request = set(requested_params[period])
            wanted_by_response_specific_params = ResponseParams.specific_params()

            for row in rows:
                row_payload = row[period]
                filtered_data = {
                    k: v for k, v in row_payload.items() if k in wanted_by_data_request
                }
                filtered_specific = {
                    k: v
                    for k, v in row_payload.items()
                    if k in wanted_by_response_specific_params
                }
                data_params: DataParams = data_params_by_period(
                    TimePeriod(period), **filtered_data
                )
                params = ResponseSpecificParams(**filtered_specific)
                parsed_items.append(
                    ResponseParams(params=params, data_params=data_params)
                )

        return PlacedResponseData(
            coords=request.coordinates(), data=ResponseData(data=parsed_items)
        )

    async def send_request(self, request: Request) -> PlacedResponseData:
        constructed_request = self._build_request(request)
        response = await self._send_request(constructed_request)
        try:
            response.raise_for_status()
            return self._build_response(request, response)
        except HTTPStatusError as e:
            message = str(e)
            exception_request = e.request
            exception_response = e.response
            msg = f"Message: {message}\nRequest: {repr(exception_request)}\nResponse: {repr(exception_response)}"
            raise Exception(msg)
        except Exception as e:
            msg = f"Not HTTP Error occured: {str(e)}"
            raise Exception(msg)
