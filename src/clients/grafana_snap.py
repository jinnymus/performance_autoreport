import re
from typing import Optional
import logging
from grafana.client.grafana import Grafana, GrafanaSnapshot
from grafana.web.model import Dashboard, DashboardElementResponse
from settings import settings

logger = logging.getLogger('root')
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    force=True
)

class GrafanaService:
    def __init__(self, host: str = settings.grafana_snapshot_host, port: str = settings.grafana_snapshot_port) -> list:
        self.host = host
        self.port = port
        logger.debug(f"[get_snapshot][init] host: {host} port: {port}")

    def get_snapshot(self, dashboard_url: str,
                     grafana_login: str,
                     grafana_password: str,
                     date_from: int,
                     date_to: int,
                     panels: Optional[list[int]] = None):
        logger.debug(f"[get_snapshot] dashboard_url: {dashboard_url}")
        variables = {v[0]: v[1] for v in re.findall('var-(.+?)=(.+?)(&|$)', dashboard_url)}

        pattern_to = re.compile(r"(to=)(.+?)(&|$)")
        match_to = re.search(pattern_to, dashboard_url)
        if match_to:
            dashboard_url = dashboard_url.replace(match_to.group(1) + match_to.group(2), match_to.group(1) + str(date_to))
        else:
            dashboard_url += f'&to={date_to}'
        pattern_from = re.compile(r"(from=)(.+?)(&|$)")

        match_from = re.search(pattern_from, dashboard_url)
        if match_from:
            dashboard_url = dashboard_url.replace(match_from.group(1) + match_from.group(2), match_from.group(1) + str(date_from))
        else:
            dashboard_url += f'&from={date_from}'

        logger.debug(f"[get_snapshot] panels: {panels}")
        dashboards = Dashboard(url=dashboard_url, panels=panels)
        logger.debug(f"[get_snapshot] dashboards: {dashboards}")
        logger.debug(f"[get_snapshot] dashboards.url_dashboard: {dashboards.url_dashboard}")
        grafana = GrafanaSnapshot.build_from_url(dashboards.url_dashboard)
        logger.debug(f"[get_snapshot] grafana_login: {grafana_login} grafana_password: {grafana_password}" )
        grafana.auth(login=grafana_login, password=grafana_password)
        logger.debug(f"[get_snapshot] grafana auth" )
        grafana.authorize(login=grafana_login, password=grafana_password)
        logger.debug(f"[get_snapshot] grafana authorize" )
        structure_dashboard = grafana.get_structure_dashboard()
        logger.debug(f"[get_snapshot] grafana get_structure_dashboard" )
        if dashboards.element_dashboard:
            for graph in structure_dashboard:
                graphs = set()
                if graph['type'] == 'graph' or graph['type'] == 'stat':
                    graphs.pop(graph['id'])
            # graphs = (graph['id'] for graph in structure_dashboard if graph['type'] == 'graph'
            logger.debug(f"[get_snapshot] graphs: {graphs}")
            if set(dashboards.element_dashboard) - set(graphs):
                raise ValueError(f"Not found id {set(dashboards.element_dashboard) - set(graphs)} in dashboard")

        response: list[DashboardElementResponse] = list()

        for i in range(0, 10):
            if grafana.driver.current_url != grafana.url:
                grafana.driver.get(grafana.url)
            else:
                break
        if not dashboards.element_dashboard:
            dashboards.element_dashboard = list()
            for element in structure_dashboard:
                if element['type'] == 'graph' or element['type'] == 'stat':
                    dashboards.element_dashboard.append(element['id'])
                    # dashboards.element_dashboard = [element['id'] for element in structure_dashboard if element['type'] == 'graph']
        for i, element in enumerate(structure_dashboard):
            logger.debug(f"[get_snapshot] i: {i} element: {element}")
            if element['type'] == 'graph' and element['id'] in dashboards.element_dashboard:
                logger.debug(f"[get_snapshot] create_graphql_snapshot -->")
                snap_url = grafana.create_graphql_snapshot(element['title'], element['id'], element['type'])
                if snap_url is not None:
                    logger.debug(f"[get_snapshot] snap_url: {snap_url}")
                    response.append(DashboardElementResponse(url=snap_url, **element))
                else:
                    logger.debug(f"[get_snapshot] snap_url: {snap_url}")
            if element['type'] == 'stat':
                logger.debug(f"[get_snapshot] create_graphql_snapshot for stat -->")
                snap_url = grafana.create_graphql_snapshot(name=element['title'], id=element['id'], type=element['type'])
                if snap_url is not None:
                    logger.debug(f"[get_snapshot] snap_url: {snap_url}")
                    response.append(DashboardElementResponse(url=snap_url, **element))
            if len([r for r in response if r.url]) >= len(dashboards.element_dashboard):
                logger.debug(f"[get_snapshot] break")
                break
            if element['type'] == 'row':
                logger.debug(f"[get_snapshot] row")
                response.append(DashboardElementResponse(**element))
        grafana.driver_close()
        logger.debug(f"[get_snapshot] response: {response}")
        return response


    def get_structure_dashboard(uid: str, unknown: bool = False) -> list[dict]:
        snap = Grafana(host=settings.grafana_snapshot_host, port=settings.grafana_snapshot_port, uid=uid)
        return snap.get_structure_dashboard(unknown)