import logging

from clients.express_client import ExpressCLient
from clients.report_storage_client import send_performance_test
from analysis.max_rps import get_max_rps_for_sla, extract_page_response_times
from constants import MAX_RPS_CALCULATION_TYPES
from base.element import InfluxType, ServerType
from clients.yandex_client import YandexClient
from clients.markdown_client import MarkdownClient
from analysis.aggregator_flux import AggregatorStepMetricFlux
from clients.flux_client import export_metric_from_flux_v2
from clients.html_client import HtmlClient
import uvicorn as uvicorn
from atlassian import Confluence
from fastapi import FastAPI, Response, Path

from clients.confluence_client import ConfluenceClient
import utils
from analysis.aggregator_influx import AggregatorStepMetric
from analysis.metric import *
from clients.awr import AWRPostgres, AWROracle
from clients.grafana_snap import GrafanaService, GrafanaSnapshot
from clients.influx_client import *
from confluence.tag import *
from settings import settings
from confluence.macros import html, html_data
from web.model import InfluxBase, RequestCreateReport
from web.template import *
import pandas as pd
import requests
import json
import markdownify
import os
from datetime import datetime
from clients.argocd import ArgoAdapter
from web.model import ApplicationsModel

from web.model import ArgoBase

app = FastAPI()
logger = logging.getLogger('root')
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    force=True
)

# Reduce noisy third-party loggers
logging.getLogger("hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("hpack.table").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger('seleniumwire').setLevel(logging.ERROR)
logging.getLogger('atlassian.rest_client').setLevel(logging.ERROR)
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)


def get_influx_metrics(request: RequestCreateReport) -> pd.DataFrame:
    logger.debug(f"[get_influx_metrics] start")
    influx = request.influx
    load_plan = request.test.load_plan
    uuid_test = request.test.uuid
    start_date = request.test.start_datetime
    logger.debug(f"[get_influx_metrics] start get_end_time_from_load_plan")
    end_date = utils.get_end_time_from_load_plan(start_date, load_plan)
    start_date_unix: int = int(start_date.timestamp()) * 1000
    end_date_unix: int = int(end_date.timestamp()) * 1000
    # moscow = timezone(timedelta(hours=3))
    # _date_obj_start_tz = _date_obj_start.astimezone(tz=moscow)
    # _date_obj_end_tz = _date_obj_start.astimezone(tz=moscow)
    logger.debug(f"[get_influx_metrics] influx: {influx}")

    data = pd.DataFrame()
    result = None

    logger.debug(f"[get_influx_metrics] influx: {influx}")
    if (influx.type == InfluxType.INFLUX):
        logger.debug(f"[get_influx_metrics] INFLUX type")
        data = export_metric_from_influx(host=influx.host,
                                         port=influx.port,
                                         db=influx.db,
                                         user=influx.user,
                                         pwd=influx.pwd,
                                         measurement=influx.measurement,
                                         start_datetime=start_date,
                                         end_datetime=end_date,
                                         uuid=str(uuid_test))
        if (not data.empty):
            agg = AggregatorStepMetric(
                data_source=data,
                time_column='level_0',
                operation_column='transaction',
                load_plan=request.test.load_plan,
                start_time=request.test.start_datetime
            )
            # agg.filter_operation(exclude=['Keycloak#Authorize', 'Grants#Authorize', 'JSR223 Sampler'])
            metric_loop = [('count', rpm, None), ('pct90.0', pct90, None),
                           (['count', 'count_error'], count_error, 'count_error')]
            for (metric_column, metric_func, column) in metric_loop:
                agg.metric(metric_column, metric_func, column)

            logger.debug(f"[get_influx_metrics][INFLUX] assemble_data_metric: {agg.assemble_data_metric()}")
            result = agg.assemble_data_metric()
    elif (influx.type == InfluxType.FLUX):
        logger.debug(f"[get_influx_metrics] FLUX type")
        data = export_metric_from_flux_v2(url=influx.url,
                                          bucket=influx.bucket,
                                          token=influx.token,
                                          org=influx.org,
                                          start_datetime=start_date,
                                          end_datetime=end_date,
                                          uuid=str(uuid_test))
        if (data is not None):
            agg = AggregatorStepMetricFlux(
                data_source=data,
                time_column='_time',
                operation_column='requestName',
                load_plan=load_plan,
                start_time=request.test.start_datetime
            )

            metric_loop = [('count', rpm, None),
                           ('responseTime', resp95, None),
                           ('latency', lat95, None),
                           (['count', 'errorCount'], errorCount, 'errorCount')]
            for (metric_column, metric_func, column) in metric_loop:
                agg.metric(metric_column, metric_func, column)

            # logger.debug(f"[get_influx_metrics][FLUX] assemble_data_metric: {agg.assemble_data_metric()}")
            result = agg.assemble_data_metric()
    return result


