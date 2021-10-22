from typing import Union

from raiffather.exceptions.base import RaifErrorResponse
from raiffather.models.products import Account
from raiffather.models.sbp_qr import SbpQRData, SbpQRInit, SbpQrInfo
from raiffather.modules.base import RaiffatherBase


class RaiffatherSbpQR(RaiffatherBase):
    async def sbp_qr_pay_prepare(self):
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/dailybanking/ro/v1.0/c2b/process/transfer",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return True
        raise RaifErrorResponse(r)

    async def sbp_qr_pay_init(
        self, amount: Union[float, int], src: Account, qr_data: SbpQRData
    ):
        data = {
            "amount": float(amount),
            "bankId": qr_data.bank_id,
            "crc": qr_data.crc,
            "qrc_id": qr_data.qrc,
            "qrcType": qr_data.qrc_type,
            "srcCba": src.cba,
            "currency": "RUB",
            "paymentPurpose": "",
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/dailybanking/ro/v1.0/c2b/process/transfer",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            return SbpQRInit(**r.json())
        raise RaifErrorResponse(r)

    async def sbp_qr_send_push(self, request_id: Union[str, int]) -> str:
        """
        Отправляет пуш-уведомление для подтверждение и ждёт, когда пуш-сервер его получит

        :param request_id: номер заявки
        :return: код подтверждения
        """
        data = {"deviceUid": self.device.uid, "pushId": self.device.push}

        send_code_response = await self._client.post(
            f"https://amobile.raiffeisen.ru/dailybanking/ro/v1.0/c2b/process/transfer/{request_id}/push",
            json=data,
            headers=await self.authorized_headers,
        )
        if send_code_response.status_code == 200:
            push_id = send_code_response.json()["pushId"]
            otp = await self.wait_code(push_id)
            return otp
        raise RaifErrorResponse(send_code_response)

    async def sbp_qr_push_verify(
        self, request_id: Union[str, int], code: Union[str, int]
    ) -> bool:
        """
        Проверяет код подтверждения

        :param request_id: номер заявки
        :param code: код подтверждения
        :return: успешно ли
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/dailybanking/ro/v1.0/c2b/process/transfer/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": str(code)},
        )
        if verify_response.status_code == 204:
            return True
        raise RaifErrorResponse(verify_response)

    async def sbp_qr_decode_url(self, url: str):
        data = {"scanCodeType": 3, "scanString": url}
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/qr",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            return SbpQrInfo(**r.json())
        raise RaifErrorResponse(r)
