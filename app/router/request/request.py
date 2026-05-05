from dataclasses import dataclass


@dataclass
class Request:
    type: str = "GET"
    url_continuation: str = ""
