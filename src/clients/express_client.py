import asyncio
import httpx
from uuid import UUID
import uuid
import jwt  # pip install PyJWT
import time
import requests
import logging
import os
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger('root')
logging.basicConfig(
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG,
    force=True
)

class RequestType(Enum):
    POST = 1
    GET = 2


class ExpressCLient:

    def set_env(self, cts_host, bot_id, secret_key):
        self.CTS_HOST = cts_host
        self.BOT_ID = bot_id
        self.SECRET_KEY = secret_key

    def read_env(self):

        # os.environ['CHAT_ID']="101ea5e6-5f28-5a6e-9a0a-2b9bff98f32f"
        # os.environ['CTS_HOST']="notifications.example.com"
        # os.environ['BOT_ID']="a57d58b1-1feb-58a6-a83a-23d218626dab"
        # os.environ['SECRET_KEY']="4da8a98f0b9152621f82bad37b3fb277"

        # self.CHAT_ID = "101ea5e6-5f28-5a6e-9a0a-2b9bff98f32f"  # load_test
        # self.CHAT_ID = "<uuid>"
        # self.CTS_HOST = "notifications.example.com"
        # self.BOT_ID = "a57d58b1-1feb-58a6-a83a-23d218626dab"
        # self.SECRET_KEY = "4da8a98f0b9152621f82bad37b3fb277"

        # os.environ['UI_VERSION']="ui_version"
        # os.environ['CMS_VERSION']="cms_version"
        # os.environ['DB_VERSION']="db_version"
        # os.environ['JMX_PATH']="JMX_PATH"
        # os.environ['TEST_DESC']="TEST_DESC"
        # os.environ['REPORT_URL']="REPORT_URL"
        # os.environ['JMETER_URL']="JMETER_URL"
        # os.environ['TEST_STATUS']="Started"
        self.CHAT_ID = os.environ['CHAT_ID']
        self.CTS_HOST = os.environ['CTS_HOST']
        self.BOT_ID = os.environ['BOT_ID']
        self.SECRET_KEY = os.environ['SECRET_KEY']
        self.UI_VERSION = os.environ['UI_VERSION']
        self.CMS_VERSION = os.environ['CMS_VERSION']
        self.DB_VERSION = os.environ['DB_VERSION']
        self.JMX_PATH = os.environ['JMX_PATH']
        self.TEST_DESC = os.environ['TEST_DESC']
        self.REPORT_URL = os.environ['REPORT_URL']
        self.JMETER_URL = os.environ['JMETER_URL']
        self.TEST_STATUS = os.environ['TEST_STATUS']


    def get_jwt_payload(self):
        aud = getattr(self, "CTS_HOST", None) or os.environ.get("CTS_HOST") or "notifications.example.com"
        return {
            "aud": aud,
            "exp": int(time.time()) + 60,
            "iat": int(time.time()),
            "iss": self.BOT_ID,
            "jti": str(uuid.uuid4()),
            "nbf": int(time.time()),
            "version": 2
        }

    def report_test(self):
        text = f"""Test: {self.JMX_PATH}
Description: {self.TEST_DESC}
UI: {self.UI_VERSION}
CMS: {self.CMS_VERSION}
DB: {self.DB_VERSION}
Report: {self.REPORT_URL}
JMeter dashboard: {self.JMETER_URL}
Status: {self.TEST_STATUS}"""
        sync_id = self.send_message(chat_id=self.CHAT_ID, data=text)
        logger.debug(f"[report_test] sync_id: {sync_id}")
        return sync_id, text


    def build_message(self, chat_id, text):
        data = {
            "group_chat_id": chat_id,
            "notification": {
                "body": text},
            "opts": {}
        }
        return data

    def build_edit_message(self, chat_id, text):
        data = {
            "sync_id": chat_id,
            "payload": {
                "body": text},
            "opts": {}
        }
        return data

    def send_message(self, chat_id, data):
        uri = "api/v4/botx/notifications/direct"
        logger.debug(f"[send_message] uri: {uri}")
        return  self.request_api(uri=uri, request_type=RequestType.POST, data=self.build_message(chat_id=chat_id, text=data))

    def edit_message(self, chat_id, data):
        uri = "api/v3/botx/events/edit_event"
        logger.debug(f"[send_message] uri: {uri}")
        return  self.request_api(uri=uri, request_type=RequestType.POST, data=self.build_edit_message(chat_id=chat_id, text=data))

    def get_chat_info(self, chat_id):
        uri = f"api/v3/botx/chats/info?group_chat_id={chat_id}"
        logger.debug(f"[send_message] uri: {uri}")
        return  self.request_api(uri=uri, request_type=RequestType.GET)

    def get_event_status(self, chat_id):
        uri = f"api/v3/botx/events/{chat_id}/status"
        logger.debug(f"[send_message] uri: {uri}")
        return  self.request_api(uri=uri, request_type=RequestType.GET)

    def create_thread(self, sync_id):
        logger.debug(f"[send_message] sync_id: {sync_id}")
        data = {
            "sync_id": sync_id
        }
        uri = "api/v3/botx/chats/create_thread"
        return self.request_api(uri=uri, request_type=RequestType.POST, data=data)

    def request_api(self, uri, request_type: RequestType, data=None):
        url = f"https://{self.CTS_HOST}/{uri}"
        logger.debug(f"[request_api] url: {url}")
        payload = self.get_jwt_payload()
        logger.debug(f"[request_api] payload: {payload}")
        token = jwt.encode(payload, self.SECRET_KEY, algorithm="HS256")
        logger.debug(f"[request_api] token: {token}")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        sync_id = None
        resp = None
        if request_type == RequestType.POST:
            resp = requests.post(url, headers=headers, json=data, verify=False)
        elif request_type == RequestType.GET:
            resp = requests.get(url, headers=headers, verify=False)
        logger.debug(f"[request_api] status: {resp.status_code} text: {resp.json()}")
        if "sync_id" in resp.text and resp.status_code == 202:
            sync_id = resp.json()['result']['sync_id']
            logger.debug(f"[request_api] sync_id: {sync_id}")
        return sync_id


if __name__ == "__main__":
    logger.debug(f"[__name__] start")
    ec = ExpressCLient()
    sync_id,text = ec.report_test()
    # ec.edit_message(chat_id=sync_id, data=text.replace('Started','Passed'))
    # ec.get_event_status(chat_id=sync_id)
    # ec.create_thread(sync_id=sync_id)
    # ec.send_message(chat_id=sync_id, data="test")