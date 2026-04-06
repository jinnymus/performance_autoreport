from atlassian import Confluence
import markdownify
import markdown
import logging
import requests
from requests.adapters import HTTPAdapter

from confluence.macros import iframe, lt, ltg, ut, uts

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class ConfluenceClient(Confluence):
    def __init__(self, host, token, **kwargs) -> None:
        session = requests.Session()
        adapter = CustomHTTPAdapter(headers={"Authorization": f"Bearer {token}"})
        session.mount(host, adapter)
        super().__init__(**kwargs, session=session)


    def build_snapshot_tag(self, snapshots: list) -> ltg:
        print(f"[build_snapshot_tag] snapshots: {snapshots}")
        if snapshots:
            main_ltg = ltg(vertical=True)
            main_graph_ltg = main_ltg
            for snap_model in snapshots:
                print(f"[build_snapshot_tag] snap_model: {snap_model}")
                snap = snap_model.model_dump()
                print(f"[build_snapshot_tag] snap: {snap}")
                title = snap['title']
                type = snap['type']
                if type == 'row':
                    main_graph_ltg = ltg(vertical=False)
                    main_ltg(
                        lt(title)(
                            main_graph_ltg
                        )
                    )
                if snap['type'] == 'graph':
                    main_graph_ltg(
                        lt(title)(iframe(src=snap['url']))
                    )
            return main_ltg
        else:
            raise ValueError("Grafana return empty snapshots")


    def build_snapshot_tag_uitabs(self, snapshots: list) -> uts:
        print(f"[build_snapshot_tag_uitabs] snapshots: {snapshots}")
        if snapshots:
            main_uts = uts(vertical=True)
            main_graph_uts = main_uts
            for snap_model in snapshots:
                print(f"[build_snapshot_tag_uitabs] snap_model: {snap_model}")
                snap = snap_model.model_dump()
                print(f"[build_snapshot_tag_uitabs] snap: {snap}")
                title = snap['title']
                type = snap['type']
                if type == 'row':
                    main_graph_uts = uts(vertical=False)
                    main_uts(
                        ut(title)(
                            main_graph_uts
                        )
                    )
                if snap['type'] == 'graph':
                    main_graph_uts(
                        ut(title)(iframe(src=snap['url']))
                    )
                if snap['type'] == 'stat':
                    main_graph_uts(
                        ut(title)(iframe(src=snap['url']))
                    )
            return main_uts
        else:
            raise ValueError("[build_snapshot_tag_uitabs] Grafana return empty snapshots")


class CustomHTTPAdapter(HTTPAdapter):
    def __init__(self, headers=None, *args, **kwargs):
        self.default_headers = Confluence.default_headers
        self.default_headers.update(headers)
        super().__init__(*args, **kwargs)
    def send(self, request, **kwargs):
        # Merge default headers with request-specific headers
        request.headers.update(self.default_headers)
        return super().send(request, **kwargs)

