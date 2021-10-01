from raiffather.models.internal_transfers import InternalTransactionInit
from raiffather.models.products import Account
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
            return [Account(**a) for a in r.json()]
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
            return [Account(**a) for a in r.json()]
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def internal_transfer_init(self, amount, dst, src):
        data = {
            "amount": float(amount),
            "amountInSrcCurrency": True,
            "discountRateTypeId": 1,
            "dstAccountId": dst,
            "srcAccountId": src,
            "template": False
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/internal",
            headers=await self.authorized_headers,
            json=data
        )
        if r.status_code == 200:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            return InternalTransactionInit(**r.json())
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def internal_transfer_verify(self, request_id):
        r = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/internal/{request_id}/stub",
            headers=await self.authorized_headers
        )
        if r.status_code == 204:
            logger.debug(
                f"Internal transfer prepared successfully. {r.request.method}: {r.url} -> {r.status_code}: {r.text}"
            )
            return True
        else:
            raise ValueError(f"{r.status_code} {r.text}")

