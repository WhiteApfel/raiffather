from raiffather.exceptions.base import RaifErrorResponse
from raiffather.modules.base import RaiffatherBase


class RaiffatherSettings(RaiffatherBase):
    async def set_sbp_settings(self, allow: bool, cba: str):
        """
        Позволяет обновить настройки СБП. Например, привязать другой счёт или включить/отключить приём переводов в Райф

        :param allow: Разрешить ли приём
        :param cba: На какой счёт получать. Обязательно указать, даже если отключаете приём переводов
        :return: успешность выполнения
        """
        data = {"allowTransfers": allow, "cba": cba}
        settings_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/sbp/settings",
            headers=await self.authorized_headers,
            json=data,
        )
        if settings_response.status_code == 200:
            return True
        raise RaifErrorResponse(settings_response)
