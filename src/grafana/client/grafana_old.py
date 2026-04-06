import json
import logging
from urllib.parse import urlparse
import uuid

import urllib3, re
import pytz
import requests
import time
import traceback
import pickle

from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from seleniumwire import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from lxml import html
import demjson3
import yaml
from grafana_old.client.driver import create_driver, create_firefox_driver
from selenium.webdriver.remote.remote_connection import LOGGER

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)

urllib3.disable_warnings()
logging.getLogger("hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("hpack.table").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)



class Grafana:

    def __init__(self, scheme: str, host: str, port: str, uid: str, tz: str = 'Europe%2FMoscow'):
        self.scheme = scheme
        self.host = host
        self.port = port
        self.uid = uid
        self.tz = tz
        self.__variables = dict()
        self.__url_dashboard = f''
        self.__and = '&'
        self.__date_from = None
        self.__date_to = None
        self.__password = None
        self.__login = None

    @classmethod
    def build_from_url(cls, url: str):
        scheme = re.findall(r'(https?)://', url)[0]
        logging.debug(f"[build_from_url] scheme: {scheme}")
        result = re.search(':', url)
        logging.debug(f"[build_from_url] result: {result}")
        host_port = re.findall(':\/\/(.+?):?/', url)[0]
        logging.debug(f"[build_from_url] host_port: {host_port}")
        if re.search(':', host_port):
            logging.debug(f"[build_from_url] : found")
            # logging.debug(f"[build_from_url] : found")
            host = re.findall(':\/\/([0-9a-z-.]+):([0-9]+)[\/]', url)[0][0]
            logging.debug(f"[build_from_url] host: {host}")
            port = re.findall(':\/\/([0-9a-z-\.]+):([0-9]+)[\/]', url)[0][1]
            logging.debug(f"[build_from_url] port: {port}")
        else:
            host = host_port
            # re.findall(':\/\/([0-9a-z\.]+)', url))
            if scheme == "https":
                port = "443"
            elif scheme == "http":
                port = "80"
        uid = re.findall('d\/(.+?)\/', url)[0]
        logging.debug(f"[build_from_url] scheme: {scheme} host: {host} port: {port} uid: {uid}")
        logging.debug(f"[build_from_url] host: {host} port: {port} uid: {uid}")

        obj = cls(scheme=scheme, host=host, port=port, uid=uid)
        # obj.set_variables([(v[0], v[1]) for v in re.findall('var-(.+?)=(.+?)(&|$)', url)])
        obj.variables = {v[0]: v[1] for v in re.findall('var-(.+?)=(.+?)(&|$)', url)}
        obj.date_from = int(re.findall('from=(\d+)', url)[0])
        obj.date_to = int(re.findall('to=(\d+)', url)[0])
        obj.__url_dashboard = url
        return obj

    @property
    def date_from(self):
        return self.__date_from

    @property
    def date_to(self):
        return self.__date_to

    @property
    def url(self):
        return self.__url_dashboard

    @property
    def login(self):
        return self.__login

    @property
    def password(self):
        return self.__password

    @property
    def variables(self):
        return self.__variables

    @url.setter
    def url(self, url):
        self.__url_dashboard = url

    @password.setter
    def password(self, password):
        self.__password = password

    @login.setter
    def login(self, login):
        self.__login = login

    @date_from.setter
    def date_from(self, date_from):
        self.__date_from = date_from

    @date_to.setter
    def date_to(self, date_to):
        self.__date_to = date_to

    @variables.setter
    def variables(self, variables: dict[str, str]):
        self.__variables = variables

    def set_variables(self, variables):
        for name, value in variables:
            if name != 'from' and name != 'to':
                self.__url_dashboard = self.__url_dashboard + ('' if self.__url_dashboard.endswith('?') else self.__and) + f'var-{name}={value}'


    @staticmethod
    def __date_to_int(date):
        if isinstance(date, str):
            if re.findall('^\d+$', date):
                return int(date)
            return int(datetime.strptime(date, '%Y-%m-%d %H:%M:%S').astimezone(pytz.timezone('Europe/Moscow')).timestamp() * 1000)
        elif isinstance(date, datetime):
            return int(date.astimezone(pytz.timezone('Europe/Moscow')).timestamp() * 1000)
        elif isinstance(date, int):
            return date
        else:
            raise TypeError('Date not is valid type')


class GrafanaSnapshot(Grafana):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, tz='Europe%2FMoscow', **kwargs)
        self.__driver = create_driver()
        self.wait = None
        self.session = requests.Session()


    @property
    def driver(self):
        return self.__driver

    def get_structure_dashboard(self, unknown: bool = False) -> list[dict]:
        dashboards_url = f'{self.scheme}://{self.host}:{self.port}/api/dashboards/uid/{self.uid}'
        logging.debug(f"[get_structure_dashboard] dashboards_url: {dashboards_url}")
        response = self.session.get(dashboards_url)
        logging.debug(f"[get_structure_dashboard] response: {response}")
        panels = response.json()['dashboard']['panels']
        dashboard = []
        for panel in panels:
            logging.debug(f"[get_structure_dashboard] panel title: {panel['title']} type: {panel['type']}")
            if panel['type'] == 'row':
                dashboard.append({'type': 'row', 'title': panel['title']})
            if panel['type'] in ['graph', 'timeseries']:
                dashboard.append({'type': 'graph', 'title': panel['title'], 'id': panel['id']})
            if panel['type'] in ['stat']:
                dashboard.append({'type': 'stat', 'title': panel['title'], 'id': panel['id']})
            if unknown:
                dashboard.append({'type': 'unknown', 'title': panel['title']})
        return dashboard

    def auth(self, login: str = None, password: str = None):
        payload = {
            'user': login,
            'password': password
        }
        response = self.session.post(f'{self.scheme}://{self.host}:{self.port}/login', headers={'Content-type': 'application/json'},
                                     data=json.dumps(payload), verify=False,
                                     timeout=30)
        logging.debug(f"[auth] response: {response.json()}")
        return response


    def create_driver(self):
        try:
            self.driver.get(f'{self.scheme}://{self.host}:{self.port}')
            self.wait = WebDriverWait(self.driver, 100)
            logging.debug(f"[create_driver] host: {self.host} port: {self.port}")
            logging.debug(f"[create_driver] Welcome")
            welcome = self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Welcome to Grafana')]")))
            logging.debug(f"[create_driver] welcome: {welcome}")
        except Exception as e:
            logging.debug(f"[Exception] e: {e}")
            self.__driver.close()
            self.__driver.quit()
            exit(20)

    def authorize(self, login: str = None, password: str = None, pickle_file=None):
        try:
            self.login = login if login is not None else self.login
            self.password = password if password is not None else self.password
            self.driver.set_page_load_timeout(40)
            self.driver.get(f'{self.scheme}://{self.host}:{self.port}/login')
            self.wait = WebDriverWait(self.driver, 60)
            logging.debug(f"[authorize] host: {self.host} port: {self.port}")

            username = self.wait.until(EC.presence_of_element_located((By.XPATH,'//input[@data-testid="data-testid Username input field"]')))
            password = self.wait.until(EC.presence_of_element_located((By.XPATH,'//input[@data-testid="data-testid Password input field"]')))
            submit_button = self.driver.find_element(by=By.XPATH, value='//button[@data-testid="data-testid Login button"]')

            logging.debug(f"[authorize] send_keys self.login: {self.login}")
            username.send_keys(self.login)
            logging.debug(f"[authorize] send_keys self.password: {self.password}")
            password.send_keys(self.password)
            submit_button.click()
            logging.debug(f"[authorize] clicked")
            logging.debug(f"[authorize] Welcome")
            welcome = self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Welcome to Grafana')]")))
        except Exception as e:
            logging.debug(f"[Exception] e: {e}")
            self.__driver.close()
            self.__driver.quit()
            exit(20)

    def create_graphql_snapshot(self, name: str, id: int, postfix: str = None, type: str = "graph"):
        logging.debug(f"[create_graphql_snapshot] name: {name} id: {id} postfix: {postfix}")
        url = f"{self.url}&viewPanel=panel-{id}&kiosk"
        try:
            postfix = postfix if postfix is not None else str(uuid.uuid4())
            logging.debug(f"[create_graphql_snapshot] url: {url}")
            # self.driver.set_page_load_timeout(10)
            self.driver.get(url)
            time.sleep(20)

            for i in range(0, 10):
                self.driver.get(url)
                # time.sleep(1)
                logging.debug(f"[create_graphql_snapshot][{i}] url: {url}")
                logging.debug(f"[create_graphql_snapshot][{i}] self.driver.current_url: {self.driver.current_url}")
                if self.driver.current_url != url:
                    logging.debug(f"[create_graphql_snapshot][{i}] continue: {i}")
                    continue
                else:
                    logging.debug(f"[create_graphql_snapshot][{i}] current_urls == url")
                    break

            time.sleep(20)
            logging.debug(f"[create_graphql_snapshot] check graph type: {type}")
            logging.debug(f"[create_graphql_snapshot] Check No data")
            try:
                logging.debug(f"[create_graphql_snapshot] start try")
                WebDriverWait(self.driver, 20).until(
                    EC.visibility_of_element_located((By.XPATH, '//div[@data-testid="data-testid Panel data error message"]'))
                )
                no_data = self.wait.until(EC.presence_of_element_located(
                    (By.XPATH, '//div[@data-testid="data-testid Panel data error message"]'))).text
                logging.debug(f"[create_graphql_snapshot] end try")
            except TimeoutException:
                # If the element is not found or not visible within 10 seconds, a TimeoutException is raised
                logging.debug("Element not found or not visible within the timeout.")
                no_data = None  # Assign None to 'element' in this case

            if no_data == "No data":
                logging.debug(f"[create_graphql_snapshot] No data")
                return None
            else:
                if type == "graph":
                    logging.debug(f"[create_graphql_snapshot] wait scrollbar-view")
                    WebDriverWait(self.driver, 500).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, ".scrollbar-view"))
                    )
                    logging.debug(f"[create_graphql_snapshot] wait uplot-main-div")
                    WebDriverWait(self.driver, 500).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="uplot-main-div"]'))
                    )

                logging.debug(f"[create_graphql_snapshot] wait header-container")
                container = self.wait.until(EC.presence_of_element_located((By.XPATH, f'//div[@data-testid="header-container"]')))
                container.click()

                logging.debug(f"[create_graphql_snapshot] menu item")
                share_item = self.wait.until(EC.presence_of_element_located((By.XPATH, '//div[@data-testid="header-container"]//button[@title="Menu"]')))
                share_item.click()

                logging.debug(f"[create_graphql_snapshot] share_item")
                share_item = self.wait.until(EC.presence_of_element_located((By.XPATH, '//button[@data-testid="data-testid Panel menu item Share"]')))
                share_item.click()

                # time.sleep(3)
                # logging.debug(f"[create_graphql_snapshot] time.sleep(3)")

                logging.debug(f"[create_graphql_snapshot] tab_snapshot")
                tab_snapshot = self.wait.until(EC.presence_of_element_located((By.XPATH, '//button[@data-testid="data-testid Tab Snapshot"]')))
                tab_snapshot.click()

                if type == "graph":
                    logging.debug(f"[create_graphql_snapshot] click list_expire")
                    list_expire = self.wait.until(EC.presence_of_element_located((By.XPATH, """//label[@for="expire-select-input"]/parent::div/following::div/div/div""")))
                    list_expire.click()

                logging.debug(f"[create_graphql_snapshot] click list_expire never")
                list_expire_never = self.wait.until(EC.presence_of_element_located((By.XPATH, """//label[@for="expire-select-input"]/parent::div/following::div//input[@type='radio' and @id='option-0-expire-select-input']/parent::div""")))
                list_expire_never.click()

                logging.debug(f"[create_graphql_snapshot] get snapshot name")
                snapshot_name = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[id="snapshot-name-input"]')))
                snapshot_name.clear()
                logging.debug(f"[create_graphql_snapshot] snapshot_name: {snapshot_name}")

                snapshot_name.send_keys(name + "_" + postfix)
                logging.debug(f"[create_graphql_snapshot] create_snapshot_button")
                create_snapshot_button = self.wait.until(EC.presence_of_element_located((By.XPATH, "//button[@data-testid='data-testid publish snapshot button']")))
                create_snapshot_button.click()
                logging.debug(f"[create_graphql_snapshot] time.sleep(30)")
                time.sleep(30)

                logging.debug(f"[create_graphql_snapshot] snapshot")
                snapshot = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@data-testid='data-testid snapshot copy url input']"))).get_attribute('value')
                snapshot_key = snapshot.split('/')[-1]
                snapshot_json_url = f'{self.scheme}://{self.host}:{self.port}/api/snapshots/{snapshot_key}'
                snapshot_url = f'{self.scheme}://{self.host}:{self.port}/dashboard/snapshot/{snapshot_key}'

                logging.debug(f"[create_graphql_snapshot] close_button")
                close_button = self.wait.until(EC.presence_of_element_located((By.XPATH, '//button[@aria-label="Close"]')))
                close_button.click()
                logging.debug(f"[create_graphql_snapshot] time.sleep(30)")
                time.sleep(10)

                logging.debug(f"[create_graphql_snapshot] return snapshot: {snapshot}")
                data_return = snapshot.replace("http://localhost:3000", f"{self.scheme}://{self.host}:{self.port}") + "?orgId=1&viewPanel=panel-" + str(id)
                logging.debug(f"[create_graphql_snapshot] data_return: {data_return}")

                response = self.session.get(snapshot_json_url, verify=False, timeout=30)
                snapshot_json = response.json()
                # logging.debug(f"[create_graphql_snapshot] snapshot_json: {snapshot_json}")

                return data_return
        except Exception:
            logging.debug(traceback.format_exc())
            self.__driver.close()
            self.__driver.quit()
            exit(30)

    def driver_close(self):
        self.__driver.close()
        self.__driver.quit()
