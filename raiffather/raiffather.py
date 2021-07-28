import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from string import ascii_letters, hexdigits, digits
from ipaddress import IPv4Network, IPv4Address
from random import choice, randint, randrange
from threading import Thread
from typing import Union, Optional
from uuid import uuid4
import base64

import httpx
from fuzzywuzzy import process
from httpx import Client
from pullkin import register, listen
from randmac import RandMac
from tenacity import retry, stop_after_attempt, retry_if_result

from raiffather.models.auth import OauthResponse, ResponseOwner
from raiffather.models.balance import Balance
from raiffather.models.device_info import DeviceInfo
from raiffather.models.products import Products, Account
from raiffather.models.sbp import SbpBank, SbpPam, SbpInit


class Kill(Exception):
    pass


class KThread(Thread):
    def __init__(self, *args, **keywords):
        Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        """Start the thread."""
        self.__run_backup = self.run
        self.run = self.__run # Force the Thread to install our trace.
        Thread.start(self)

    def __run(self):
        """Hacked run function, which installs the
        trace."""
        sys.settrace(self.globaltrace)
        try:
            self.__run_backup()
        except Kill:
            pass
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise Kill()
        return self.localtrace

    def kill(self):
        self.killed = True


class Raiffather:
    """
    Этот класс будет удобен для работы с апишкой. Не ешь меня. Я тебе пригожусь.
    """

    def __init__(self, username, password, device_id: str = None):
        self.__client = None
        self.__username = username
        self.__password = password
        self.__access_token = None
        self.__device_info = None
        self.__fcm_sender_id = 581003993230
        self.__otps = {}
        self.__server: Optional[KThread] = None
        self.me: Optional[ResponseOwner] = None
        self.__products: Optional[Products] = None

    def __enter__(self):
        if not self.__products: self.__products = self.products()
        self.push_server()
        return self

    def __exit__(self, *args):
        self.__server.kill()

    def push_server(self):
        with open(".persistent_ids.txt", "a+") as f:
            received_persistent_ids = [x.strip() for x in f]

        def check_pushes():
            def on_notification(obj, notification, data_message):
                idstr = data_message.persistent_id + "\n"
                with open(".persistent_ids.txt", "r") as f:
                    if idstr in f:
                        return
                with open(".persistent_ids.txt", "a") as f:
                    f.write(idstr)
                if "data" in notification:
                    server_message_id = notification['data']['serverMessageId'] + "\n"
                    with open(".persistent_ids.txt", "r") as f:
                        if server_message_id in f:
                            return
                    with open(".persistent_ids.txt", "a") as f:
                        f.write(server_message_id)

                    mfms_h = {
                        "x-device-uid": self.device.uid
                    }
                    mfms_data = {
                        "securityToken": base64.b64encode(json.dumps(self.security_token_data).encode()).decode(),
                        "sessionKey": notification['data']['sessionKey'],
                        "syncToken": "null"
                    }
                    messages = []
                    r3 = self._client.post(f"https://pushserver.mfms.ru/raif/service/getMessages", headers=mfms_h,
                                           data=mfms_data)
                    if r3.status_code == 200:
                        messages = r3.json()
                        messages = messages['data']['messageList']
                    for message in messages:
                        full_message = base64.b64decode(message["fullMessage"].encode()).decode()
                        push_id = re.search('<rcasId>([0-9]{10})<\/rcasId>', full_message)[1]
                        otp = re.search('<otp>([0-9]{6})<\/otp>', full_message)[1]
                        self.__otps[push_id] = otp
                    mfms_data = {
                        "securityToken": base64.b64encode(json.dumps(self.security_token_data).encode()).decode(),
                        "messageIds": ";".join([message["messageId"] for message in messages])
                    }
                    if messages:
                        r4 = self._client.post(f"https://pushserver.mfms.ru/raif/service/messagesReceived", headers=mfms_h,
                                               data=mfms_data)
                        if r4.status_code == 200:
                            return
                        raise ValueError(f'Received{r4.status_code}')
            listen(self.device.fcm_cred, on_notification, received_persistent_ids, timer=1)
        self.__server = KThread(target=check_pushes)
        self.__server.start()

    def wait_code(self, push_id):
        x = 0
        while x < 60:
            if push_id in self.__otps:
                return self.__otps.pop(push_id)
            x += 1
            time.sleep(2)

    @property
    def _client(self) -> Client:
        if not self.__client:
            self.__client = Client()
        return self.__client

    @property
    def device_geo_timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def oauth_token_data(self) -> dict:
        return {
            "logon_type": "login_password",
            "device_geo_lat": "58.4736657",
            "device_geo_lon": "42.1861797",
            "device_geo_timestamp": self.device_geo_timestamp,
            "grant_type": "password",
            "device_install_id": self.device.uuid,
            "password": self.__password,
            "platform": "android",
            "username": self.__username,
            "version": "5050059"
        }

    def preauth_bearer_token(self):
        return base64.b64encode(b"oauthUser:oauthPassword!@").decode()

    @property
    def _access_token(self):
        if not self.__access_token or self.__access_token[1] < time.time():
            self._auth()
        return self.__access_token[0]

    def _auth(self):
        headers = {
            'Authorization': f'Basic {self.preauth_bearer_token()}',
            'User-Agent': 'Raiffeisen 5.50.59 / Google Pixel Pfel (Android 11) / false',
            'RC-Device': 'android'
        }
        r = self._client.post('https://amobile.raiffeisen.ru/oauth/token', json=self.oauth_token_data(),
                              headers=headers)
        if r.status_code == 200:
            parsed_r = OauthResponse(**r.json())
            self.me = parsed_r.resource_owner
            self.__access_token = (parsed_r.access_token, int(time.time()) + parsed_r.expires_in - 2)
            return parsed_r
        else:
            raise ValueError(f'Status: {r.status_code}')

    @retry(stop=stop_after_attempt(2), retry=retry_if_result(lambda x: str(x) == "Unauthorized"))
    def balance(self):
        """
        Общий баланс со всех счетов. рассчитанный по курсу ЦБ. В приложении отображается в самой верхней части.
        :return:
        """
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'User-Agent': 'Raiffeisen 5.50.59 / Google Pixel Pfel (Android 11) / false',
            'RC-Device': 'android'
        }
        r = self._client.get('https://amobile.raiffeisen.ru/rest/1/balance', headers=headers)
        if r.status_code == 200:
            parsed_r = [Balance(**b) for b in r.json()]
            return parsed_r
        elif r.status_code == 401:
            self._auth()
            raise ValueError("Unauthorized")
        else:
            raise ValueError(f'Status: {r.status_code}')

    @retry(stop=stop_after_attempt(2), retry=retry_if_result(lambda x: str(x) == "Unauthorized"))
    def products(self):
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'User-Agent': 'Raiffeisen 5.50.59 / Google Pixel Pfel (Android 11) / false',
            'RC-Device': 'android'
        }
        r = self._client.get('https://amobile.raiffeisen.ru/rest/1/product/list', headers=self.authorized_headers)
        if r.status_code == 200:
            parsed_r = Products(**r.json())
            return parsed_r
        elif r.status_code == 403:
            self._auth()
            raise ValueError("Unauthorized")
        else:
            raise ValueError(f'Status: {r.status_code}')

    @property
    def device(self) -> DeviceInfo:
        if not self.__device_info:
            filename = f'{os.environ.get("HOME", ".")}/.raiffather_device_info.json'
            if not os.path.exists(filename):
                fcm_cred = register(sender_id=self.__fcm_sender_id)
                network = IPv4Network(f"192.168.0.0/16")
                random_ip = IPv4Address(randrange(int(network.network_address) + 1, int(network.broadcast_address) - 1))
                data = {
                    "app_version": "5.50.59",
                    "router_ip": str(random_ip),
                    "router_mac": "02:00:00:00:00:00",
                    "ip": "fe80::cc10:57ff:fe41:f1a7",
                    "screen_y": choice(['1920', '2340', '2400']),
                    "screen_x": "1080",
                    "os": "Android",
                    "name": "raiffather",
                    "serial_number": "".join([choice(hexdigits[:-6]) for _ in range(8)]),
                    "provider": "PH47RipsRD9WamEkODcrWVg2ckhmUDZqYH4+Cg",
                    "mac": str(RandMac()),
                    "os_version": "11",
                    "uid": "".join([choice(hexdigits[:-6]) for _ in range(40)]),
                    "model": "WhiteApfel Raiffather",
                    "push": fcm_cred['fcm']['token'],
                    "user_security_hash": "".join([choice('1234567890ABCDEF') for _ in range(40)]),
                    "fingerprint": str(randint(1000000000, 9999999999)),
                    "uuid": uuid4().hex,
                    "fcm_cred": fcm_cred
                }
                json.dump(data, open(filename, 'w+'))
                self.__device_info = DeviceInfo(**data)
            else:
                self.__device_info = DeviceInfo(**json.load(open(filename, "r")))
        return self.__device_info

    @property
    def authorized_headers(self):
        return {
            'Authorization': f'Bearer {self._access_token}',
            'User-Agent': f'Raiffeisen {self.device.app_version} / {self.device.model} ({self.device.os} {self.device.os_version}) / false',
            'RC-Device': 'android'
        }

    @property
    def security_token_data(self):
        dt_now = datetime.now(tz=timezone(timedelta(hours=3))).astimezone()

        return {
            "appPackage": "ru.raiffeisen.rmobile_fcm",
            "appVersion": self.device.app_version.replace(".", "0"),
            "routerIpAddress": self.device.router_ip,
            "localErrorLog": "BAD_PARAMETERS",
            "routerMacAddress": self.device.router_mac,
            "ipAddress": self.device.ip,
            "screenResolutionY": self.device.screen_y,
            "screenResolutionX": self.device.screen_x,
            "osName": self.device.os,
            "locale": "ru_RU",
            "version": "1.0-121-2020-11-16-11-33-release-b121",
            "deviceName": self.device.name,
            "deviceSerialNumber": self.device.serial_number,
            "providerUid": self.device.provider,
            "macAddress": self.device.mac,
            "generationTime": dt_now.strftime("%Y.%m.%d %H:%M:%S") + " 0300",
            "osVersion": self.device.os_version,
            "deviceUid": self.device.uid,
            "deviceModel": self.device.model,
            "pushAddress": self.device.push,
            "userSecurityHash": self.device.user_security_hash
        }

    def register_device(self):
        data = {
            "otp": {
                "deviceName": f"{self.device.model} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "deviceUid": self.device.uid,
                "fingerPrint": self.device.fingerprint,
                "pushId": self.device.push,
                "securityToken": base64.b64encode(json.dumps(self.security_token_data).encode()).decode()
            }
        }
        r = self._client.post("https://amobile.raiffeisen.ru/rest/1/push-address/push/control", json=data,
                              headers=self.authorized_headers)
        if r.status_code == 200:
            request_id = r.json()["requestId"]
            r2 = self._client.post(f"https://amobile.raiffeisen.ru/rest/1/push-address/push/control/{request_id}/sms",
                                   headers=self.authorized_headers, json="")
            if r2.status_code == 201:
                return request_id
        return r

    def register_device_verify(self, request_id: str, code: str):
        r = self._client.put(f"https://amobile.raiffeisen.ru/rest/1/push-address/push/control/{request_id}/sms",
                             headers=self.authorized_headers, json={"code": code})
        if r.status_code == 204:
            return True
        return False

    def c2c(self, amount: Union[float, int]):
        """
        Надо деить. Мне лень. Там муторно со счетами. Лучше сначала СБП замучулькаю
        :param amount:
        :return:
        """
        data = {
            "amount": {
                "currency": 643,
                "sum": 50.0
            },
            "commission": {
                "currency": 810,
                "sum": 50.0
            },
            "dst": {
                "pan": "5321304044087960",
                "type": "pan"
            },
            "salary": False,
            "src": {
                "cardId": 83159519,
                "type": "cardId"
            }
        }
        r = self._client.post("https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer", headers=self.authorized_headers, json=data)
        if r.status_code == 200:
            rjson = r.json()
            request_id = rjson['requestId']
            data2 = {
                "deviceUid": self.device.uid,
                "pushId": self.device.push
            }
            r2 = self._client.post(f"https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer/{request_id}/PUSHOTP", json=data2, headers=self.authorized_headers)
            if r2.status_code == 200:
                push_id = r2.json()['pushId']
                otp = self.wait_code(push_id)
                print(otp)

    def sbp_settings(self):
        return self._client.get("https://amobile.raiffeisen.ru/rest/1/sbp/settings", headers=self.authorized_headers).json()

    def sbp_banks(self, phone, cba: str = None):
        if not self.__products:
            self.__products = self.products()
        data = {
            "phone": phone,
            "srcCba": cba or self.sbp_settings()['cba']
        }
        r = self._client.post("https://amobile.raiffeisen.ru/rest/1/transfer/contact/bank", headers=self.authorized_headers, json=data)
        if r.status_code == 200:
            return [SbpBank(**bank) for bank in r.json()]

    def sbp_pam(self, bank: str, phone: str, cba: str = None):
        data = {
            "bankId": bank,
            "phone": phone,
            "srcCba": cba or self.sbp_settings()['cba']
        }
        r = self._client.post("https://amobile.raiffeisen.ru/rest/1/transfer/contact/pam",
                              headers=self.authorized_headers, json=data)
        # TODO добавить проверку на неналичие счёта в банке
        if r.status_code == 200:
            return SbpPam(**r.json())

    def sbp_commission(self, bank, phone, amount, cba: str = None):
        data = {
            "amount": float(amount),
            "bankId": bank,
            "phone": phone,
            "srcCba": cba or self.sbp_settings()['cba']
        }
        r = self._client.post("https://amobile.raiffeisen.ru/rest/1/transfer/contact/commission",
                              headers=self.authorized_headers, json=data)
        if r.status_code == 200:
            return r.json()

    def sbp_init(self, amount, bank, phone, message, cba: str = None):
        data = {
            "amount": float(amount),
            "bankId": bank,
            # "commission": 0.0,
            # "currency": "810",
            "message": message or '',
            "phone": phone,
            "recipient": "",
            "srcAccountId": self.__products.accounts[0].id,
            "srcCba": cba or  self.sbp_settings()['cba'],
            "template": False
        }
        # r = self._client.get("https://amobile.raiffeisen.ru/rest/1/transfer/contact", headers=self.authorized_headers)
        r = self._client.post("https://amobile.raiffeisen.ru/rest/1/transfer/contact",
                              headers=self.authorized_headers, json=data)
        if r.status_code == 200:
            return SbpInit(**r.json())

    def sbp_prepare(self):
        r = self._client.get("https://amobile.raiffeisen.ru/rest/1/transfer/contact", headers=self.authorized_headers)
        if r.status_code == 200:
            return True

    def sbp_accounts(self):
        r = self._client.get("https://amobile.raiffeisen.ru/rest/1/transfer/contact/account?alien=false", headers=self.authorized_headers)
        if r.status_code == 200:
            return [Account(a) for a in r.json()]

    def sbp_bank_fuzzy_search(self, banks: list, bank: str):
        return process.extractOne(bank, banks)[0]

    def sbp_send_push(self, request_id):
        data = {
            "deviceUid": self.device.uid,
            "pushId": self.device.push
        }

        r = self._client.post(f"https://amobile.raiffeisen.ru/rest/1/transfer/contact/{request_id}/push", json=data,
                               headers=self.authorized_headers)
        if r.status_code == 201:
            push_id = r.json()['pushId']
            otp = self.wait_code(push_id)
            return otp

    def sbp_push_verify(self, request_id, code):
        r = self._client.put(f"https://amobile.raiffeisen.ru/rest/1/transfer/contact/{request_id}/push",
                             headers=self.authorized_headers, json={"code": code})
        if r.status_code == 204:
            return True
        return False

    def sbp(self, phone, bank, amount, comment=None):
        cba = self.sbp_settings()['cba']
        self.sbp_prepare()
        banks = self.sbp_banks(phone=phone, cba=cba)
        bank_name = self.sbp_bank_fuzzy_search([b.name for b in banks], bank)
        bank = next((bank for bank in banks if bank.name == bank_name), None)
        if bank:
            pam = self.sbp_pam(bank=bank.id, phone=phone, cba=cba)
            com = float(self.sbp_commission(bank=bank.id, phone=phone, amount=float(amount), cba=cba)['commission'])
            init = self.sbp_init(float(amount), bank.id, phone, comment, cba)
            code = self.sbp_send_push(init.request_id)
            success = self.sbp_push_verify(init.request_id, code)
            return success





