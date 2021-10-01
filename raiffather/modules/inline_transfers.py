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

    async def internal_transfers_accounts_source(self):
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

    async def internal_transfers_accounts_destination(self):
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
