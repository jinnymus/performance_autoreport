import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class HtmlClient:
    def __init__(self):
        logger.debug("[HtmlClient] init")

    def write_html(self, path:str = None, html_string: str = None):
        logger.debug("[HtmlClient][from_html] init")
        with open(f"{path}", 'a+') as f:
            f.write(html_string)
        return html_string

    def write(self, path, data: str):
        logger.debug(f"[HtmlClient][write]")
        with open(path, 'a+') as f:
            f.write(data)

    def html_link(self, name: str, url: str):
        return f"""<a href="{url.replace('&amp;','&')}">{name}</a>"""


    def get_jmeter_dashboard_for_bot(self, snapshots: list) -> str:
        if snapshots:
            data = str()
            for snap_model in snapshots:
                snap = snap_model.model_dump()
                print(f"[HtmlClient][build_snapshot_tag] snap: {snap}")
                title = snap['title']
                _jmeter_panel_titles = (
                    "Overall request rate vs response time",
                    "Общая интенсивность запросов vs Время ответа",
                )
                if title in _jmeter_panel_titles:
                    return snap['url']
        else:
            raise ValueError("Grafana return empty snapshots")


    def build_snapshot_tag(self, snapshots: list) -> str:
        if snapshots:
            data = str()
            for snap_model in snapshots:
                snap = snap_model.model_dump()
                print(f"[HtmlClient][build_snapshot_tag] snap: {snap}")
                title = snap['title']
                type = snap['type']
                if type == 'row':
                    data = f"{data}<h5>{title}</h5>"
                if snap['type'] == 'graph':
                    data = f"{data}<br>{self.html_link(name=title, url=snap['url'])}"
                if snap['type'] == 'stat':
                    data = f"{data}<br>{self.html_link(name=title, url=snap['url'])}"
            return data
        else:
            raise ValueError("Grafana return empty snapshots")

    def create_page(self, param, title, param1, parent_id, type, representation, editor, full_width):
        pass

    def get_page_by_title(self, space, page):
        pass

    def get_page_id(self, space, title):
        pass

    def get_page_by_id(self, page_id, expand):
        pass

    def update_page(self, param, title, page_body, parent_id, type, representation):
        pass

    def build_snapshot_tag_uitabs(self, snapshots_tmp):
        pass
