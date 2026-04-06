from abc import ABC, abstractmethod
from typing import Iterable, Optional, Any
from enum import Enum


class InfluxType(Enum):
    """
    Type of the server.
    """

    INFLUX = "influx"
    FLUX = "flux"

class ServerType(Enum):
    """
    Type of the server.
    """

    CONFLUENCE = "confluence"
    YANDEX = "yandex"
    MARKDOWN = "markdown"
    HTML = "html"

class BaseElementABC(ABC):

    @abstractmethod
    def render(self):
        return NotImplemented

    @abstractmethod
    def __call__(self, *args):
        return NotImplemented
