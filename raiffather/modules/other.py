from raiffather.exceptions.base import RaifErrorResponse
from raiffather.modules.base import RaiffatherBase


class RaiffatherOther(RaiffatherBase):
    async def technical_alerts(self):
        r = await self._client.get(
            f"https://amobile.raiffeisen.ru/import/mobile/android/entrance.json",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return r.json()
        else:
            raise RaifErrorResponse(r)
