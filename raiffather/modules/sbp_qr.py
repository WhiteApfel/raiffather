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
