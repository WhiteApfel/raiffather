from typing import Union

from raiffather.exceptions.base import RaifErrorResponse, RaifValueError
from raiffather.models.products import Account
from raiffather.modules._helpers import extend_product_types
from raiffather.modules.base import RaiffatherBase


class RaiffatherSettings(RaiffatherBase):
    @extend_product_types
    async def set_sbp_settings(self, allow: bool, account: Account):
        """
        Позволяет обновить настройки СБП. Например, привязать другой счёт или включить/
        отключить приём переводов в Райф

        :param allow: Разрешить ли приём
        :param cba: На какой счёт получать. Обязательно указать,
        даже если отключаете приём переводов
        :return: успешность выполнения
        """
        if account.currency.id == "RUR":
            data = {"allowTransfers": allow, "cba": account.cba}
            settings_response = await self._client.post(
                "https://amobile.raiffeisen.ru/rest/1/sbp/settings",
                headers=await self.authorized_headers,
                json=data,
            )
            if settings_response.status_code == 200:
                return True
            raise RaifErrorResponse(settings_response)
        raise RaifValueError(
            "Account currency must be RUR (ruble). It requires a central bank"
        )
