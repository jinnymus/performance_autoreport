import os
import requests
import logging
from bs4 import BeautifulSoup
from requests import post, Session
import sys
import time
from pyquery import PyQuery

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=config.LOG_LEVEL)

my_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'

headers = {
    "content-type": "application/json",
    # 'accept': 'text/html,application/xhtml+xml,application/xml',
    'user-agent': my_user_agent,
    'origin': 'https://wiki.yandex.ru',
    'priority': 'u=1, i',
    'referer': 'https://wiki.yandex.ru/homepage/reports/.edit',
    'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': "macOS",
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ru',
    'content-type': 'application/json'
}
ya_login = '*'
ya_password = '*'

class YandexClient:
    def __init__(self, url: str=None, username: str=None, password: str=None, verify_ssl:bool=False):
        logger.debug("[connect] init")
        self.url = url
        self.verify_ssl = verify_ssl
        self.client_id = os.environ.get("YANDEX_OAUTH_CLIENT_ID", "")
        self.client_secret = os.environ.get("YANDEX_OAUTH_CLIENT_SECRET", "")
        self.redirect_uri = os.environ.get("YANDEX_OAUTH_REDIRECT_URI", "https://localhost")

    def connect(self):
        import requests

        scope = 'wiki:edit wiki:read'
        auth_url = (
            f'https://oauth.yandex.ru/authorize?response_type=code&client_id={self.client_id}'
            f'&redirect_uri={self.redirect_uri}&scope={scope}'
        )
        print(f'Open this URL to authorize: {auth_url}')
        authorization_code = input('Paste the authorization code: ')
        token_url = 'https://oauth.yandex.ru/token'
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
        }

        response = requests.post(token_url, data=data)
        token_info = response.json()

        if 'access_token' in token_info:
            access_token = token_info['access_token']
            print(f'Access token: {access_token}')
        else:
            print('Token error:', token_info)

    def connect2(self):
        logger.debug("[connect] start")
        # Start session: load the login page and extract csrf_token and process_uuid
        try:
            self.session = requests.Session()
            r_welcome = self.session.get('https://passport.yandex.ru/auth', headers=headers)
            pyquery_object = PyQuery(r_welcome.text)
            csrf_token = pyquery_object('input[name=csrf_token]').val()
            process_uuid_href = pyquery_object('.Button2_type_link:first').attr('href')
            process_uuid = process_uuid_href[process_uuid_href.find('process_uuid=')+13:]
        except Exception as e:
            print(f'Exit script. Error at start session: {e}')
            sys.exit(1)
        else:
            pass

        time.sleep(2.5)
        # POST login; track_id comes from the JSON body (mirror browser form fields)
        try:
            headers['X-Requested-With'] = 'XMLHttpRequest'
            headers['Referer'] = 'https://passport.yandex.ru/auth'
            logger.debug(f"[connect] csrf_token: {csrf_token} process_uuid: {process_uuid}")
            r_start = self.session.post('https://passport.yandex.ru/registration-validations/auth/multi_step/start',
                                {'csrf_token': csrf_token, 'login': ya_login, 'process_uuid': process_uuid},
                                headers={'User-Agent': my_user_agent, 'Referer': 'https://passport.yandex.ru/auth/welcome',
                                   'X-Requested-With': 'XMLHttpRequest'})
            logger.debug(f"[connect] r_start.json(): {r_start.text} status: {r_start.status_code}")
            track_id = r_start.json()['track_id']
        except Exception as e:
            print(f'Exit script. Error at multi_step/start: {e}')
            sys.exit(1)
        else:
            pass

        time.sleep(2.5)
        # POST password; on success the session cookies are set
        r_password = self.session.post('https://passport.yandex.ru/registration-validations/auth/multi_step/commit_password',
                                {'csrf_token': csrf_token, 'track_id': track_id, 'password': ya_password,
                                'retpath': 'https://passport.yandex.ru/profile'},
                                headers={'User-Agent': my_user_agent, 'Referer': 'https://passport.yandex.ru/auth/welcome',
                                        'X-Requested-With': 'XMLHttpRequest'})

        if (r_password.json()['status'] == 'ok'):
            time.sleep(1)
            # Verify session by loading the profile page
            r_profile = self.session.get('https://passport.yandex.ru/profile', headers={'User-Agent': my_user_agent})
            logger.debug(f"[connect] r_profile: {r_profile.text}")
            pyquery_object = PyQuery(r_profile.text)
            logger.debug(f"[connect] pyquery_object: {pyquery_object}")
            first_name = pyquery_object('div.personal-info__first:first').text()
            last_name = pyquery_object('div.personal-info__last:first').text()
            logger.debug(f"[connect] Profile name: {first_name} {last_name}")
        else:
            print(f'Exit script. Error at multi_step/commit_password: {r_password.json()["status"]} {r_password.json()["errors"]}')
            sys.exit(1)

        # s = requests.Session()
        # resp = s.get("https://passport.yandex.ru/")
        # soup = BeautifulSoup(resp.text, "html.parser")
        # csrf = soup.find("input", {"name": "csrf_token"})["value"]
        # print(csrf)

        # link = "https://passport.yandex.com/auth"
        # data = {
        #     'login': '*',
        #     'passwd': '*',
        # }
        # self.session = Session()
        # response2 = self.session.post(url=link, headers=headers, data=data)
        # logger.debug(f"[connect] response2: {response2.text}")
        # response1 = requests.get(self.url, headers=headers, verify=self.verify_ssl)
        # logger.debug(f"[connect] response1: {response1.cookies}")
        # headers['cookie'] = '; '.join([x.name + '=' + x.value for x in response1.cookies])
        # headers['content-type'] = 'application/x-www-form-urlencoded'
        # payload = {
        #     'username': '*',
        #     'password': '*'
        # }
        # response2 = requests.post(self.url, data=payload, headers=headers, verify=self.verify_ssl)
        # headers['cookie'] = '; '.join([x.name + '=' + x.value for x in response2.cookies])
        # logger.debug(f"[connect] response2: {response2.text}")

    def create_page(self, title: str, name: str, data: str = None):
        logger.debug("[create_page] start")
        response = self.session.post(url=f"{self.url}/.gateway/root/wiki/createPage",
                                headers=headers,
                                data=self.get_data_create(title=title, name=name))
        logger.debug(f"[create_page] response: {response.text}")

    def update_page(self, title: str, page_id: int, data: str):
        logger.debug("[update_page] start")
        response = self.session.post(url=f"{self.url}/.gateway/root/wiki/updatePageDetails",
                                headers=headers,
                                data=self.get_data(page_id=page_id, data=data))
        logger.debug(f"[update_page] response: {response}")

    def open_page(self, url: str):
        response = self.session.get(url=f"{self.url}/{url}")
        logger.debug(f"[open_page] url: {self.url}/{url} response: {response.text}")

    def get_page_by_id(self, id: str):
        logger.debug("[get_page_by_id] start")

    def get_data_create(self, title: str, name: str):
        page_data = {
                "title": title,
                "pageType": "wysiwyg",
                "slug": f"homepage/reports/{name}",
                "parentSlug": "homepage/reports",
                "subscribeMe": True
                }
        return page_data

    def get_data_update(self, page_id: int, data: str):
        page_data = {
                "pageId": page_id,
                "content": data,
                # "revision": 61156223,
                "fields": [
                    "content",
                    "last_revision_id",
                    "attributes",
                    "revision_draft"
                ],
                "settings": {
                    "lang": "ru",
                    "theme": "light"
                }
                }
        return page_data

    def h1(self, content: str):
        return f"# {content}\\n\\n"

    def h2(self, content: str):
        return f"## {content}\\n\\n"

    def h3(self, content: str):
        return f"### {content}\\n\\n"

    def line(self):
        return f"&nbsp;\\n\\n"

    def h3(self, content: str):
        return f"### {content}\\n\\n"

    def h3(self, content: str):
        return f"### {content}\\n\\n"

    def h3(self, content: str):
        return f"### {content}\\n\\n"

    def h3(self, content: str):
        return f"### {content}\\n\\n"

    def h3(self, content: str):
        return f"### {content}\\n\\n"

    def code(self, content: str):
        return f"```\n{content}\n```\\n\\n"

    def iframe(self, link: str):
        return f'/iframe/(src=\"{link}\")\\n\\n'

