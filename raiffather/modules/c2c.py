from typing import Union

from loguru import logger

from raiffather.models.c2c import C2cInit, E3DSOTPData, C2cRetrieve
from raiffather.modules.base import RaiffatherBase

logger.disable("raiffather")


class RaiffatherC2C(RaiffatherBase):
    async def c2c_prepare(self):
        """
        Подготавливает к проведению перевода по номеру карты, обязательный пунктик
        :return: bool
        """
        logger.debug(f"C2C prepare...")
        r = await self._client.get(
            "https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"C2C prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            return True
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_retrieve(self):
        """
        Подготавливает к проведению перевода по номеру карты, обязательный пунктик
        :return: bool
        """
        logger.debug(f"C2C retrieve initial data...")
        r = await self._client.get(
            "https://e-commerce.raiffeisen.ru/c2c/v2.0/retrieveInitialData",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"C2C retrieved initial data successfully. {r.request.method}: {r.url} -> "
                f"{r.status_code}: {r.text}"
            )
            try:
                return C2cRetrieve(**r.json())
            except Exception as e:
                print(e)
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_fees(self, amount, dst=83159519, src="4111111111111111"):
        """
        Рассчитывает комиссию со стороны Райфа для перевода.
        Другие банки могут взять комиссию за стягивание или пополнение
        :return: bool
        """
        logger.debug("C2C getting fees...")
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
            logger.debug(
                f"C2C got fees successfully. {r.request.method}: {r.url} -> "
                f"{r.status_code}: {r.text}"
            )
            return r.json()
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_init(self, amount):
        """
        Инициализирует намерение перевода. Возвращает какие-то данные
        Нужная штука, если хотите сделать перевод, без неё вообще нельзя, гы
        :return: bool
        """
        logger.debug("C2C initialization...")
        r = await self._client.post(
            "https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer",
            headers=await self.authorized_headers,
            json={
                "amount": {"currency": 643, "sum": amount},
                "commission": {"currency": 810, "sum": 0.0},
                "dst": {"cardId": 83159519, "type": "cardId"},
                "src": {"tpcId": 233841, "type": "tpcId"},
                "salary": False,
            },
        )
        if r.status_code == 200:
            logger.debug(
                f"C2C initialized successfully. {r.request.method}: {r.url} -> "
                f"{r.status_code}: {r.text}"
            )
            return C2cInit(**r.json())
        else:
            logger.critical(
                f"C2C initialization failed. {r.request.method}: {r.url} -> "
                f"{r.status_code}: {r.text}\nRequest headers: {r.request.headers}\n"
                f"Request content:\n{r.request.content}"
            )
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_e3ds_start(self, request_id):
        """
        Получение данных для перенаправления на 3DS

        :param request_id: номер заявки на перевод, получается в self.c2c_init()
        :return:
        """
        logger.debug("C2C getting E3DS OTP data")
        headers = await self.authorized_headers
        headers.update({"Content-Type": "application/json"})
        e3dsotp_response = await self._client.post(
            f"https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer/{request_id}/E3DSOTP",
            headers=headers,
        )
        if e3dsotp_response.status_code == 200:
            logger.debug(
                f"C2C got E3DS OTP data successfully. {e3dsotp_response.request.method}: "
                f"{e3dsotp_response.url} -> "
                f"{e3dsotp_response.status_code}: {e3dsotp_response.text}"
            )
            return E3DSOTPData(**e3dsotp_response.json())
        else:
            raise ValueError(f"{e3dsotp_response.status_code} {e3dsotp_response.text}")

    async def c2c_e3ds_pareq(self, acs_url, pareq):
        data = {
            "MD": "",
            "TermUrl": "https://imobile.raiffeisen.ru/3ds/1400474370",
            "PaReq": pareq,
        }
        r = await self._client.post(
            acs_url,
            headers=await self.authorized_headers,
            data=data,
        )
        if r.status_code == 200:
            return r.text
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def c2c_e3ds_verify(self, request_id, pares):
        data = {
            "pares": pares,
        }
        r = await self._client.put(
            f"https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer/{request_id}/E3DSOTP",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            return True
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
