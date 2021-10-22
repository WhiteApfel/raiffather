from typing import Union

from loguru import logger

from raiffather.exceptions.base import RaifErrorResponse
from raiffather.models.c2c import (
    C2cInit,
    E3DSOTPData,
    C2cRetrieve,
    C2cTpcOne,
    C2cCard,
    C2cNewCard,
    BinInfo,
)
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
        raise RaifErrorResponse(r)

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
            return C2cRetrieve(**r.json())
        raise RaifErrorResponse(r)

    async def c2c_fees(
        self,
        src: Union[C2cTpcOne, C2cCard, str],
        dst: Union[C2cTpcOne, C2cCard, str],
        amount,
    ):
        """
        Рассчитывает комиссию со стороны Райфа для перевода.
        Другие банки могут взять комиссию за стягивание или пополнение
        :return: bool
        """
        dst_data = (
            {"serno": dst.card.id}
            if type(dst) is C2cCard
            else {
                "pan": dst
                if type(dst) is str and len(dst) == 16
                else "4111111111111111"
            }
        )
        src_data = (
            {"serno": src.card.id}
            if type(src) is C2cCard
            else {
                "pan": src
                if type(dst) is str and len(src) == 16
                else "4111111111111111"
            }
        )
        logger.debug("C2C getting fees...")
        r = await self._client.post(
            "https://e-commerce.raiffeisen.ru/ws/link/c2c/v1.0/fees",
            headers=await self.authorized_headers,
            json={
                "amount": float(amount),
                "dst": dst_data,
                "feeCurrency": 643,
                "src": src_data,
                "transferCurrency": 643,
            },
        )
        if r.status_code == 200:
            logger.debug(
                f"C2C got fees successfully. {r.request.method}: {r.url} -> "
                f"{r.status_code}: {r.text}"
            )
            return r.json()
        raise RaifErrorResponse(r)

    async def c2c_init(
        self,
        amount,
        src: Union[C2cTpcOne, C2cCard, C2cNewCard],
        dst: Union[C2cTpcOne, C2cCard, C2cNewCard],
    ):
        """
        Инициализирует намерение перевода. Возвращает какие-то данные
        Нужная штука, если хотите сделать перевод, без неё вообще нельзя, гы
        :return: bool
        """
        class2type = {C2cCard: "cardId", C2cTpcOne: "tpcId", C2cNewCard: "newCard"}
        src_data = {
            class2type[type(src)]: src.id
            if type(src) is C2cTpcOne
            else src.card.id
            if type(src) is C2cCard
            else src.dict(by_alias=True),
            "type": class2type[type(src)],
        }
        dst_data = {
            class2type[type(dst)]: dst.id
            if type(dst) is C2cTpcOne
            else dst.card.id
            if type(dst) is C2cCard
            else dst.dict(by_alias=True),
            "type": class2type[type(dst)],
        }
        logger.debug("C2C initialization...")
        r = await self._client.post(
            "https://e-commerce.raiffeisen.ru/c2c/v2.0/transfer",
            headers=await self.authorized_headers,
            json={
                "amount": {"currency": 643, "sum": amount},
                "commission": {"currency": 810, "sum": 0.0},
                "dst": dst_data,
                "src": src_data,
                "salary": False,
            },
        )
        if r.status_code == 200:
            logger.debug(
                f"C2C initialized successfully. {r.request.method}: {r.url} -> "
                f"{r.status_code}: {r.text}"
            )
            return C2cInit(**r.json())
        logger.critical(
            f"C2C initialization failed. {r.request.method}: {r.url} -> "
            f"{r.status_code}: {r.text}\nRequest headers: {r.request.headers}\n"
            f"Request content:\n{r.request.content}"
        )
        raise RaifErrorResponse(r)

    async def c2c_e3ds_start(self, request_id: Union[str, int]):
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
        raise RaifErrorResponse(e3dsotp_response)

    async def c2c_e3ds_pareq(self, acs_url: str, pareq: str, term_url: str = None):
        data = {
            "MD": "",
            "TermUrl": term_url or "https://imobile.raiffeisen.ru/3ds/1400474370",
            "PaReq": pareq,
        }
        r = await self._client.post(
            acs_url,
            headers=await self.authorized_headers,
            data=data,
        )
        if r.status_code == 200:
            return r.text
        raise RaifErrorResponse(r)

    async def c2c_e3ds_verify(self, request_id: Union[str, int], pares: str):
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
        raise RaifErrorResponse(r)

    async def c2c_bin_info(self, card_bin: Union[str, int]):
        r = await self._client.get(
            f"https://amobile.raiffeisen.ru/rest/transfer/c2c/bin/{card_bin}",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return BinInfo(**r.json())
        raise RaifErrorResponse(r)