def prepare_request():
    start_test = os.environ['START_TEST']
    uuid_test = os.environ['UUID_TEST']
    load_plan = os.environ['LOAD_PLAN']
    jxm_path = os.environ['JMX_PATH']
    ui_version = os.environ['UI_VERSION']
    cms_version = os.environ['CMS_VERSION']
    db_version = os.environ['DB_VERSION']
    test_desc = os.environ['TEST_DESC']
    test_name = os.environ['TESTNAME']
    test_type = os.environ.get('TEST_TYPE', 'max_performance_search')
    bot_id = os.environ['BOT_ID']
    chat_id = os.environ['CHAT_ID']
    cts_host = os.environ['CTS_HOST']
    secret_key = os.environ['SECRET_KEY']
    app_versions = os.environ['APP_VERSIONS']
    confluence_host = os.environ['CONFLUENCE_HOST']
    confluence_space = os.environ['CONFLUENCE_SPACE']
    confluence_token = os.environ['CONFLUENCE_TOKEN']
    confluence_page = os.environ['CONFLUENCE_PAGE']
    confluence_title = os.environ['CONFLUENCE_TITLE']
    confluence_parent = os.environ['CONFLUENCE_PARENT']
    confluence_parent_page = os.environ['PARENT_PAGE']
    influx_host = os.environ['INFLUX_HOST']
    influx_port = os.environ['INFLUX_PORT']
    influx_org = os.environ['INFLUX_ORG']
    influx_bucket = os.environ['INFLUX_BUCKET']
    influx_db = os.environ['INFLUX_DB']
    influx_url = os.environ['INFLUX_URL']
    influx_token = os.environ['INFLUX_TOKEN']
    vault_token = os.environ['VAULT_TOKEN']
    argo_url = os.environ['ARGO_URL']
    argo_token = os.environ['ARGO_TOKEN']
    grafana_host = os.environ['GRAFANA_HOST']
    grafana_snapshot_nodejs = os.environ['GRAFANA_SNAPSHOT_NODEJS']
    grafana_snapshot_jmeter = os.environ['GRAFANA_SNAPSHOT_JMETER']
    grafana_snapshot_elastic = os.environ['GRAFANA_SNAPSHOT_ELASTIC']
    grafana_snapshot_pods = os.environ['GRAFANA_SNAPSHOT_PODS']
    grafana_snapshot_nodes = os.environ['GRAFANA_SNAPSHOT_NODES']
    report_url = os.environ['REPORT_URL']
    service = os.environ['SERVICE']
    grafana_user = os.environ['GRAFANA_USER']
    grafana_pass = os.environ['GRAFANA_PASS']
    if type(load_plan) is str:
        logger.debug(f"load_plan as str detected")
        load_plan = json.loads(load_plan)
    logger.debug(f'report_url = "{report_url}"')
    logger.debug(f'start_test = "{start_test}"')
    logger.debug(f'uuid_test = "{uuid_test}"')
    logger.debug(f'influx_token = "{influx_token}"')
    logger.debug(f'load_plan = {load_plan}')
    logger.debug(f'influx_org = "{influx_org}"')
    logger.debug(f'influx_bucket = "{influx_bucket}"')
    logger.debug(f'influx_db = "{influx_db}"')
    logger.debug(f'influx_url = "{influx_url}"')
    logger.debug(f'report_url = "{report_url}"')
    logger.debug(f'service = "{service}"')
    logger.debug(f'grafana_user = "{grafana_user}"')
    logger.debug(f'grafana_pass = "{grafana_pass}"')
    logger.debug(f'test_type = "{test_type}"')
    logger.debug(f'test_name = "{test_name}"')
    logger.debug(f"start create report")

    now = datetime.now()
    confluence_date = now.strftime("%Y-%m-%d %H:%M")

    confluence_title = f"{confluence_date} {test_type}"
    payload = {
        "test": {
            "start_datetime": start_test,
            "uuid": uuid_test,
            "load_plan": load_plan,
            "service": "host",
            "jmx": jxm_path,
            "test_desc": test_desc
        },
        "express": {
            "chat_id": chat_id,
            "cts_host": cts_host,
            "bot_id": bot_id,
            "secret_key": secret_key
        },
        "settings" :{
            "ui_version": ui_version,
            "cms_version": cms_version,
            "db_version": db_version
        },
        "server": {
            "type": "confluence",
            "host": confluence_host,
            "token": confluence_token,
            "space": confluence_space,
            "parent": confluence_parent_page,
            "title": confluence_title,
            "date": confluence_date
        },
        "influx": {
            "url": influx_url,
            "type": "flux",
            "host": influx_host,
            "port": influx_port,
            "db": influx_db,
            "org": influx_org,
            "bucket": influx_bucket,
            "token": influx_token
        },
        "applications": [
            {
                "application": "host-external-load-host-web-ui",
                "namespace": "host-external-load",
                "resource": "host-web-ui",
                "kind": "Deployment"
            },
            {
                "application": "host-external-load-host-web-cms-core",
                "namespace": "host-external-load",
                "resource": "host-web-cms-core",
                "kind": "Deployment"
            }
        ],
        "argo": {
            "host": argo_url,
            "token": argo_token
        },
        "vault": {
            "token": vault_token,
            "applications": [
                "host-external-load/data/host-web-cms-core",
                "host-external-load/data/host-web-ui"
            ]
        },
        "grafana": {
            "scheme": "https",
            "host": grafana_host,
            "snapshot_template_nodejs": grafana_snapshot_nodejs,
            "snapshot_template_jmeter": grafana_snapshot_jmeter,
            "snapshot_template_elastic": grafana_snapshot_elastic,
            "snapshot_template_pods": grafana_snapshot_pods,
            "snapshot_template_nodes": grafana_snapshot_nodes,
            "user": grafana_user,
            "pwd": grafana_pass
        },
        "test_type": test_type,
        "test_name": test_name
    }
    # headers = {
    #     'Content-Type': 'application/json'
    # }
    logger.debug(f"request data: {payload}")
    # response = requests.request("POST", report_url, headers=headers, data=payload)
    # response_data = response.text
    # logger.debug(f"response response status: {response.status_code}")
    # logger.debug(f"response response_data: {response_data}")
    return payload


