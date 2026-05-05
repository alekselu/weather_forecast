import httpx
from httpx import AsyncClient
from typing import Dict, Any

from app.router.messages.messages import (
    Request,
    ResponseData,
    DataParams,
    ResponseParams,
    get_DataParams_by_period,
)


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
        params |= request.get_provided_params()

        requested_params = request.get_requested_params()
        formatted_params = {k: ",".join(v) for k, v in requested_params.items()}
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
    ) -> ResponseData:
        payload = response.json()
        requested_params = request.get_requested_params()
        periods = requested_params.keys()

        parsed_items: list[ResponseParams] = []

        for period in periods:
            if period not in payload:
                continue

            rows = dict_of_lists_to_list_of_dicts(payload, period)
            wanted_by_data_request = set(requested_params[period])
            wanted_by_response_except_data = (
                ResponseParams.get_requested_params_except_data()
            )

            for row in rows:
                row_payload = row[period]
                filtered_data = {
                    k: v for k, v in row_payload.items() if k in wanted_by_data_request
                }
                filtered_except_data = {
                    k: v
                    for k, v in row_payload.items()
                    if k in wanted_by_response_except_data
                }
                params: DataParams = get_DataParams_by_period(period, **filtered_data)
                parsed_items.append(
                    ResponseParams(**filtered_except_data, data_params=params)
                )

        return ResponseData(data=parsed_items)

    async def send_request(self, request: Request) -> ResponseData:
        constructed_request = self._build_request(request)
        response = await self._send_request(constructed_request)
        response.raise_for_status()
        return self._build_response(request, response)