class YandexRow:
    def __init__(self):
        self.columns: list[str] = []

    def add_column(self, content):
        return self.columns.append(content)

    def __str__(self):
        content = str()
        for column in self.columns:
            content += "|\\n\\n"
            content += column
            content += "\\n\\n"
        content += "||\\n|"
        return content


class YandexColumn:
    def __init__(self, name: str):
        self.name = name
        self.rows = []

    def add_row(self, content: str):
        self.rows.append(content)


class YandexTable:
    def __init__(self, name: str):
        logger.debug("[YandexTable] init")
        self.name = name
        self.data = []
        self.data.append(f"{name}\\n\\n")
        self.columns: list[YandexColumn] = []

    def add_row(self, row: YandexRow):
        self.data.append("|\\n|")
        self.data.append(str(row))

    def __str__(self):
        content = str()
        for item in self.data:
            content += item
        logger.debug(f"[YandexTable] content: {content}")
        return content


if __name__ == "__main__":
    yandex = YandexClient(url="https://wiki.yandex.ru")
    yandex.connect()
    # yandex.open_page(url=".gateway/root/wiki/getPageDetails")
    # page_data = yandex.get_data_create(title="testing", name="testing")
    # yandex.create_page(title="testing2", name="testing2")
    # table = YandexTable("Table")
    # row = YandexRow()
    # row.add_column("Column1 - Row1")
    # row.add_column("Column1 - Row2")
    # table.add_row(row)
    # row2 = YandexRow()
    # row2.add_column("Column2 - Row1")
    # row2.add_column("Column2 - Row2")
    # table.add_row(row2)
    # logger.debug(f"[YandexTable] table: {table}")
