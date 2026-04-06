import uuid

import lxml
from lxml.etree import (SubElement, CDATA, Element)

from confluence.tag import BaseElement


class BaseMacros(BaseElement):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.params = None

    def render(self):
        """
        Создаете структуру макроса
        :param name: имя макроса
        :param attrs: атрибуты, записываются как атрибуты тега
        :param params: параметры, для каждого параметра отедльный тег parameter
        :return:
        """
        if self.parent is not None:
            self.element = SubElement(self.parent.element, "{confluence}structured-macro")
        else:
            raise ValueError('Parent element is None')
        self.element.set('{confluence}name', self.name)
        if self.attrs:
            for key, value in self.attrs.items():
                self.element.set('{confluence}' + key, value)
        if self.params:
            for key, value in self.params.items():
                param = SubElement(self.element, '{confluence}parameter')
                param.set('{confluence}name', key)
                param.text = str(value)


class toc(BaseMacros):
    """
    макрос оглавления
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = 'toc'


class lt(BaseMacros):
    """
    макрос localtab
    """

    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = 'localtab'
        self.params = {'title': title}

    def render(self):
        super().render()
        self.element = SubElement(self.element, '{confluence}rich-text-body')
        for child in self.childes:
            child.render()

class ut(BaseMacros):
    """
    макрос localtab
    """

    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = 'ui-tab'
        self.params = {'title': title}

    def render(self):
        super().render()
        self.element = SubElement(self.element, '{confluence}rich-text-body')
        for child in self.childes:
            child.render()

class ltg(BaseMacros):
    """
    макрос localtabgroup
    """

    def __init__(self, width: int = 150, vertical: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = 'localtabgroup'
        self.params = {
            'width': width,
            'vertical': str(vertical).lower()
        }

    def render(self):
        super().render()
        self.element = SubElement(self.element, '{confluence}rich-text-body')
        for child in self.childes:
            child.render()

class uts(BaseMacros):
    """
    макрос localtabgroup
    """

    def __init__(self, width: int = 150, vertical: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = 'ui-tabs'
        self.params = {
            'width': width,
            'vertical': str(vertical).lower()
        }

    def render(self):
        super().render()
        self.element = SubElement(self.element, '{confluence}rich-text-body')
        for child in self.childes:
            child.render()


class image(BaseMacros):
    """
    макрос изображения
    """

    def __init__(self, file_name, **kwargs) -> None:
        super().__init__(**kwargs)
        self.file_name = file_name
        self.element = SubElement(self.parent.element, "{confluence}image")

    def render(self):
        SubElement(self.element, "{ri_confluence}attachment").set('{ri_confluence}filename', self.file_name)


class html(BaseMacros):
    """
    макрос html
    """

    def __init__(self, data, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = 'html'
        self.attrs = {
            "schema-version": "1",
            "macro-id": str(uuid.uuid4()),
        }
        self.data = data

    def render(self):
        super().render()
        self.element = SubElement(self.element, '{confluence}plain-text-body')
        self.element.text = self.data


class code(BaseMacros):
    """
    макрос code
    <ac:structured-macro ac:name="code" ac:schema-version="1" ac:macro-id="def6c902-879a-4a95-b8dd-e47c62901b98">
 <ac:parameter ac:name="language">json</ac:parameter>
 <ac:plain-text-body>
 <![CDATA[{    }]]>
</ac:plain-text-body>
</ac:structured-macro>
    """

    def __init__(self, data, **kwargs) -> None:

        super().__init__(**kwargs)
        self.name = 'code'
        self.attrs = {
            "schema-version": "1",
            "macro-id": str(uuid.uuid4()),
        }
        self.data = data

    def render(self):
        super().render()
        self.element = SubElement(self.element, '{confluence}plain-text-body')
        data = CDATA(
                self.data
        )
        self.element.text = data


class link(BaseMacros):
    """
    макрос link
    """

    def __init__(self, data, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = 'html'
        self.attrs = {
            "schema-version": "1",
            "macro-id": str(uuid.uuid4()),
        }
        self.data = data

    def render(self):
        super().render()
        self.element = SubElement(self.element, '{confluence}plain-text-link-body')
        self.element.text = self.data

class lin(BaseMacros):
    """
    макрос html
    """

    def __init__(self, data, **kwargs) -> None:
        super().__init__(**kwargs)

    def render(self):
        super().render()
        self.element = self.data


class html_plain(html):
    """
    макрос html
    """
    def __init__(self, data, **kwargs) -> None:
        element = Element(
            'html'
        )
        element.text = data
        super().__init__(data, **kwargs)


class html_data(html):
    def __init__(self, data, **kwargs) -> None:
        element = Element(
            'html'
        )
        element.text = data
        data = CDATA(
                data
        )
        super().__init__(data, **kwargs)

class iframe(html):
    def __init__(self, src, loading: str = 'lazy', frame_border: int = 0, width: int = 1050, height: int = 500, scrolling: str = 'yes', **kwargs) -> None:
        element = Element(
            'iframe',
            attrib={'src': src, 'loading': loading, 'frameBorder': str(frame_border), 'width': str(width), 'height': str(height), 'scrolling': scrolling, 'seamless': ""}
        )
        element.text = ""
        data = CDATA(
            lxml.etree.tostring(
                element,
                encoding='utf-8')
        )
        super().__init__(data, **kwargs)
