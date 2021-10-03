from typing import Union

from raiffather.models.internal_transfers import (
    InternalTransferInit,
    InternalTransferExchangeRate,
)
from raiffather.models.products import Account, Accounts
from raiffather.modules.base import RaiffatherBase
from loguru import logger

logger.disable("raiffather")


class RaiffatherInlineTransfers(RaiffatherBase):
    async def internal_transfer_prepare(self):
        """
        Подготавливает к проведению перевода между счетами
        :return: bool
        """
        logger.debug(f"Internal transfer prepare...")
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/internal",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            return True
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def internal_transfer_accounts_source(self):
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/internal/account/source?alien=false",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            return Accounts(accounts=r.json())
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def internal_transfer_accounts_destination(self):
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/internal/account/destination?alien=false",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            return Accounts(accounts=r.json())
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def internal_transfer_init(
        self,
        amount: Union[float, int],
        src: Union[str, int, Account],
        dst: Union[str, int, Account],
        source_currency=True,
    ):
        if type(src) in [int, str]:
            src = self.products.accounts[src]
        if type(dst) in [int, str]:
            dst = self.products.accounts[dst]
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
                f"Internal transfer prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            try:
                return InternalTransferInit(**r.json())
            except Exception as e:
                print(e)
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def internal_transfer_verify_stub(self, request_id):
        headers = await self.authorized_headers
        headers.update({"Content-Type": "application/json"})
        r = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/internal/{request_id}/stub",
            headers=headers,
        )
        if r.status_code == 204:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            return True
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def internal_transfer_send_push(self, request_id) -> str:
        """
        Отправляет пуш-уведомление для подтверждение и ждёт, когда пуш-сервер его получит

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
        else:
            raise ValueError(
                f"{send_code_response.status_code} {send_code_response.text}"
            )

    async def internal_transfer_push_verify(self, request_id, code) -> bool:
        """
        Проверяет код подтверждения

        :param request_id: номер заявки
        :param code: код подтверждения
        :return: успешно ли
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/internal/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": code},
        )
        if verify_response.status_code == 204:
            return True
        return False

    async def internal_transfer_exchange_rate(
        self, amount=1.0, src="RUR", dst="USD", in_src_currency=False, scope=4
    ):
        params = {
            "currencySource": src,
            "currencyDest": dst,
            "amount": float(amount),
            "amount_in_src_currency": in_src_currency,
            "scope": scope,
        }
        rate_response = await self._client.get(
            f"https://amobile.raiffeisen.ru/rest/exchange/rate", params=params
        )
        if rate_response.status_code == 200:
            return InternalTransferExchangeRate(**rate_response.json())
        else:
            raise ValueError(f"{rate_response.status_code} {rate_response.text}")
