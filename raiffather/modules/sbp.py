from typing import List, Union

from fuzzywuzzy import process
from loguru import logger

from raiffather.exceptions.base import RaifErrorResponse
from raiffather.exceptions.sbp import SBPRecipientNotFound
from raiffather.models.products import Account
from raiffather.models.sbp import (
    SbpBank,
    SbpBanks,
    SbpCommission,
    SbpInit,
    SbpPam,
    SbpSettings,
)
from raiffather.modules.base import RaiffatherBase

logger.disable("raiffather")


class RaiffatherSBP(RaiffatherBase):
    async def sbp_settings(self) -> SbpSettings:
        """
        Получение настроек про СБП

        Важным полем является номер аккаунта в ЦБ: SbpSettings.cba

        :return: Информация о настройках СБП
        :rtype: SbpSettings
        """
        settings_response = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/phone/settings",
            headers=await self.authorized_headers,
        )
        if settings_response.status_code == 200:
            return SbpSettings(**settings_response.json())
        raise RaifErrorResponse(settings_response)

    async def sbp_stored_banks(self, phone) -> SbpBanks:
        """
        Получение банков для получателя. Интересным является в ответе банк по умолчанию

        :param phone: номер телефона получателя
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpBanks
        """
        if not self.products:
            self.products = await self.get_products()
        data = {"phone": phone}
        sbp_banks_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/phone/stored-banks",
            headers=await self.authorized_headers,
            json=data,
        )
        if sbp_banks_response.status_code == 200:
            return SbpBanks(
                list=[SbpBank(**bank) for bank in sbp_banks_response.json()]
            )
        raise RaifErrorResponse(sbp_banks_response)

    async def sbp_banks(self, phone, cba: str = None) -> SbpBanks:
        """
        Получение банков для получателя. Интересным является в ответе банк по умолчанию

        :param phone: номер телефона получателя
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpBanks
        """
        if not self.products:
            self.products = await self.get_products()
        data = {"phone": phone, "srcCba": cba or (await self.sbp_settings()).cba}
        sbp_banks_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/bank",
            headers=await self.authorized_headers,
            json=data,
        )
        if sbp_banks_response.status_code == 200:
            return SbpBanks(
                list=[SbpBank(**bank) for bank in sbp_banks_response.json()]
            )
        raise RaifErrorResponse(sbp_banks_response)

    async def sbp_pam(self, bank_id: str, phone: str, cba: str = None) -> dict:
        """
        Внутри есть информация о лимитах

        :param bank_id: id банка получателя, можно узнать в self.sbp_banks()
        :param phone: номер телефона получателя
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpPam
        """
        data = {
            "bankId": bank_id,
            "phone": phone,
            "srcCba": cba or (await self.sbp_settings()).cba,
        }
        r = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/2/transfer/phone/pam",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            return r.json()
            # TODO: add model
            # {
            #   "pams": [
            #     {
            #       "priority": true,
            #       "channel": {
            #         "id": 2,
            #         "name": "SBP"
            #       },
            #       "recipient": "Никита Артемович Б",
            #       "limits": {
            #         "maxAmount": 300000.00,
            #         "minAmount": 0.00
            #       }
            #     }
            #   ],
            #   "errors": []
            # }
        if r.status_code == 417:
            raise SBPRecipientNotFound(r.json()["_form"][0])
        raise RaifErrorResponse(r)

    async def sbp_commission(
        self, bank, phone, amount, cba: str = None
    ) -> SbpCommission:
        """
        Расчёт комиссии для перевода по СБП

        :param bank: id банка получателя, можно узнать в self.sbp_banks()
        :param phone: номер телефона получателя
        :param amount: сумма перевода в рублях
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpCommission
        """
        data = {
            "amount": float(amount),
            "bankId": bank,
            "phone": phone,
            "srcCba": cba or (await self.sbp_settings()).cba,
        }
        commission_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/phone/commission",
            headers=await self.authorized_headers,
            json=data,
        )
        if commission_response.status_code == 200:
            return SbpCommission(**commission_response.json())
        raise RaifErrorResponse(commission_response)

    async def sbp_init(
        self,
        amount: Union[float, int],
        bank: Union[str, int],
        phone: str,
        message=None,
        cba: str = None,
    ) -> SbpInit:
        """
        Ещё один этап для проведения перевода по СБП

        :param amount: сумма перевода в рублях
        :param bank: id банка получателя, можно узнать в self.sbp_banks()
        :param phone: номер телефона получателя
        :param message: комментарий к перевод
        :param cba: номер вашего аккаунта в ЦБ, можно узнать в self.sbp_settings()
        :return: SbpInit
        """
        data = {
            "amount": float(amount),
            "bankId": int(bank),
            "commission": 0.0,
            "currency": "810",
            "channelId": "2",
            "message": message or "",
            "phone": phone,
            "recipient": "",
            "srcAccountId": self.products.accounts[0].id,
            "srcCba": cba or (await self.sbp_settings()).cba,
            "template": False,
        }
        init_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/phone/operation",
            headers=await self.authorized_headers,
            json=data,
        )
        if init_response.status_code == 200:
            return SbpInit(**init_response.json())
        raise RaifErrorResponse(init_response)

    async def sbp_prepare(self) -> bool:
        """
        Подготавливает к проведению перевода по СБП, обязательный пунктик
        :return: bool
        """
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/phone/operation",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return True
        raise RaifErrorResponse(r)

    async def sbp_accounts(self) -> List[Account]:
        """
        Доступные счета для отправки денег
        :return: list[Account]
        """
        accounts_response = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/phone/account?alien=false",
            headers=await self.authorized_headers,
        )
        if accounts_response.status_code == 200:
            return [Account(**a) for a in accounts_response.json()]
        raise RaifErrorResponse(accounts_response)

    def sbp_bank_fuzzy_search(self, banks: list, bank: str) -> SbpBank:
        """
        Возвращает название банка из списка, название которого
        наиболее совпадает с искомым

        :param banks: лист названий банков
        :param bank: искомое название
        :return:
        """
        return process.extractOne(bank, banks)[0]

    async def sbp_send_push(self, request_id: Union[str, int]) -> str:
        """
        Отправляет пуш-уведомление для подтверждения и ждёт,
        когда пуш-сервер его получит

        :param request_id: номер заявки
        :return: код подтверждения
        """
        print(self.device.push)
        data = {"deviceUid": self.device.uid, "pushId": self.device.push}

        send_code_response = await self._client.post(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/phone/operation/{request_id}/push",
            json=data,
            headers=await self.authorized_headers,
        )
        if send_code_response.status_code == 200:
            push_id = send_code_response.json()["pushId"]
            otp = await self.wait_code(push_id)
            return otp
        raise RaifErrorResponse(send_code_response)

    async def sbp_push_verify(
        self, request_id: Union[str, int], code: Union[str, int]
    ) -> bool:
        """
        Проверяет код подтверждения

        :param request_id: номер заявки
        :param code: код подтверждения
        :return: успешно ли
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/phone/operation/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": str(code)},
        )
        if verify_response.is_success:
            return True
        raise RaifErrorResponse(verify_response)

    async def sbp(
        self, phone: str, bank: str, amount: Union[float, int], comment=None
    ) -> bool:
        """
        Единый метод для автоматического проведения всего перевода

        :param phone: номер телефона получателя
        :param bank: название банка получателя, можно в произвольной форме,
        типа "Тинька" или "Райф". Можно с ошибками.
        :param amount: сумма перевода в рублях
        :param comment: комментарий к переводу
        :return: bool
        """
        cba = (await self.sbp_settings()).cba
        await self.sbp_prepare()
        banks = await self.sbp_banks(phone=phone, cba=cba)
        bank_name = self.sbp_bank_fuzzy_search([b.name for b in banks], bank)
        bank = next((bank for bank in banks if bank.name == bank_name), None)
        if bank:
            await self.sbp_pam(bank_id=bank.id, phone=phone, cba=cba)
            init = await self.sbp_init(float(amount), bank.id, phone, comment, cba)
            code = await self.sbp_send_push(init.request_id)
            success = await self.sbp_push_verify(init.request_id, code)
            return success
