from urllib.parse import urlparse
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import logging
from selenium.webdriver.remote.remote_connection import LOGGER
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
# from selenium.webdriver.firefox.options import Options

LOGGER.setLevel(logging.WARNING)

def create_driver():
    # chromedriver = "/usr/bin/chromedriver"
    # chromedriver = "C:\\chromedriver.exe"

    # service = Service(chromedriver)
    options = Options()

    # options.binary_location = "/opt/google/chrome/google-chrome"
    # options.binary_location = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("disable-infobars")
    options.add_argument("start-maximized")
    options.add_argument("enable-automation")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-browser-side-navigation")
    # options.add_argument("--disable-popup-blocking")
    # options.add_argument('--headless')
    # options.add_argument('--no-sandbox')
    # options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--chrome.switches')
    # options.add_argument('--disable-background-networking')
    # options.add_argument('--disable-browser-side-navigation')
    # options.add_argument('--disable-client-side-phishing-detection')
    # options.add_argument('--disable-default-apps')
    # options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--disable-extensions')
    # options.add_argument('--disable-gpu')
    # options.add_argument('--disable-hang-monitor')
    # options.add_argument('--disable-infobars')
    # # options.add_argument('--disable-popup-blocking')
    # options.add_argument('--disable-prompt-on-repost')
    # options.add_argument('--disable-setuid-sandbox')
    # options.add_argument('--disable-sync')
    # options.add_argument('--disable-web-resources')
    # options.add_argument('--enable-automation')
    # options.add_argument('--enable-blink-features=ShadowDOMV0')
    # options.add_argument('--enable-logging')
    # options.add_argument('--force-fieldtrials=SiteIsolationExtensions/Control')
    # options.add_argument('--ignore-certificate-errors')
    # options.add_argument('--log-level=0')
    # options.add_argument('--no-first-run')
    # options.add_argument('--password-store=basic')
    # options.add_argument('--remote-debugging-port=0')
    # options.add_argument('--start-maximized')

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


def create_firefox_driver():
    firefox_options = Options()
    firefox_options.add_argument('--headless')
    firefox_options.add_argument('--disable-gpu')
    firefox_options.add_argument(f'--width=1920')
    firefox_options.add_argument(f'--height=1080')
    firefox_options.accept_insecure_certs = True

    selenium_wire_options = {
        'network.stricttransportsecurity.preloadlist': False,
        'network.stricttransportsecurity.enabled': False,
    }

    driver = webdriver.Firefox(options=firefox_options, seleniumwire_options=selenium_wire_options)

    driver.set_page_load_timeout(30)

    return driver