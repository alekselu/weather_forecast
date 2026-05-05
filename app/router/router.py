import httpx
from httpx import AsyncClient
from request.request import Request


class AsyncRouter:
    def __init__(self, url: str) -> None:
        self._url = url
        self._client: AsyncClient = AsyncClient()

    def _build_request(self, request: Request) -> httpx.Request:
        return self._client.build_request(request.type, request.url_continuation)

    async def _send_request(self, request: httpx.Request) -> httpx.Response:
        return await self._client.send(request)

    async def send_request(self, request: Request) -> httpx.Response:
        constructed_request: httpx.Request = self._build_request(request)
        return await self._send_request(constructed_request)
