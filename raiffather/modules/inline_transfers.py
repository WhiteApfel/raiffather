from typing import Union

from loguru import logger

from raiffather.exceptions.base import RaifErrorResponse
from raiffather.models.internal_transfers import (
    InternalTransferExchangeRate,
    InternalTransferInit,
)
from raiffather.models.products import Account, Accounts
from raiffather.modules._helpers import extend_product_types
from raiffather.modules.base import RaiffatherBase

logger.disable("raiffather")


class RaiffatherInlineTransfers(RaiffatherBase):
    async def internal_transfer_prepare(self):
        """
        Подготавливает к проведению перевода между счетами
        :return: bool
        """
        logger.debug("Internal transfer prepare...")
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/internal",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: "
                f"{r.url} -> {r.status_code}: {r.text}"
            )
            return True
        raise RaifErrorResponse(r)

    async def internal_transfer_accounts_source(self):
        r = await self._client.get(
            "https://amobile.raiffeisen.ru"
            "/rest/1/transfer/internal/account/source?alien=false",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: "
                f"{r.url} -> {r.status_code}: {r.text}"
            )
            return Accounts(accounts=r.json())
        raise RaifErrorResponse(r)

    async def internal_transfer_accounts_destination(self):
        r = await self._client.get(
            "https://amobile.raiffeisen.ru"
            "/rest/1/transfer/internal/account/destination?alien=false",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: "
                f"{r.url} -> {r.status_code}: {r.text}"
            )
            return Accounts(accounts=r.json())
        raise RaifErrorResponse(r)

    @extend_product_types
    async def internal_transfer_init(
        self,
        amount: Union[float, int],
        src: Account,
        dst: Account,
        source_currency: bool = True,
    ):
        """
        Инициализирует намерение перевода между счетами.
        В ответе содержит список методов подтверждения.

        :param amount: сумма перевода
        :param src: какой-либо идентификатор счёта-отправителя: id, cba, rma, название
        :param dst: какой-либо идентификатор счёта-получателя: id, cba, rma,  название
        :param source_currency: True, если сумма указана в валюте счёта получателя
        :return:
        """
        data = {
            "amount": float(amount),
            "amountInSrcCurrency": source_currency,
            "discountRateTypeId": 1,
            "dstAccountId": dst.id,
            "srcAccountId": src.id,
            "template": False,
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/internal",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: "
                f"{r.url} -> {r.status_code}: {r.text}"
            )
            return InternalTransferInit(**r.json())
        raise RaifErrorResponse(r)

    async def internal_transfer_verify_stub(self, request_id: Union[str, int]):
        """
        Подтверждение намерения для проведения перевода
        """
        headers = await self.authorized_headers
        headers.update({"Content-Type": "application/json"})
        r = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/internal/{request_id}/stub",
            headers=headers,
        )
        if r.status_code == 204:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: "
                f"{r.url} -> {r.status_code}: {r.text}"
            )
            return True
        raise RaifErrorResponse(r)

    async def internal_transfer_send_push(self, request_id: Union[str, int]) -> str:
        """
        Отправляет пуш-уведомление для подтверждение и ждёт,
        когда пуш-сервер его получит

        :param request_id: номер заявки
        :return: код подтверждения
        """
        data = {"deviceUid": self.device.uid, "pushId": self.device.push}

        send_code_response = await self._client.post(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/internal/{request_id}/push",
            json=data,
            headers=await self.authorized_headers,
        )
        if send_code_response.status_code == 201:
            push_id = send_code_response.json()["pushId"]
            otp = await self.wait_code(push_id)
            return otp
        raise RaifErrorResponse(send_code_response)

    async def internal_transfer_push_verify(
        self, request_id: Union[str, int], code: Union[str, int]
    ) -> bool:
        """
        Проверяет код подтверждения и подтверждает намерение на перевод

        :param request_id: номер заявки
        :param code: код подтверждения
        :return: успешно ли
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/internal/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": str(code)},
        )
        if verify_response.status_code == 204:
            return True
        raise RaifErrorResponse(verify_response)

    async def internal_transfer_exchange_rate(
        self,
        amount: Union[float, int] = 1.0,
        src: str = "RUR",
        dst: str = "USD",
        in_src_currency: bool = False,
        scope: int = 4,
    ):
        """
        Расчёт курса обмена валюты

        :param amount: сумма для обмена
        :param src: валюта отправителя
        :param dst: валюта получателя
        :param in_src_currency: True, если в валюте отправителя
        :param scope: хз что, не надо трогать
        :return:
        """
        params = {
            "currencySource": src,
            "currencyDest": dst,
            "amount": float(amount),
            "amount_in_src_currency": in_src_currency,
            "scope": scope,
        }
        rate_response = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/exchange/rate", params=params
        )
        if rate_response.status_code == 200:
            return InternalTransferExchangeRate(**rate_response.json())
        raise RaifErrorResponse(rate_response)
