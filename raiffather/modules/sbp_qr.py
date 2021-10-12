from raiffather.exceptions.base import RaifErrorResponse
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
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def sbp_qr_pay_init(self, amount, src, qr_data: SbpQRData):
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
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def sbp_qr_send_push(self, request_id) -> str:
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
        else:
            raise ValueError(
                f"{send_code_response.status_code} {send_code_response.text}"
            )

    async def sbp_qr_push_verify(self, request_id, code) -> bool:
        """
        Проверяет код подтверждения

        :param request_id: номер заявки
        :param code: код подтверждения
        :return: успешно ли
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/dailybanking/ro/v1.0/c2b/process/transfer/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": code},
        )
        if verify_response.status_code == 204:
            return True
        else:
            raise RaifErrorResponse(verify_response)

    async def sbp_qr_decode_url(self, url):
        data = {
            "scanCodeType": 3,
            "scanString": url
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/qr",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            return SbpQrInfo(**r.json())
        else:
            raise RaifErrorResponse(r)