class CreateReport:
    def __init__(self, request):
        logger.debug(f"[create_report] Start")
        logger.debug(f"[create_report] request: {request}")

        self.request = request
        self.test = request.test
        self.server = request.server
        self.settings = request.settings
        self.grafana_base = request.grafana
        self.argo_base = request.argo
        self.load_plan = request.test.load_plan
        self.test_desc = request.test.test_desc
        self.jmx_path = request.test.jmx
        self.start_date = request.test.start_datetime
        self.end_date = utils.get_end_time_from_load_plan(self.start_date, self.load_plan)
        self.start_date_unix: int = int(self.start_date.timestamp()) * 1000
        self.end_date_unix: int = int(self.end_date.timestamp()) * 1000
        self.grafana_service = GrafanaService(host=request.grafana.host, port=request.grafana.port)
        self.ec = ExpressCLient()
        self._max_rps = None
        self._page_response_times_for_api = []
        self._jmeter_snapshot_url = None
        self.ec.set_env(bot_id=self.request.express.bot_id,
                   secret_key=self.request.express.secret_key,
                   cts_host=self.request.express.cts_host)
        ###########################################################################################
        ############### Client init Block
        ###########################################################################################

        logger.debug(f"[create_report] Client init Block")
        if (self.request.server.type == ServerType.CONFLUENCE):
            self.page_client = ConfluenceClient(url=f'https://{self.server.host}',
                                                host=f'{self.server.host}',
                                                token=self.server.token,
                                                verify_ssl=False)
        elif (self.request.server.type == ServerType.YANDEX):
            self.page_client = YandexClient(url=f'https://{settings.yandex_host}',
                                            username=settings.yandex_login,
                                            password=settings.yandex_password,
                                            verify_ssl=False)
        elif (self.request.server.type == ServerType.MARKDOWN):
            self.page_client = MarkdownClient("/tmp/report.md")

        elif (self.request.server.type == ServerType.HTML):
            self.page_client = HtmlClient()

    def create(self):
        logger.debug(f"[create] Start")

        ###########################################################################################
        ############### Header init Block
        ###########################################################################################
        logger.debug(f"[create_report] Header init Block")
        # Table of contents and objectives
        self.page_template = page()(
            toc(),
            *block_purpose(self.test_desc)
        )
        self.page_template(block_conclusion())

        ###########################################################################################
        ############### Influx Block
        ###########################################################################################

        logger.debug(f"[create_report] Influx Block")

        # Business metrics and charts
        if self.request.test.service:
            self.page_template(tag('h2')('Business metrics'))
            logger.debug("call get_influx_metrics")
            data = get_influx_metrics(request=self.request)
            logger.debug("call get_influx_metrics done")
            if data is not None:
                # Max RPS for max-performance search (all steps ≤ 400 ms)
                test_type_val = getattr(self.request, 'test_type', None) or os.environ.get('TEST_TYPE', '')
                if test_type_val in MAX_RPS_CALCULATION_TYPES:
                    self._max_rps = get_max_rps_for_sla(data, self.load_plan)
                    logger.info(f"[create_report] max_rps (SLA ≤400ms): {self._max_rps}")
                if self._max_rps is None and self.load_plan:
                    self._max_rps = self.load_plan[-1][3]
                if self._max_rps is not None:
                    self._page_response_times_for_api = extract_page_response_times(
                        data, load_level=self._max_rps
                    )
                self.page_template(tag('h3')('Aggregated metrics table'))
                data_display = data.dropna()
                data_colored = data_display.style.applymap(lambda x: highlight(x)).format('{:.0f}').set_properties(
                    **{'text-align': 'left'}).set_table_styles(
                    [{'selector': 'th, td', 'props': [('text-align', 'left'), ('border', '0.5px solid black')]}])
                html_data_processed = html_data(data=data_colored.to_html())
                logger.debug(f"html_data_processed: {html_data_processed}")
                self.page_template(html_data_processed)
            else:
                return "Influx data is empty", 404

        ###########################################################################################
        ############### Jmeter Block
        ###########################################################################################

        logger.debug(f"[create_report] Jmeter Block")
        # Business metric charts
        self.page_template(tag('h3')('Business metric charts'))

        snapshots = [{'title': 'title', 'type': 'graph', 'url': 'url'}]
        snapshot_url = f"{self.request.grafana.snapshot_template_jmeter.format(self.request.test.uuid)}"
        logger.debug(f"[__main__] snapshot_url: {snapshot_url}")
        snapshots = self.grafana_service.get_snapshot(grafana_login=self.request.grafana.user,
                                                      grafana_password=self.request.grafana.pwd,
                                                      dashboard_url=snapshot_url, date_from=self.start_date_unix,
                                                      date_to=self.end_date_unix)
        logger.debug(f"[__main__] snapshots: {snapshots}")
        ltg_jmeter = self.page_client.build_snapshot_tag_uitabs(snapshots)
        logger.debug(f"[__main__] ltg_jmeter: {ltg_jmeter}")
        self._jmeter_snapshot_url = None
        if (self.request.server.type == ServerType.MARKDOWN):
            self.page_template(link(ltg_jmeter))
        elif (self.request.server.type == ServerType.HTML):
            self.page_template(link(ltg_jmeter))
        else:
            html_client = HtmlClient()
            html_dashboards_jmeter = html_client.build_snapshot_tag(snapshots)
            self._jmeter_snapshot_url = html_client.get_jmeter_dashboard_for_bot(snapshots)
            self.page_template(tag('h4')('Snapshot links'))
            self.page_template(html_data(html_dashboards_jmeter))
            self.page_template(tag('h4')('Charts'))
            self.page_template(ltg_jmeter)

        ###########################################################################################
        ############### Methodology block
        ###########################################################################################
        #
        logger.debug(f"[create_report] MNT Block")
        self.page_template(*block_mnt(self.load_plan, self.jmx_path))
        self.page_template(tag('h1')('Test results'))

        # ###########################################################################################
        # ############### Argo Block
        # ###########################################################################################

        self.page_template(*block_config_ppo(argo_base=self.request.argo, vault_base=self.request.vault,
                                             applications=self.request.applications))


        # ###########################################################################################
        # ############### host Web Pods Block
        # ###########################################################################################
        self.create_snapshots_block(name="Pod utilization",
                                    dashboard_url=self.request.grafana.snapshot_template_pods)

        # ###########################################################################################
        # ############### K8S Nodes Block
        # ###########################################################################################

        self.create_snapshots_block(name="Kubernetes node utilization",
                                    dashboard_url=self.request.grafana.snapshot_template_nodes)

        # ###########################################################################################
        # ############### Nodejs Block
        # ###########################################################################################

        self.create_snapshots_block(name="Node.js utilization",
                                    dashboard_url=self.request.grafana.snapshot_template_nodejs)

        # ###########################################################################################
        # ############### Requests Elastic Block
        # ###########################################################################################

        self.create_snapshots_block(name="Request duration chart",
                                    dashboard_url=self.request.grafana.snapshot_template_elastic)

        ###########################################################################################
        ############### AWR Block
        ###########################################################################################

        # logger.debug(f"[create_report] AWR Block")
        #
        # awr = None
        # if request.awr:
        #     if hasattr(request.awr, 'sid'):
        #         awr = AWROracle(start_date=start_date, load_plan=load_plan, **dict(request.awr))
        #     elif hasattr(request.awr, 'dbname'):
        #         awr = AWRPostgres(start_date=start_date, load_plan=load_plan, **dict(request.awr))
        # if awr:
        #     awr.get_awr()
        #     awr.upload_attachment(page_client, page_data['id'])
        #     page_template(*block_result_awr(awr))

        ###########################################################################################
        ############### Update Block
        ###########################################################################################

        logger.debug(f"[create_report] Update Block server.type: {self.request.server.type}")
        # CREATE_REPORT gate
        create_report_flag = os.environ.get('CREATE_REPORT', 'True').lower() == 'true'
        page_id = None
        report_url = ""
        jmeter_url = getattr(self, '_jmeter_snapshot_url', None) or ""
        
        if create_report_flag:
            page_body = self.page_template.render()
            # logger.debug(f"Before update page_body: {page_body}")
            if (self.request.server.type == ServerType.CONFLUENCE):
                logger.debug(f"ServerType CONFLUENCE")
                if self.server.page:
                    # Update existing page
                    page_id = self.page_client.get_page_id(space=self.server.space, title=self.server.page)
                    page_data = self.page_client.get_page_by_id(page_id, expand='body.storage')
                    logger.debug(f"[create_report] page_data: {page_data}")
                    page_data = self.page_client.get_page_by_title(self.server.space, self.server.page)
                    title = self.server.title
                    # logger.debug(f"Before update page_data: {page_data}")
                else:
                    # Create a new page
                    logger.debug(f"Create page")
                    title = self.server.title + " " + settings.ui_version + " " + settings.cms_version
                    page_data = self.page_client.create_page(str(self.server.space), title, '',
                                                             parent_id=self.server.parent, type='page',
                                                             representation='storage', editor='v2', full_width=False)
                # logger.debug(f"page_body: {page_body}")
                page_data = self.page_client.update_page(page_data['id'], title, page_body, parent_id=self.server.parent,
                                                         type='page', representation='storage')
                page_id = page_data['id']
            elif (self.request.server.type == ServerType.HTML):
                page_data = self.page_client.write_html("/tmp/report.html", page_body)
            elif (self.request.server.type == ServerType.MARKDOWN):
                page_data = self.page_client.write_html(page_body)
                # page_data = page_body
            else:
                return "Unknown ServerType", 404
            
            logger.debug(f"[create_report] page_id: {page_id}")
            report_base = getattr(self.server, 'host', None) or os.environ.get('CONFLUENCE_HOST', 'confluence.example.com')
            report_url = f"https://{report_base}/pages/viewpage.action?pageId={page_id}" if page_id else ""
        else:
            logger.info("[create_report] CREATE_REPORT=False, skipping report creation in Confluence")

        # Reporting flags (independent)
        save_to_storage = os.environ.get('SAVE_TO_STORAGE', 'True').lower() == 'true'
        send_bot_notification = os.environ.get('SEND_BOT_NOTIFICATION', 'True').lower() == 'true'

        # Optional push to external report storage API
        if save_to_storage:
            clinic_reports_url = os.environ.get('CLINIC_REPORTS_URL', '')
            if clinic_reports_url and self.settings:
                test_type = getattr(self.request, 'test_type', None) or os.environ.get('TEST_TYPE') or 'max_performance_search'
                test_name = getattr(self.request, 'test_name', None) or os.environ.get('TESTNAME', '')
                test_identifier = f"perf-{test_name}-{self.request.test.start_datetime.strftime('%Y%m%d-%H%M')}" if test_name else f"perf-{self.request.test.uuid}"
                grafana_url = self.request.grafana.snapshot_template_jmeter.format(self.request.test.uuid) if self.request.grafana else ""
                taurus_exit = os.environ.get('TAURUS_EXIT_CODE', '1')
                test_passed = str(taurus_exit).strip() == '0'
                send_performance_test(
                    clinic_reports_url,
                    ui_version=self.settings.ui_version,
                    cms_version=self.settings.cms_version,
                    db_version=self.settings.db_version or "",
                    test_date=self.request.test.start_datetime,
                    test_end_time=self.end_date,
                    test_identifier=test_identifier,
                    test_type=test_type,
                    requests_per_second=getattr(self, '_max_rps', None),
                    test_description=self.request.test.test_desc or "",
                    test_plan=os.path.basename(self.request.test.jmx or ""),
                    script_path=self.request.test.jmx or "",
                    confluence_url=report_url,
                    grafana_dashboard_url=grafana_url,
                    page_response_times=getattr(self, '_page_response_times_for_api', []),
                    test_passed=test_passed,
                )

        # Optional chat bot notification
        if send_bot_notification:
            self.send_express_event(report_url=report_url, jmeter_url=jmeter_url)
        logger.debug(f"[create_report] success")
        return page_data

    def send_express_event(self, report_url, jmeter_url):
        logger.debug(f"[send_express_event] start")
        text = f"""Date: {self.request.test.start_datetime}
Test: {self.request.test.jmx}
UUID: {self.request.test.uuid}
Description: {self.request.test.test_desc}
UI: {self.settings.ui_version}
CMS: {self.settings.cms_version}
DB: {self.settings.db_version}
Report: {report_url}
JMeter: {jmeter_url}"""
        self.ec.send_message(chat_id=self.request.express.chat_id, data=text)

    def create_snapshots_block(self, name: str, dashboard_url: str):
        logger.debug(f"[create_report] {name} Block")
        self.page_template(tag('h2')(name))
        snapshots_header = [{'title': 'title', 'type': 'graph', 'url': 'url'}]
        logger.debug(f"[create_snapshots_block] snapshot_url: {dashboard_url}")
        snapshots_tmp = self.grafana_service.get_snapshot(grafana_login=self.request.grafana.user,
                                                          grafana_password=self.request.grafana.pwd,
                                                          dashboard_url=dashboard_url,
                                                          date_from=self.start_date_unix,
                                                          date_to=self.end_date_unix)
        logger.debug(f"[create_snapshots_block] snapshots_elastic: {snapshots_tmp}")
        ltg_tmp = self.page_client.build_snapshot_tag_uitabs(snapshots_tmp)
        logger.debug(f"[create_snapshots_block] ltg_tmp: {ltg_tmp}")

        if (self.request.server.type == ServerType.MARKDOWN):
            self.page_template(link(ltg_tmp))
        elif (self.request.server.type == ServerType.HTML):
            self.page_template(link(ltg_tmp))
        else:
            html_client = HtmlClient()
            html_dashboards_tmp = html_client.build_snapshot_tag(snapshots_tmp)
            self.page_template(tag('h4')('Snapshot links'))
            self.page_template(html_data(html_dashboards_tmp))
            self.page_template(tag('h4')('Charts'))
            self.page_template(ltg_tmp)


def highlight(cell):
    if int(cell) > 400:
        return 'background-color: salmon'


@app.post("/report")
def create_report(request_data: RequestCreateReport, response: Response):
    create_request = CreateReport(request_data)
    return create_request.create()


if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=9200, timeout_keep_alive=15)
    logger.debug(f"[main] prepare_request")
    payload = prepare_request()
    request = RequestCreateReport(**payload)
    logger.debug(f"[main] request: {request}")
    reporter = CreateReport(request=request)
    reporter.create()
