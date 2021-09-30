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
from typing import Optional, Union, AsyncGenerator, List
from uuid import uuid4

import asyncio

from async_property import async_property
from fuzzywuzzy import process
from httpx import AsyncClient
from loguru import logger
from pullkin import AioPullkin
from pullkin.proto.notification import Notification
from randmac import RandMac
from tenacity import retry, retry_if_result, stop_after_attempt

from raiffather.exceptions.sbp import SBPRecipientNotFound
from raiffather.models.auth import OauthResponse, ResponseOwner
from raiffather.models.balance import Balance
from raiffather.models.c2c import C2cInit, E3DSOTPData, C2cRetrieve
from raiffather.models.device_info import DeviceInfo
from raiffather.models.products import Account, Products
from raiffather.models.sbp import SbpBank, SbpInit, SbpPam, SbpSettings, SbpCommission
from raiffather.models.transactions import Transactions, Transaction

logger.disable("raiffather")


class Raiffather:
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
        self.__products: Optional[Products] = None
        self.pullkin = AioPullkin()
        self.__receiving_push: Task = None

    async def __aenter__(self):
        if not self.__products:
            self.__products = await self.products()
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

        try:
            while True:
                await push_listener.asend(None)
        except asyncio.exceptions.CancelledError:
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
        retry=retry_if_result(lambda x: str(x) == "Unauthorized"),
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
            raise ValueError("Unauthorized")
        else:
            raise ValueError(f"Status: {r.status_code}")

    @retry(
        stop=stop_after_attempt(2),
        retry=retry_if_result(lambda x: str(x) == "Unauthorized"),
    )
    async def products(self) -> Products:
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/product/list",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            parsed_r = Products(**r.json())
            return parsed_r
        elif r.status_code == 403:
            await self._auth()
            raise ValueError("Unauthorized")
        else:
            raise ValueError(f"Status: {r.status_code}")

    async def c2c_prepare(self):
        """
        Подготавливает к проведению перевода по номеру карты, обязательный пунктик
        :return: bool
        """
        r = await self._client.get(
            "https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return True
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_retrieve(self):
        """
        Подготавливает к проведению перевода по номеру карты, обязательный пунктик
        :return: bool
        """
        r = await self._client.get(
            "https://e-commerce.raiffeisen.ru/c2c/v2.0/retrieveInitialData",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return C2cRetrieve(**r.json())
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_fees(self, amount, dst=83159519, src="4111111111111111"):
        """
        Рассчитывает комиссию со стороны Райфа для перевода.
        Другие банки могут взять комиссию за стягивание или пополнение
        :return: bool
        """
        r = await self._client.post(
            "https://e-commerce.raiffeisen.ru/ws/link/c2c/v1.0/fees",
            headers=await self.authorized_headers,
            json={
                "amount": 1.0,
                "dst": {"serno": dst},
                "feeCurrency": 643,
                "src": {"pan": src},
                "transferCurrency": 643,
            },
        )
        if r.status_code == 200:
            return r.json()
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_init(self, amount):
        """
        Инициализирует намерение перевода. Возвращает какие-то данные
        Нужная штука, если хотите сделать перевод, без неё вообще нельзя, гы
        :return: bool
        """
        r = await self._client.post(
            "https://e-commerce.raiffeisen.ru/ws/link/c2c/v1.0/fees",
            headers=await self.authorized_headers,
            json={
                "amount": {"currency": 643, "sum": amount},
                "dst": {"cardId": 83159519, "type": "cardId"},
                "commission": {"currency": 810, "sum": 0.0},
                "src": {"tcpId": 233841, "type": "tcpId"},
                "salary": False,
            },
        )
        if r.status_code == 200:
            return C2cInit(**r.json())
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_e3dsotp(self, request_id):
        """
        Получение данных для перенаправления на 3DS

        :param request_id: номер заявки на перевод, получается в self.c2c_init()
        :return:
        """
        e3dsotp_response = await self._client.post(
            f"https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer/{request_id}/E3DSOTP",
            json="",
            headers=await self.authorized_headers,
        )
        if e3dsotp_response.status_code == 200:
            return E3DSOTPData(**e3dsotp_response.json())
        else:
            raise ValueError(f"{e3dsotp_response.status_code} {e3dsotp_response.text}")

    async def c2c_e3ds_pareq(self, pareq):
        data = {
            "MD": "",
            "TermUrl": "https://imobile.raiffeisen.ru/3ds/1400474370",
            "PaReq": pareq,
        }
        r = await self._client.post(
            "https://ds.mirconnect.ru/vbv2/pareq",
            headers=await self.authorized_headers,
            data=data,
        )
        if r.status_code == 200:
            return r.text
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c(self, amount: Union[float, int]):
        """
        Общий метод для полноценного проведения операции по всем этапам

        Надо деить. Мне лень. Там муторно со счетами. Лучше сначала СБП замучулькаю
        :param amount:
        :return:
        """
        data = {
            "amount": {"currency": 643, "sum": 50.0},
            "commission": {"currency": 810, "sum": 50.0},
            "dst": {"pan": "5321304044087960", "type": "pan"},
            "salary": False,
            "src": {"cardId": 83159519, "type": "cardId"},
        }
        r = await self._client.post(
            "https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            rjson = r.json()
            request_id = rjson["requestId"]
            data2 = {"deviceUid": self.device.uid, "pushId": self.device.push}
            r2 = await self._client.post(
                f"https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer/{request_id}/PUSHOTP",
                json=data2,
                headers=await self.authorized_headers,
            )
            if r2.status_code == 200:
                push_id = r2.json()["pushId"]
                otp = self.wait_code(push_id)
                print(otp)

    # СБП

    async def sbp_settings(self) -> SbpSettings:
        """
        Получение настроек про СБП

        Важным полем является номер аккаунта в ЦБ: SbpSettings.cba

        :return: Информация о настройках СБП
        :rtype: SbpSettings
        """
        settings_reponse = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/sbp/settings",
            headers=await self.authorized_headers,
        )
        if settings_reponse.status_code == 200:
            return SbpSettings(**settings_reponse.json())
        else:
            raise ValueError(f"{settings_reponse.status_code} {settings_reponse.text}")

    async def sbp_banks(self, phone, cba: str = None):
        if not self.__products:
            self.__products = await self.products()
        data = {"phone": phone, "srcCba": cba or (await self.sbp_settings()).cba}
        sbp_banks_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/bank",
            headers=await self.authorized_headers,
            json=data,
        )
        if sbp_banks_response.status_code == 200:
            return [SbpBank(**bank) for bank in sbp_banks_response.json()]
        else:
            raise ValueError(
                f"{sbp_banks_response.status_code} {sbp_banks_response.text}"
            )

    async def sbp_pam(self, bank_id: str, phone: str, cba: str = None) -> SbpPam:
        """
        Не знаю, зачем это надо, но это обязательный этап проведения перевода по СБП

        :param bank_id: id банка получателя, можно узнать в self.sbp_banks()
        :param phone: номер телефона получателя
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpPam
        """
        data = {
            "bankId": bank_id,
            "phone": phone,
            "srcCba": cba or (await self.sbp_settings()).cba,
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/pam",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            return SbpPam(**r.json())
        elif r.status_code == 417:
            raise SBPRecipientNotFound(r.json()["_form"][0])
        else:
            raise ValueError(f"{r.status_code}: {r.text}")

    async def sbp_commission(
        self, bank, phone, amount, cba: str = None
    ) -> SbpCommission:
        """
        Расчёт комиссии для перевода по СБП

        :param bank: id банка получателя, можно узнать в self.sbp_banks()
        :param phone: номер телефона получателя
        :param amount: сумма перевода в рублях
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpCommission
        """
        data = {
            "amount": float(amount),
            "bankId": bank,
            "phone": phone,
            "srcCba": cba or (await self.sbp_settings()).cba,
        }
        comission_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/commission",
            headers=await self.authorized_headers,
            json=data,
        )
        if comission_response.status_code == 200:
            return SbpCommission(**comission_response.json())
        else:
            raise ValueError(
                f"{comission_response.status_code} {comission_response.text}"
            )

    async def sbp_init(
        self, amount, bank, phone, message=None, cba: str = None
    ) -> SbpInit:
        """
        Ещё один этап для проведения перевода по СБП

        :param amount: сумма перевода в рублях
        :param bank: id банка получателя, можно узнать в self.sbp_banks()
        :param phone: номер телефона получателя
        :param message: комментарий к перевод
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpInit
        """
        data = {
            "amount": float(amount),
            "bankId": bank,
            # "commission": 0.0,
            # "currency": "810",
            "message": message or "",
            "phone": phone,
            "recipient": "",
            "srcAccountId": self.__products.accounts[0].id,
            "srcCba": cba or (await self.sbp_settings()).cba,
            "template": False,
        }
        init_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact",
            headers=await self.authorized_headers,
            json=data,
        )
        if init_response.status_code == 200:
            return SbpInit(**init_response.json())
        else:
            raise ValueError(f"{init_response.status_code} {init_response.text}")

    async def sbp_prepare(self) -> bool:
        """
        Подготавливает к проведению перевода по СБП, обязательный пунктик
        :return: bool
        """
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return True
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def sbp_accounts(self) -> List[Account]:
        """
        Доступные счета для отправки денег
        :return: list[Account]
        """
        accounts_response = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/account?alien=false",
            headers=await self.authorized_headers,
        )
        if accounts_response.status_code == 200:
            return [Account(**a) for a in accounts_response.json()]
        else:
            raise ValueError(
                f"{accounts_response.status_code} {accounts_response.text}"
            )

    def sbp_bank_fuzzy_search(self, banks: list, bank: str):
        """
        Возвращает название банка из списка, название которого наиболее совпадает с искомым

        :param banks: лист названий банков
        :param bank: искомое название
        :return:
        """
        return process.extractOne(bank, banks)[0]

    async def sbp_send_push(self, request_id) -> str:
        """
        Отправляет пуш-уведомление для подтверждение и ждёт, когда пуш-сервер его получит

        :param request_id: номер заявки
        :return: код подтверждения
        """
        data = {"deviceUid": self.device.uid, "pushId": self.device.push}

        send_code_response = await self._client.post(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/contact/{request_id}/push",
            json=data,
            headers=await self.authorized_headers,
        )
        if send_code_response.status_code == 201:
            push_id = send_code_response.json()["pushId"]
            print("awaiting code")
            otp = await self.wait_code(push_id)
            print("code is", otp)
            return otp
        else:
            raise ValueError(
                f"{send_code_response.status_code} {send_code_response.text}"
            )

    async def sbp_push_verify(self, request_id, code) -> bool:
        """
        Проверяет код подтверждения

        :param request_id: номер заявки
        :param code: код подтверждения
        :return: успешно ли
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/contact/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": code},
        )
        if verify_response.status_code == 204:
            return True
        return False

    async def sbp(self, phone, bank, amount, comment=None):
        """
        Единый метод для автоматического проведения всего перевода

        :param phone: номер телефона получателя
        :param bank: название банка получателя, можно в произвольной форме, типа "Тинька" или "Райф"
        :param amount: сумма перевода в рублях
        :param comment: комментарий к переводу
        :return: успешно ли
        """
        cba = (await self.sbp_settings()).cba
        await self.sbp_prepare()
        banks = await self.sbp_banks(phone=phone, cba=cba)
        bank_name = self.sbp_bank_fuzzy_search([b.name for b in banks], bank)
        bank = next((bank for bank in banks if bank.name == bank_name), None)
        if bank:
            pam = await self.sbp_pam(bank_id=bank.id, phone=phone, cba=cba)
            com = float(
                (
                    await self.sbp_commission(
                        bank=bank.id, phone=phone, amount=float(amount), cba=cba
                    )
                ).commission
            )
            init = await self.sbp_init(float(amount), bank.id, phone, comment, cba)
            code = await self.sbp_send_push(init.request_id)
            success = await self.sbp_push_verify(init.request_id, code)
            return success

    async def transactions(
        self, size: int = 25, page: int = 0, desc: bool = True
    ) -> Transactions:
        """
        Получить транзакции, можно только последние три месяца пока что это ограничения со стороны Райфа

        :param size: всегда 25, лучше не менять, райф не умеет с этим работать, хотя зачем-то заявляет
        :param page: страница. После какой-то будет игнорироваться
        :param desc: Не работает, но поле райф предоставил
        :return: Transactions
        """
        transactions_response = await self._client.get(
            f"https://amobile.raiffeisen.ru/rths/history/v1/transactions?"
            f"size={size}&sort=date&page={page}&order={'desc' if desc else 'asc'}",
            headers=await self.authorized_headers,
            timeout=20,
        )
        if transactions_response.status_code == 200:
            return Transactions(**transactions_response.json())
        else:
            raise ValueError(
                f"{transactions_response.status_code} {transactions_response.text}"
            )

    async def global_history_generator(self) -> AsyncGenerator[Transaction, None]:
        """
        Генератор для итерации страниц из истории операций, но дальше трёх страниц уйти получить не получится
        Но оно само остановится, когда увидит, что пошло по старой. Может быть полезно, да. И удобно. Благодарите.

        Можно ещё звезду на гитхабе поставить https://github.com/WhiteApfel/raiffather

        :return:
        """
        first_transaction: Transaction = None
        page = 0
        while True:
            transactions = await self.transactions(page=page)
            if first_transaction != transactions.list[0]:
                if not first_transaction:
                    first_transaction = transactions.list[0]
                for transaction in transactions.list:
                    yield transaction
                page += 1
            else:
                break
