from typing import Optional, Union

from raiffather.exceptions.base import RaifErrorResponse
from raiffather.models.products import Card
from raiffather.models.service_payments import TopUpMobileAccountProviderInfo, TopUpMobileAccountVerify
from raiffather.modules.base import RaiffatherBase


class RaiffatherServicePayments(RaiffatherBase):
    async def top_up_mobile_account_get_provider_info(self, phone_number: str) -> TopUpMobileAccountProviderInfo:
        phone_number = phone_number if phone_number[0] == "7" else f"7{phone_number}"
        provider_response = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/payment/online/provider/mobile",
            headers=await self.authorized_headers,
            params={"phone": phone_number}
        )
        if provider_response.status_code == 200:
            return TopUpMobileAccountProviderInfo(**provider_response.json())
        raise RaifErrorResponse(provider_response)

    async def top_up_mobile_account_init(
        self,
        phone_number: str,
        amount: Union[int, float],
        card: Optional[Card] = None,
        provider_id: Optional[str] = None,
        save_template: Optional[bool] = False,
    ) -> TopUpMobileAccountVerify:
        data = {
            "cardId": str(card.id),
            "parameters": [
                {
                    "name": "amount",
                    "value": amount,
                },
                {
                    "name": "account",
                    "value": phone_number.lstrip("7"),
                }
            ],
            "providerId": str(provider_id),
            "template": save_template,
            "typeId": "7",
        }
        response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/payment/online",
            headers=await self.authorized_headers,
            json=data,
        )

        if response.status_code == 200:
            return TopUpMobileAccountVerify(**response.json())
        raise RaifErrorResponse(response)

    async def top_up_mobile_account_send_push(self, request_id: str) -> str:
        r = await self._client.post(
            f"https://amobile.raiffeisen.ru/rest/payment/online/{request_id}/push",
            headers=await self.authorized_headers,
            json={"deviceUid": self.device.uid, "pushId": self.device.push},
        )
        if r.status_code == 201:
            return r.json()["pushId"]
        raise RaifErrorResponse(r)

    async def top_up_mobile_account_verify(self, request_id: str, code: Union[str, int]) -> bool:
        r = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/payment/online/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": str(code)},
        )
        if r.status_code == 204:
            return True
        raise RaifErrorResponse(r)
