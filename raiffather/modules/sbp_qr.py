from raiffather.models.sbp_qr import SbpQRData
from raiffather.modules.base import RaiffatherBase


class RaiffatherSbpQR(RaiffatherBase):
    async def sbp_qr_pay_prepare(self):
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/dailybanking/ro/v1.0/c2b/process/transfer",
            headers=await self.authorized_headers
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
            "paymentPurpose": ""
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/dailybanking/ro/v1.0/c2b/process/transfer",
            headers=await self.authorized_headers,
            json=data
        )
        if r.status_code == 200:
            return r.json()
        else:
            raise ValueError(f"{r.status_code} {r.text}")
