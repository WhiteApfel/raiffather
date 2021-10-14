import asyncio
import base64
import json
import os
import re
import time
import traceback
from asyncio import Task
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address, IPv4Network
from random import choice, randint, randrange
from string import hexdigits
from typing import Optional
from uuid import uuid4

from async_property import async_property
from httpx import AsyncClient
from loguru import logger
from pullkin import AioPullkin
from pullkin.proto.notification import Notification
from randmac import RandMac
from tenacity import retry, retry_if_result, stop_after_attempt, retry_if_exception

from raiffather.exceptions.base import RaifUnauthorized
from raiffather.models.auth import OauthResponse, ResponseOwner
from raiffather.models.balance import Balance
from raiffather.models.device_info import DeviceInfo
from raiffather.models.products import Products

logger.disable("raiffather")


class RaiffatherBase:
    """
    Этот класс будет удобен для работы с апишкой. Не ешь меня. Я тебе пригожусь.
    """

    def __init__(self, username, password):
        self.__client: AsyncClient = None
        self.__username: str = username
        self.__password: str = password
        self.__access_token: str = None
        self.__device_info: str = None
        self.__fcm_sender_id: int = 581003993230  # Raiffeisen
        self.__otps: dict = {}
        self.me: Optional[ResponseOwner] = None
        self.products: Optional[Products] = None
        self.pullkin = AioPullkin()
        self.__receiving_push: Task = None

    async def __aenter__(self):
        if not self.products:
            self.products = await self.get_products()
        self.__receiving_push = asyncio.get_event_loop().create_task(
            self._push_server()
        )
        return self

    async def __aexit__(self, *args):
        await self.pullkin.close()
        await self.__client.aclose()
        self.__receiving_push.cancel()
        await self.__receiving_push

    async def _push_server(self):
        with open(".persistent_ids.txt", "a+") as f:
            received_persistent_ids = [x.strip() for x in f]

        @self.pullkin.on_notification()
        async def on_notification(obj, notification: Notification, data_message):
            idstr = data_message.persistent_id + "\n"
            with open(".persistent_ids.txt", "r") as f:
                if idstr in f:
                    return
            with open(".persistent_ids.txt", "a") as f:
                f.write(idstr)
            if "data" in notification.raw_data:
                server_message_id = notification["data"]["serverMessageId"] + "\n"
                with open(".persistent_ids.txt", "r") as f:
                    if server_message_id in f:
                        return
                with open(".persistent_ids.txt", "a") as f:
                    f.write(server_message_id)

                mfms_h = {"x-device-uid": self.device.uid}
                mfms_data = {
                    "securityToken": base64.b64encode(
                        json.dumps(self.security_token_data).encode()
                    ).decode(),
                    "sessionKey": notification["data"]["sessionKey"],
                    "syncToken": "null",
                }
                messages_response = await self._client.post(
                    f"https://pushserver.mfms.ru/raif/service/getMessages",
                    headers=mfms_h,
                    data=mfms_data,
                )
                if messages_response.status_code == 200:
                    messages = messages_response.json()
                    messages = messages["data"]["messageList"]
                else:
                    raise ValueError(
                        f"{messages_response.status_code} {messages_response.text}"
                    )
                for message in messages:
                    full_message = base64.b64decode(
                        message["fullMessage"].encode()
                    ).decode()
                    push_id = re.search("<rcasId>([0-9]{10})</rcasId>", full_message)[1]
                    otp = re.search("<otp>([0-9]{6})</otp>", full_message)[1]
                    self.__otps[push_id] = otp
                mfms_data = {
                    "securityToken": base64.b64encode(
                        json.dumps(self.security_token_data).encode()
                    ).decode(),
                    "messageIds": ";".join(
                        [message["messageId"] for message in messages]
                    ),
                }
                if messages:
                    verify_received_response = await self._client.post(
                        f"https://pushserver.mfms.ru/raif/service/messagesReceived",
                        headers=mfms_h,
                        data=mfms_data,
                    )
                    if verify_received_response.status_code == 200:
                        return
                    raise ValueError(f"Received {verify_received_response.status_code}")

        self.pullkin.credentials = self.device.fcm_cred
        self.pullkin.persistent_ids = received_persistent_ids
        try:
            push_listener = await self.pullkin.listen_coroutine()
        except asyncio.exceptions.CancelledError:
            return
        except ConnectionResetError:
            return
        try:
            while True:
                await push_listener.asend(None)
        except asyncio.exceptions.CancelledError:
            ...
        except ConnectionResetError:
            ...
        except Exception:
            print(traceback.format_exc())

    async def wait_code(self, push_id):
        x = 0
        while x < 60:
            logger.debug(f"Wait push #{push_id} i={x} in {self.__otps}")
            if push_id in self.__otps:
                return self.__otps.pop(push_id)
            x += 1
            await asyncio.sleep(2)
        raise KeyError(f"Код для #{push_id} не был получен в течение двух минут")

    @property
    def _client(self) -> AsyncClient:
        if not self.__client:
            self.__client = AsyncClient(timeout=10.0)
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
            "version": "5050059",
        }

    def preauth_bearer_token(self):
        return base64.b64encode(b"oauthUser:oauthPassword!@").decode()

    @async_property
    async def _access_token(self):
        if not self.__access_token or self.__access_token[1] < time.time():
            await self._auth()
        return self.__access_token[0]

    async def _auth(self):
        headers = {
            "Authorization": f"Basic {self.preauth_bearer_token()}",
            "User-Agent": "Raiffeisen 5.50.59 / Google Pixel Pfel (Android 11) / false",
            "RC-Device": "android",
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/oauth/token",
            json=self.oauth_token_data(),
            headers=headers,
        )
        if r.status_code == 200:
            parsed_r = OauthResponse(**r.json())
            self.me = parsed_r.resource_owner
            self.__access_token = (
                parsed_r.access_token,
                int(time.time()) + parsed_r.expires_in - 2,
            )
            return parsed_r
        else:
            raise ValueError(f"Status: {r.status_code}")

    @async_property
    async def authorized_headers(self):
        return {
            "Authorization": f"Bearer {await self._access_token}",
            "User-Agent": f"Raiffeisen {self.device.app_version} / {self.device.model} "
            f"({self.device.os} {self.device.os_version}) / false",
            "RC-Device": "android",
        }

    @property
    def device(self) -> DeviceInfo:
        if not self.__device_info:
            filename = f'{os.environ.get("HOME", ".")}/.raiffather_device_info.json'
            if not os.path.exists(filename):
                fcm_cred = self.pullkin.register(sender_id=self.__fcm_sender_id)
                network = IPv4Network(f"192.168.0.0/16")
                random_ip = IPv4Address(
                    randrange(
                        int(network.network_address) + 1,
                        int(network.broadcast_address) - 1,
                    )
                )
                data = {
                    "app_version": "5.50.59",
                    "router_ip": str(random_ip),
                    "router_mac": "02:00:00:00:00:00",
                    "ip": "fe80::cc10:57ff:fe41:f1a7",
                    "screen_y": choice(["1920", "2340", "2400"]),
                    "screen_x": "1080",
                    "os": "Android",
                    "name": "raiffather",
                    "serial_number": "".join(
                        [choice(hexdigits[:-6]) for _ in range(8)]
                    ),
                    "provider": "PH47RipsRD9WamEkODcrWVg2ckhmUDZqYH4+Cg",
                    "mac": str(RandMac()),
                    "os_version": "11",
                    "uid": "".join([choice(hexdigits[:-6]) for _ in range(40)]),
                    "model": "WhiteApfel Raiffather",
                    "push": fcm_cred["fcm"]["token"],
                    "user_security_hash": "".join(
                        [choice("1234567890ABCDEF") for _ in range(40)]
                    ),
                    "fingerprint": str(randint(1000000000, 9999999999)),
                    "uuid": uuid4().hex,
                    "fcm_cred": fcm_cred,
                }
                json.dump(data, open(filename, "w+"))
                self.__device_info = DeviceInfo(**data)
            else:
                self.__device_info = DeviceInfo(**json.load(open(filename, "r")))
        return self.__device_info

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
            "userSecurityHash": self.device.user_security_hash,
        }

    async def register_device(self) -> str:
        """
        Регистрация устройства для получения права на проведение операций

        Процесс регистрации подразумевает получение SMS-кода.
        Его нужно будет передать в функцию ``self.register_device_verify(request_id, code)`` в течение двух минут

        :return: request_id для последующего подтверждения кодом из SMS
        :rtype: ``str``
        """
        data = {
            "otp": {
                "deviceName": f"{self.device.model} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "deviceUid": self.device.uid,
                "fingerPrint": self.device.fingerprint,
                "pushId": self.device.push,
                "securityToken": base64.b64encode(
                    json.dumps(self.security_token_data).encode()
                ).decode(),
            }
        }
        register_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/push-address/push/control",
            json=data,
            headers=await self.authorized_headers,
        )
        if register_response.status_code == 200:
            request_id = register_response.json()["requestId"]
            send_sms_response = await self._client.post(
                f"https://amobile.raiffeisen.ru/rest/1/push-address/push/control/{request_id}/sms",
                headers=await self.authorized_headers,
                json="",
            )
            if send_sms_response.status_code == 201:
                return request_id
            raise ValueError(
                f"{send_sms_response.status_code} {send_sms_response.text}"
            )
        else:
            raise ValueError(
                f"{register_response.status_code} {register_response.text}"
            )

    async def register_device_verify(self, request_id: str, code: str):
        """
        Подтверждение регистрации устройства на право проведения операций

        :param request_id: идентификатор запросу, его можно получить через метод ``self.register_device()``
        :param code: код подтверждения из SMS
        :return: результат истинности регистрации
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/push-address/push/control/{request_id}/sms",
            headers=await self.authorized_headers,
            json={"code": str(code)},
        )
        if verify_response.status_code == 204:
            return True
        return False

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_exception(RaifUnauthorized),
    )
    async def balance(self) -> list[Balance]:
        """
        Общий баланс со всех счетов, рассчитанный по курсу ЦБ. В приложении отображается в самой верхней части.
        :return:
        """
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/balance",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            parsed_r = [Balance(**b) for b in r.json()]
            return parsed_r
        elif r.status_code == 401:
            await self._auth()
            raise RaifUnauthorized(r)
        else:
            raise ValueError(f"Status: {r.status_code}")

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_exception(RaifUnauthorized),
    )
    async def get_products(self) -> Products:
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/product/list",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            parsed_r = Products(**r.json())
            self.products = parsed_r
            return parsed_r
        elif r.status_code == 403:
            await self._auth()
            raise RaifUnauthorized()
        else:
            raise ValueError(f"Status: {r.status_code}")
