import asyncio
import base64
import json
import os
import re
import time
from asyncio import Task
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from random import choice, randint, randrange
from ssl import SSLError
from string import hexdigits
from typing import Optional
from uuid import uuid4

from appdirs import AppDirs
from async_property import async_property
from httpx import AsyncClient
from loguru import logger
from pullkin import AioPullkin
from pullkin.models import AppCredentials
from pullkin.models.message import Message
from randmac import RandMac

from raiffather.exceptions.base import RaifErrorResponse, RaifInvalidLoginPassword
from raiffather.models.auth import (
    OauthFreshTokensResponse,
    OauthMfaResponse,
    ResponseOwner,
)
from raiffather.models.balance import Balance
from raiffather.models.device_info import DeviceInfo
from raiffather.models.products import Products

logger.disable("raiffather")


class RaiffatherBase:
    """
    Этот класс будет удобен для работы с апишкой. Не ешь меня. Я тебе пригожусь.
    """

    def __init__(self, username, password, app_name="default"):
        self.__client: AsyncClient = None
        self.__username: str = username
        self.__password: str = password
        self.__app_dirs = AppDirs("raiffather", "whiteapfel")
        self.__app_name = app_name
        self.__access_token: str = None
        self.__device_info: str = None
        self.__fcm_sender_id: int = 581003993230  # Raiffeisen
        self.__otps: dict = {}
        self.me: Optional[ResponseOwner] = None
        self.products: Optional[Products] = None
        self.pullkin = AioPullkin()
        self.__receiving_push: Task = None

    async def __aenter__(self):
        failed = True
        try:
            # if not self.produ   await self.get_products()
            self.__receiving_push = asyncio.get_event_loop().create_task(
                self._push_server()
            )
            failed = False
            return self
        finally:
            if failed:
                await self.__aexit__()

    async def __aexit__(self, *args):
        try:
            await self.pullkin.close()
        except ValueError as e:  # httpcore ValueError: list.remove(x): x not in list
            logger.opt(exception=e).error("ValueError: ")
        except RuntimeError as e:
            if "The connection pool was closed while" not in str(e):
                logger.opt(exception=e).error("RuntimeError: ")
        await self.__client.aclose()
        if self.__receiving_push:
            self.__receiving_push.cancel()
            await self.__receiving_push

    async def _push_server(self):
        filedir = f"{self.__app_dirs.user_data_dir}/{self.__app_name}"
        persistent_path = f"{filedir}/persistent_ids.txt"
        Path(filedir).mkdir(parents=True, exist_ok=True)

        with open(persistent_path, "a+") as f:
            received_persistent_ids = [x.strip() for x in f]

        @self.pullkin.on_notification()
        async def on_notification(
            obj, notification: Message, data_message  # skipcq: PYL-W0613
        ):
            idstr = data_message.persistent_id + "\n"
            with open(persistent_path, "r") as f:
                if idstr in f:
                    return
            with open(persistent_path, "a") as f:
                f.write(idstr)
            if "data" in notification.raw_data:
                server_message_id = notification["data"]["serverMessageId"] + "\n"
                with open(persistent_path, "r") as f:
                    if server_message_id in f:
                        return
                with open(persistent_path, "a") as f:
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
                    "https://pushserver.mfms.ru/raif/service/getMessages",
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
                        "https://pushserver.mfms.ru/raif/service/messagesReceived",
                        headers=mfms_h,
                        data=mfms_data,
                    )
                    if verify_received_response.status_code == 200:
                        return
                    raise RaifErrorResponse(verify_received_response)

        self.pullkin.credentials = AppCredentials(**self.device.fcm_cred)
        self.pullkin.persistent_ids = received_persistent_ids
        try:
            push_listener = await self.pullkin.listen_coroutine()
            while True:
                await push_listener.asend(None)
        except asyncio.exceptions.CancelledError:
            return
        except ConnectionResetError:
            return
        except SSLError as e:
            if "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" in str(e):
                return
            raise

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

    def refresh_token_data(self) -> dict:
        return {
            "logon_type": "pin",
            "refresh_token": self.device.refresh_token,
            "grant_type": "refresh_token",
            "device_install_id": self.device.uuid,
            "platform": "android",
            "version": self.device.app_version.replace(".", "0"),
        }

    def preauth_token(self):
        return base64.b64encode(
            b"android-p-usr:PsHI5X5AKDESv4bykUp3eqOOvzALV}9C"
        ).decode()

    def _update_refresh_token(self, refresh_token: str):
        self.device.refresh_token = refresh_token
        filedir = f"{self.__app_dirs.user_data_dir}/{self.__app_name}"
        filename = f"{filedir}/raiffather_device_info.json"
        with open(filename, "w+") as f:
            f.write(self.device.json())

    @async_property
    async def _access_token(self):
        if (
            not self.__access_token or self.__access_token[1] < time.time()
        ) and self.device.refresh_token is not None:
            await self._refresh_tokens()
        elif self.device.refresh_token is None:
            raise ValueError("You should log in to raiffeisen with MFA")
        return self.__access_token[0]

    async def _mfa_send_code(self, mfa_token: str) -> bool:
        headers = {
            "Authorization": f"Basic {self.preauth_token()}",
            "User-Agent": "Raiffeisen 5.50.59 / Google Pixel Pfel (Android 11) / false",
            "RC-Device": "android",
            "X-Device-Id": self.device.uuid,
        }
        data = {
            "mfa_token": mfa_token,
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/id/oauth/mfa/otp/send",
            json=data,
            headers=headers,
        )
        return r.status_code == 200

    async def mfa_send_code(self) -> OauthMfaResponse:
        headers = {
            "Authorization": f"Basic {self.preauth_token()}",
            "User-Agent": (
                f"Raiffeisen {self.device.app_version} / {self.device.name} / false"
            ),
            "RC-Device": "android",
        }
        # TODO: Add phone auth (without username)
        data = {
            "logon_type": "login_password",
            "username": self.__username,
            "grant_type": "password",
            "device_install_id": self.device.uuid,
            "platform": "android",
            "version": self.device.app_version.replace(".", "0"),
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/id/oauth/id/token",
            json=data,
            headers=headers,
        )
        if r.status_code == 200:
            parsed_username_response = OauthMfaResponse(**r.json())
            # TODO: сделать проверку на случай, если это не mfa токен
            await self._mfa_send_code(parsed_username_response.access_token)
            return parsed_username_response
        raise RaifErrorResponse(r)

    async def mfa_verify_code(self, mfa_token: str, code: str) -> OauthMfaResponse:
        headers = {
            "Authorization": f"Basic {self.preauth_token()}",
            "User-Agent": (
                f"Raiffeisen {self.device.app_version} / {self.device.name} / false"
            ),
            "RC-Device": "android",
        }
        data = {
            "code": code,
            "mfa_token": mfa_token,
            "grant_type": "mfa-otp",
            "device_install_id": self.device.uuid,
            "platform": "android",
            "version": self.device.app_version.replace(".", "0"),
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/id/oauth/id/token",
            json=data,
            headers=headers,
        )
        if r.status_code == 200:
            parsed_username_response = OauthMfaResponse(**r.json())
            # TODO: сделать проверку на случай, если это не mrfa токен
            return parsed_username_response
        raise RaifErrorResponse(r)
        # {
        #     "error": "wrong_otp",
        #     "error_description": "Wrong OTP code.",
        # }

    async def mfa_password(self, mfa_token: str) -> OauthFreshTokensResponse:
        headers = {
            "Authorization": f"Basic {self.preauth_token()}",
            "User-Agent": (
                f"Raiffeisen {self.device.app_version} / {self.device.name} / false"
            ),
            "RC-Device": "android",
        }
        data = {
            "password": self.__password,
            "mfa_token": mfa_token,
            "grant_type": "mfa-otp",
            "device_install_id": self.device.uuid,
            "platform": "android",
            "version": self.device.app_version.replace(".", "0"),
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/id/oauth/id/token",
            json=data,
            headers=headers,
        )
        if r.status_code == 200:
            tokens_response = OauthFreshTokensResponse(**r.json())
            self.me = tokens_response.resource_owner
            # TODO: сделать проверку на случай, если это не mfa токен
            self._update_refresh_token(tokens_response.refresh_token)
            return tokens_response
        elif r.is_client_error:
            if r.json().get("error") == "invalid_grant":
                raise RaifInvalidLoginPassword(r)
        raise RaifErrorResponse(r)

    async def _refresh_tokens(self) -> OauthFreshTokensResponse:
        headers = {
            "Authorization": f"Basic {self.preauth_token()}",
            "User-Agent": (
                f"Raiffeisen {self.device.app_version} / {self.device.name} / false"
            ),
            "RC-Device": "android",
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/id/oauth/id/token",
            json=self.refresh_token_data(),
            headers=headers,
        )
        if r.status_code == 200:
            refresh_response = OauthFreshTokensResponse(**r.json())
            self.me = refresh_response.resource_owner
            self.__access_token = (
                refresh_response.access_token,
                int(time.time()) + refresh_response.expires_in - 2,
            )
            self._update_refresh_token(refresh_response.refresh_token)
            return refresh_response
        raise RaifErrorResponse(r)

    @async_property
    async def authorized_headers(self):
        return {
            "Authorization": f"Bearer {await self._access_token}",
            "User-Agent": (
                f"Raiffeisen {self.device.app_version} / {self.device.model} "
                f"({self.device.os} {self.device.os_version}) / false"
            ),
            "RC-Device": "android",
            "X-Device-Id": self.device.uuid,
        }

    @property
    def device(self) -> DeviceInfo:
        if not self.__device_info:
            filedir = f"{self.__app_dirs.user_data_dir}/{self.__app_name}"
            filename = f"{filedir}/raiffather_device_info.json"
            Path(filedir).mkdir(parents=True, exist_ok=True)
            if not os.path.exists(filename):
                fcm_cred = self.pullkin.register(sender_id=self.__fcm_sender_id)
                network = IPv4Network("192.168.0.0/16")
                random_ip = IPv4Address(
                    randrange(
                        int(network.network_address) + 1,
                        int(network.broadcast_address) - 1,
                    )
                )
                data = {
                    "app_version": "5.93.07",
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
                    "push": fcm_cred.fcm.token,
                    "user_security_hash": "".join(
                        [choice("1234567890ABCDEF") for _ in range(40)]
                    ),
                    "fingerprint": str(randint(1000000000, 9999999999)),
                    "uuid": str(uuid4()),
                    "fcm_cred": fcm_cred.dict(),
                    "refresh_token": None,
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
        Его нужно будет передать в функцию
        ``self.register_device_verify(request_id, code)`` в течение двух минут

        :return: request_id для последующего подтверждения кодом из SMS
        :rtype: ``str``
        """
        data = {
            "otp": {
                "deviceName": (
                    f"{self.device.model} {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                ),
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
                "https://amobile.raiffeisen.ru"
                f"/rest/1/push-address/push/control/{request_id}/sms",
                headers=await self.authorized_headers,
                json="",
            )
            if send_sms_response.status_code == 201:
                return request_id
            raise RaifErrorResponse(send_sms_response)
        raise RaifErrorResponse(register_response)

    async def register_device_verify(self, request_id: str, code: str):
        """
        Подтверждение регистрации устройства на право проведения операций

        :param request_id: идентификатор запросу, его можно получить через метод
        ``self.register_device()``
        :param code: код подтверждения из SMS
        :return: результат истинности регистрации
        """
        verify_response = await self._client.put(
            "https://amobile.raiffeisen.ru"
            f"/rest/1/push-address/push/control/{request_id}/sms",
            headers=await self.authorized_headers,
            json={"code": str(code)},
        )
        if verify_response.status_code == 204:
            return True
        raise RaifErrorResponse(verify_response)

    async def balance(self) -> list[Balance]:
        """
        Общий баланс со всех счетов, рассчитанный по курсу ЦБ. В приложении отображается
        в самой верхней части.

        :return:
        """
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/balance",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            parsed_r = [Balance(**b) for b in r.json()]
            return parsed_r
        raise RaifErrorResponse(r)

    async def get_products(self) -> Products:
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/product/list",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            parsed_r = Products(**r.json())
            self.products = parsed_r
            return self.products
        raise RaifErrorResponse(r)
