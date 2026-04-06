import json
import logging
import re
import time
import traceback
import uuid
from datetime import datetime

import pytz
import requests
import urllib3
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotVisibleException, \
    ElementNotSelectableException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
# from selenium.webdriver.support.ui import FluentWait
from seleniumwire import webdriver

logger = logging.getLogger('root')
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    force=True
)


# Отключение избыточных логов
urllib3.disable_warnings()
logging.getLogger("hpack.hpack").setLevel(logging.WARNING)
logging.getLogger("hpack.table").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("selenium.webdriver.remote.remote_connection").setLevel(logging.WARNING)

def create_optimized_chrome_driver():
    """Создание оптимизированного Chrome WebDriver с лучшими настройками производительности"""
    try:
        chrome_options = ChromeOptions()
        
        # Основные настройки производительности
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")  # Отключить если JS не нужен
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("enable-automation")

        # Размер окна
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--remote-debugging-pipe")  # Для ChromeDriver 117+

        # Антидетект настройки
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Дополнительные настройки стабильности
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.debug("Chrome WebDriver создан успешно")
        return driver
        
    except Exception as e:
        logging.error(f"Ошибка создания Chrome WebDriver: {e}")
        raise

def create_optimized_firefox_driver():
    """Создание оптимизированного Firefox WebDriver с лучшими настройками производительности"""
    try:
        firefox_options = FirefoxOptions()
        
        # Основные настройки производительности
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-gpu")
        firefox_options.add_argument("--disable-dev-shm-usage")
        
        # Настройки профиля для производительности
        firefox_options.set_preference("media.volume_scale", "0.0")
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference("useAutomationExtension", False)
        firefox_options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")
        
        # Отключение изображений для ускорения
        firefox_options.set_preference("permissions.default.image", 2)
        firefox_options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", "false")
        
        driver = webdriver.Firefox(options=firefox_options)
        
        logger.debug("Firefox WebDriver создан успешно")
        return driver
        
    except Exception as e:
        logging.error(f"Ошибка создания Firefox WebDriver: {e}")
        raise

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
        
        logger.debug(f"Grafana объект создан: {scheme}://{host}:{port}")

    def create_smart_wait(self, timeout=80, poll_frequency=0.5):
        """Создание умного ожидания с FluentWait"""
        # return (FluentWait(self.driver).with_timeout(timeout).
        #         polling_every(poll_frequency).ignoring(NoSuchElementException))

        return WebDriverWait(self.driver, timeout, poll_frequency=poll_frequency,
                             ignored_exceptions=[NoSuchElementException,
                                                 ElementNotVisibleException,
                                                 ElementNotSelectableException])

    @classmethod
    def build_from_url(cls, url: str):
        try:
            scheme = re.findall(r'(https?)://', url)[0]
            logger.debug(f"scheme: {scheme}")
            
            host_port = re.findall(':\\/\\/(.+?):?/', url)[0]
            logger.debug(f"host_port: {host_port}")
            
            if re.search(':', host_port):
                host = re.findall(':\\/\\/([0-9a-z-.]+):([0-9]+)[\\/]', url)[0][0]
                port = re.findall(':\\/\\/([0-9a-z-\\.]+):([0-9]+)[\\/]', url)[0][1]
                logger.debug(f"host: {host}, port: {port}")
            else:
                host = host_port
                if scheme == "https":
                    port = "443"
                elif scheme == "http":
                    port = "80"
                    
            uid = re.findall('d\\/(.+?)\\/', url)[0]
            logger.debug(f"URL разобран успешно - scheme: {scheme}, host: {host}, port: {port}, uid: {uid}")
            
            obj = cls(scheme=scheme, host=host, port=port, uid=uid)
            obj.variables = {v[0]: v[1] for v in re.findall('var-(.+?)=(.+?)(&|$)', url)}
            obj.date_from = int(re.findall('from=(\\d+)', url)[0])
            obj.date_to = int(re.findall('to=(\\d+)', url)[0])
            obj.__url_dashboard = url
            
            return obj
            
        except Exception as e:
            logging.error(f"Ошибка разбора URL: {e}")
            raise

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
            if re.findall('^\\d+$', date):
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
        # Выбор драйвера - можно переключать между Chrome и Firefox
        self.__driver = create_optimized_chrome_driver()  # или create_optimized_firefox_driver()
        self.wait = None
        self.session = requests.Session()
        logger.debug("GrafanaSnapshot инициализирован")

    @property
    def driver(self):
        return self.__driver

    def get_structure_dashboard(self, unknown: bool = False) -> list[dict]:
        try:
            dashboards_url = f'{self.scheme}://{self.host}:{self.port}/api/dashboards/uid/{self.uid}'
            logger.debug(f"dashboards_url: {dashboards_url}")
            
            response = self.session.get(dashboards_url)
            logger.debug(f"response: {response}")
            
            panels = response.json()['dashboard']['panels']
            dashboard = []
            
            for panel in panels:
                logger.debug(f"panel title: {panel['title']} type: {panel['type']}")
                
                if panel['type'] == 'row':
                    dashboard.append({'type': 'row', 'title': panel['title']})
                elif panel['type'] in ['graph', 'timeseries']:
                    dashboard.append({'type': 'graph', 'title': panel['title'], 'id': panel['id']})
                elif panel['type'] in ['stat']:
                    dashboard.append({'type': 'stat', 'title': panel['title'], 'id': panel['id']})
                elif unknown:
                    dashboard.append({'type': 'unknown', 'title': panel['title']})
                    
            logger.debug(f"Структура дашборда получена, панелей: {len(dashboard)}")
            return dashboard
            
        except Exception as e:
            logging.error(f"Ошибка получения структуры дашборда: {e}")
            raise

    def auth(self, login: str = None, password: str = None):
        try:
            payload = {
                'user': login,
                'password': password
            }
            
            response = self.session.post(
                f'{self.scheme}://{self.host}:{self.port}/login',
                headers={'Content-type': 'application/json'},
                data=json.dumps(payload),
                verify=False,
                timeout=30
            )
            
            logger.debug(f"Авторизация через API - статус: {response.status_code}")
            return response
            
        except Exception as e:
            logging.error(f"Ошибка API авторизации: {e}")
            raise

    def create_driver(self):
        try:
            self.driver.get(f'{self.scheme}://{self.host}:{self.port}')
            
            wait = self.create_smart_wait(100)
            logger.debug(f"host: {self.host} port: {self.port}")
            
            welcome = wait.until(
                EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Welcome to Grafana')]"))
            )
            logger.debug("Welcome сообщение найдено")
            
        except TimeoutException as e:
            logging.error(f"Таймаут при загрузке Grafana: {e}")
            self.driver.save_screenshot('error_create_driver.png')
            self.__driver.quit()
            exit(20)
        except Exception as e:
            logging.error(f"Ошибка создания драйвера: {e}")
            self.__driver.quit()
            exit(20)

    def authorize(self, login: str = None, password: str = None, pickle_file=None):
        try:
            self.login = login if login is not None else self.login
            self.password = password if password is not None else self.password
            
            self.driver.set_page_load_timeout(60)
            self.driver.get(f'{self.scheme}://{self.host}:{self.port}/login')
            
            wait = self.create_smart_wait(80)
            logger.debug(f"Переход на страницу логина: {self.host}:{self.port}")

            # Оптимизированные локаторы (убрал дублирование data-testid)
            username_field = wait.until(
                EC.visibility_of_element_located((By.XPATH, '//input[@data-testid="data-testid Username input field"]'))
            )
            logger.debug("Поле логина найдено")

            password_field = wait.until(
                EC.visibility_of_element_located((By.XPATH, '//input[@data-testid="data-testid Password input field"]'))
            )
            logger.debug("Поле пароля найдено")

            submit_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="data-testid Login button"]'))
            )
            logger.debug("Кнопка входа найдена")

            # Ввод данных
            username_field.clear()
            username_field.send_keys(self.login)
            logger.debug(f"Логин введен: {self.login}")

            password_field.clear()
            password_field.send_keys(self.password)
            logger.debug("Пароль введен")

            submit_button.click()
            logger.debug("Кнопка входа нажата")

            # Ожидание успешной авторизации
            welcome = wait.until(
                EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Welcome to Grafana')]"))
            )
            logger.debug("Авторизация успешна - Welcome сообщение найдено")

        except TimeoutException as e:
            logging.error(f"Таймаут при авторизации: {e}")
            self.driver.save_screenshot('error_authorize_timeout.png')
            self.__driver.quit()
            exit(20)
        except Exception as e:
            logging.error(f"Ошибка авторизации: {e}")
            self.driver.save_screenshot('error_authorize.png')
            self.__driver.quit()
            exit(20)

    def create_graphql_snapshot(self, name: str, id: int, postfix: str = None, type: str = "graph"):
        try:
            postfix = postfix if postfix is not None else str(uuid.uuid4())
            url = f"{self.url}&viewPanel=panel-{id}&kiosk"
            
            logger.debug(f"Создание снапшота: {name}, ID: {id}, тип: {type}")
            logger.debug(f"URL панели: {url}")

            # Переход на панель с повторными попытками
            for i in range(10):
                self.driver.get(url)
                logger.debug(f"Попытка {i+1}: переход на URL")
                
                if self.driver.current_url == url:
                    logger.debug("URL загружен успешно")
                    break
                time.sleep(1)

            wait = self.create_smart_wait(500)
            
            # Проверка на "No data"
            try:
                no_data_wait = self.create_smart_wait(20)
                no_data_element = no_data_wait.until(
                    EC.visibility_of_element_located((By.XPATH, '//div[@data-testid="data-testid Panel data error message"]'))
                )
                no_data = no_data_element.text
                logger.debug(f"Проверка данных: {no_data}")
                
                if no_data == "No data":
                    logging.warning("Нет данных для панели")
                    return None
                    
            except TimeoutException:
                logger.debug("Элемент 'No data' не найден - продолжаем")
                no_data = None

            if type == "graph":
                # Ожидание загрузки графика
                logger.debug("Ожидание загрузки графика scrollbar")
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".scrollbar-view")))
                logger.debug("scrollbar-view загружен")
                
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="uplot-main-div"]')))
                logger.debug("uplot-main-div загружен")

            # Создание снапшота
            container = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@data-testid="header-container"]'))
            )
            container.click()
            logger.debug("Контейнер хедера нажат")

            menu_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@data-testid="header-container"]//button[@title="Menu"]'))
            )
            menu_button.click()
            logger.debug("Меню открыто")

            share_item = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="data-testid Panel menu item Share"]'))
            )
            share_item.click()
            logger.debug("Пункт Share нажат")

            tab_snapshot = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="data-testid Tab Snapshot"]'))
            )
            tab_snapshot.click()
            logger.debug("Вкладка Snapshot открыта")

            if type == "graph":
                # Настройка срока действия
                list_expire = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//label[@for="expire-select-input"]/parent::div/following::div/div/div'))
                )
                list_expire.click()
                logger.debug("Список срока действия открыт")

                list_expire_never = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//label[@for="expire-select-input"]/parent::div/following::div//input[@type="radio" and @id="option-0-expire-select-input"]/parent::div'))
                )
                list_expire_never.click()
                logger.debug("Выбран срок 'никогда'")

            # Ввод имени снапшота
            snapshot_name = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, '[id="snapshot-name-input"]'))
            )
            snapshot_name.clear()
            snapshot_name_value = f"{name}_{postfix}"
            snapshot_name.send_keys(snapshot_name_value)
            logger.debug(f"Имя снапшота введено: {snapshot_name_value}")

            # Создание снапшота
            create_snapshot_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@data-testid="data-testid publish snapshot button"]'))
            )
            create_snapshot_button.click()
            logger.debug("Кнопка создания снапшота нажата")

            # Ожидание создания
            time.sleep(10)

            # Получение URL снапшота
            snapshot_url_element = wait.until(
                EC.visibility_of_element_located((By.XPATH, '//input[@data-testid="data-testid snapshot copy url input"]'))
            )
            snapshot = snapshot_url_element.get_attribute('value')
            
            snapshot_key = snapshot.split('/')[-1]
            snapshot_json_url = f'{self.scheme}://{self.host}:{self.port}/api/snapshots/{snapshot_key}'
            
            logger.debug("URL снапшота получен")

            # Закрытие диалога
            close_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Close"]'))
            )
            close_button.click()
            logger.debug("Диалог закрыт")

            # time.sleep(10)

            data_return = snapshot.replace("http://localhost:3000", f"{self.scheme}://{self.host}:{self.port}") + f"?orgId=1&viewPanel=panel-{id}"
            
            # Получение JSON снапшота
            response = self.session.get(snapshot_json_url, verify=False, timeout=30)
            snapshot_json = response.json()
            
            logger.debug(f"Снапшот создан успешно: {data_return}")
            return data_return

        except TimeoutException as e:
            logging.error(f"Таймаут при создании снапшота: {e}")
            self.driver.save_screenshot('error_snapshot_timeout.png')
            self.__driver.quit()
            exit(30)
        except Exception as e:
            logging.error(f"Ошибка создания снапшота: {e}")
            logging.error(traceback.format_exc())
            self.driver.save_screenshot('error_snapshot.png')
            self.__driver.quit()
            exit(30)

    def driver_close(self):
        try:
            logger.debug("Закрытие WebDriver")
            self.__driver.quit()
        except Exception as e:
            logging.error(f"Ошибка при закрытии драйвера: {e}")