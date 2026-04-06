import markdownify
import markdown
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class MarkdownClient:
    def __init__(self, path):
        logger.debug("[MarkdownClient] init")
        self.path = path
        with open(self.path, 'w+') as f:
            f.write("")

    def write_html(self, html_string: str):
        logger.debug("[MarkdownClient][from_html] init")
        data = markdownify.markdownify(html_string, heading_style='ATX')
        with open(self.path, 'a+') as f:
            f.write(data)
        with open(f"{self.path}.html", 'a+') as f:
            f.write(html_string)
        return data

    def write(self, data: str):
        logger.debug(f"[MarkdownClient][write]")
        with open(self.path, 'a+') as f:
            f.write(data)

    def md_link(self, name: str, url: str):
        return f"[{name}]({url.replace('&amp;','&')})\n"

    def html_link(self, name: str, url: str):
        return f"""<a href="{url.replace('&amp;','&')}">{name}</a>"""

    def build_snapshot_tag(self, snapshots: list) -> str:
        if snapshots:
            data = str()
            for snap_model in snapshots:
                snap = snap_model.model_dump()
                print(f"[MarkdownClient][build_snapshot_tag] snap: {snap}")
                title = snap['title']
                type = snap['type']
                if type == 'row':
                    data = f"{data}\n#### {title}\n"
                if snap['type'] == 'graph':
                    data = f"{data}\n{self.html_link(name=title, url=snap['url'])}\n"
            return data
        else:
            raise ValueError("Grafana return empty snapshots")
