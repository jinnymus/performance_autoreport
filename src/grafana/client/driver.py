import logging

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from seleniumwire import webdriver

logger = logging.getLogger('root')
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    force=True
)

def create_driver():
    """Создание оптимизированного Chrome WebDriver с лучшими настройками производительности"""
    try:
        chrome_options = ChromeOptions()

        chrome_options.add_argument("--headless=new")
        # Основные настройки производительности
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript")  # Отключить если JS не нужен

        # Размер окна
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
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


def create_firefox_driver():
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
        firefox_options.set_preference("general.useragent.override",
                                       "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0")

        # Отключение изображений для ускорения
        firefox_options.set_preference("permissions.default.image", 2)
        firefox_options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", "false")

        driver = webdriver.Firefox(options=firefox_options)

        logger.debug("Firefox WebDriver создан успешно")
        return driver

    except Exception as e:
        logging.error(f"Ошибка создания Firefox WebDriver: {e}")
        raise