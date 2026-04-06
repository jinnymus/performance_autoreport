from abc import ABC, abstractmethod
from typing import Iterable, Optional, Any

import base.element.BaseElementABC


class BaseElement(BaseElementABC):
    def __init__(self, **kwargs) -> None:
        self.name: Optional[str] = None
        self.attrs = kwargs
        self.value: Optional[Any] = None
        self.element: Optional[_Element] = None
        self.parent: Optional[BaseElementABC] = None
        self.childes: list[BaseElementABC] = list()


class page(BaseElement):
    def __init__(self) -> None:
        super().__init__()
        self.element = fromstring(
            f'<root xmlns:ac="confluence" xmlns:ri="ri_confluence"></root>'.replace('&nbsp;', ' ').encode('utf-8'), parser=XMLParser(encoding='utf-8')
        )


class tag(BaseElement):
    def __init__(self, tag_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name: str = tag_name


class element(BaseElement):
    def __init__(self, data, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

 