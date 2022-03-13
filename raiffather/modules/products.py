from loguru import logger
from typing import Union

from raiffather.exceptions.base import RaifErrorResponse
from raiffather.models.products import Account, AccountDetails, BaseVerifyInit, Card, CardDetails
from raiffather.modules.base import RaiffatherBase

logger.disable("raiffather")


class RaiffatherProducts(RaiffatherBase):
    async def get_account_details(self, account: Account):
        r = await self._client.get(
            f"https://amobile.raiffeisen.ru/rest/1/product/account/{account.id}/requisites",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return AccountDetails(**r.json())
        raise RaifErrorResponse(r)

    async def get_card_details_prepare(self):
        r = await self._client.get(
            "https://orc.ecom.raiffeisen.ru/display/requisites",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return r.json()
        raise RaifErrorResponse(r)

    async def get_card_details_init(self, card: Card):
        r = await self._client.get(
            f"https://orc.ecom.raiffeisen.ru/display/requisites/card-holder-check/{card.id}",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return r.json()
        raise RaifErrorResponse(r)

    async def get_card_details_request(self, card: Card):
        r = await self._client.post(
            f"https://orc.ecom.raiffeisen.ru/display/requisites",
            headers=await self.authorized_headers,
            json={
                "cardId": card.id,
            },
        )
        if r.status_code == 200:
            return BaseVerifyInit(**r.json())
        raise RaifErrorResponse(r)

    async def get_card_details_send_push(self, request_id: str) -> str:
        logger.debug("Get card details...")
        r = await self._client.post(
            f"https://orc.ecom.raiffeisen.ru/display/requisites/{request_id}/PUSHOTP",
            headers=await self.authorized_headers,
            json={"deviceUid": self.device.uid, "pushId": self.device.push},
        )
        if r.status_code == 200:
            push_id = r.json()["pushId"]
            otp = await self.wait_code(push_id)
            return otp
        raise RaifErrorResponse(r)

    async def get_card_details_verify(self, request_id: str, code: Union[str, int]) -> bool:
        logger.debug("Get card details...")
        r = await self._client.put(
            f"https://orc.ecom.raiffeisen.ru/display/requisites/{request_id}/PUSHOTP",
            headers=await self.authorized_headers,
            json={"code": str(code)},
        )
        if r.status_code == 204:
            return True
        raise RaifErrorResponse(r)

    async def get_card_details_receive(self, request_id: str, code: Union[str, int]) -> CardDetails:
        logger.debug("Get card details...")
        r = await self._client.get(
            f"https://orc.ecom.raiffeisen.ru/display/requisites/{request_id}",
            headers=await self.authorized_headers,
        )
        if r.status_code == 204:
            return CardDetails(**r.json())
        raise RaifErrorResponse(r)
