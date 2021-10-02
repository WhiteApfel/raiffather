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

    async def internal_transfer_verify_stub(self, request_id):
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

