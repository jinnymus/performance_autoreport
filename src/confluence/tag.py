from abc import ABC, abstractmethod
from typing import Iterable, Optional, Any

from base.element import BaseElementABC
import lxml
from lxml.etree import (_Element, SubElement, XMLParser, fromstring)


class BaseElement(BaseElementABC):
    def __init__(self, **kwargs) -> None:
        self.name: Optional[str] = None
        self.attrs = kwargs
        self.value: Optional[Any] = None
        self.element: Optional[_Element] = None
        self.parent: Optional[BaseElementABC] = None
        self.childes: list[BaseElementABC] = list()

    def render(self):
        if self.childes:
            for child in self.childes:
                child.render()

    def __call__(self, *args):
        if isinstance(args[0], str):
            self.value = args[0]
        elif isinstance(args, Iterable):
            for tag_element in args:
                if isinstance(tag_element, Iterable):
                    for tag_element_int in tag_element:
                        tag_element_int.parent = self
                        self.childes.append(tag_element_int)
                else:
                    tag_element.parent = self
                    self.childes.append(tag_element)
        elif issubclass(args[0], BaseElementABC):
            tag_element = args[0]
            tag_element.parent = self
            self.childes.append(tag_element)
        else:
            raise ValueError(f"Not support {args.__class__}")
        return self

    # @functools.singledispatchmethod
    # def __call__(self, *args):
    #     if args[0]:
    #         raise ValueError(f"Not support {args[0].__class__}")
    #
    # @__call__.register
    # def base_element__call__(self, *args: BaseElementABC):
    #     for tag_element in args:
    #         if tag_element:
    #             tag_element.parent = self
    #             self.childes.append(tag_element)
    #     return self
    #
    # @__call__.register
    # def str__call__(self, *args: str):
    #     self.value = args[0]
    #     return self


class page(BaseElement):
    def __init__(self) -> None:
        super().__init__()
        self.element = fromstring(
            f'<root xmlns:ac="confluence" xmlns:ri="ri_confluence"></root>'.replace('&nbsp;', ' ').encode('utf-8'), parser=XMLParser(encoding='utf-8')
        )

    def render(self):
        super().render()
        return lxml.etree.tostring(self.element).decode('utf-8')

class tag(BaseElement):
    def __init__(self, tag_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name: str = tag_name

    def render(self):
        self.element = SubElement(self.parent.element, self.name)
        if self.value:
            self.element.text = self.value
        for attr, value in self.attrs.items():
            self.element.set(attr, value)
        if self.childes:
            for child in self.childes:
                child.render()


class element(BaseElement):
    def __init__(self, data, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def render(self):
        #print(f"[BaseElement][element] self.data: {self.data}")
        self.parent.element.append(lxml.etree.fromstring(self.data))


class plain(BaseElement):
    def __init__(self, data, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data

    def render(self):
        print(f"[BaseElement][element] self.data: {self.data}")
        self.parent.element.append(self.data)


class attachment(BaseElement):
    def __init__(self, filename, **kwargs) -> None:
        super().__init__(**kwargs)
        self.filename = filename

    def render(self):
        self.element = SubElement(self.parent.element, '{confluence}link')
        SubElement(self.element, '{ri_confluence}attachment', attrib={'{ri_confluence}filename': self.filename})
