from typing import List

from fuzzywuzzy import process
from loguru import logger

from raiffather.exceptions.sbp import SBPRecipientNotFound
from raiffather.models.products import Account
from raiffather.models.sbp import SbpBank, SbpInit, SbpPam, SbpSettings, SbpCommission
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
        settings_reponse = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/sbp/settings",
            headers=await self.authorized_headers,
        )
        if settings_reponse.status_code == 200:
            return SbpSettings(**settings_reponse.json())
        else:
            raise ValueError(f"{settings_reponse.status_code} {settings_reponse.text}")

    async def sbp_banks(self, phone, cba: str = None):
        if not self.products:
            self.products = await self.get_products()
        data = {"phone": phone, "srcCba": cba or (await self.sbp_settings()).cba}
        sbp_banks_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/bank",
            headers=await self.authorized_headers,
            json=data,
        )
        if sbp_banks_response.status_code == 200:
            return [SbpBank(**bank) for bank in sbp_banks_response.json()]
        else:
            raise ValueError(
                f"{sbp_banks_response.status_code} {sbp_banks_response.text}"
            )

    async def sbp_pam(self, bank_id: str, phone: str, cba: str = None) -> SbpPam:
        """
        Не знаю, зачем это надо, но это обязательный этап проведения перевода по СБП

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
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/pam",
            headers=await self.authorized_headers,
            json=data,
        )
        if r.status_code == 200:
            return SbpPam(**r.json())
        elif r.status_code == 417:
            raise SBPRecipientNotFound(r.json()["_form"][0])
        else:
            raise ValueError(f"{r.status_code}: {r.text}")

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
        comission_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/commission",
            headers=await self.authorized_headers,
            json=data,
        )
        if comission_response.status_code == 200:
            return SbpCommission(**comission_response.json())
        else:
            raise ValueError(
                f"{comission_response.status_code} {comission_response.text}"
            )

    async def sbp_init(
        self, amount, bank, phone, message=None, cba: str = None
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
            "bankId": bank,
            # "commission": 0.0,
            # "currency": "810",
            "message": message or "",
            "phone": phone,
            "recipient": "",
            "srcAccountId": self._products.accounts[0].id,
            "srcCba": cba or (await self.sbp_settings()).cba,
            "template": False,
        }
        init_response = await self._client.post(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact",
            headers=await self.authorized_headers,
            json=data,
        )
        if init_response.status_code == 200:
            return SbpInit(**init_response.json())
        else:
            raise ValueError(f"{init_response.status_code} {init_response.text}")

    async def sbp_prepare(self) -> bool:
        """
        Подготавливает к проведению перевода по СБП, обязательный пунктик
        :return: bool
        """
        r = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact",
            headers=await self.authorized_headers,
        )
        if r.status_code == 200:
            return True
        else:
            raise ValueError(f"{r.status_code} {r.text}")

    async def sbp_accounts(self) -> List[Account]:
        """
        Доступные счета для отправки денег
        :return: list[Account]
        """
        accounts_response = await self._client.get(
            "https://amobile.raiffeisen.ru/rest/1/transfer/contact/account?alien=false",
            headers=await self.authorized_headers,
        )
        if accounts_response.status_code == 200:
            return [Account(**a) for a in accounts_response.json()]
        else:
            raise ValueError(
                f"{accounts_response.status_code} {accounts_response.text}"
            )

    def sbp_bank_fuzzy_search(self, banks: list, bank: str):
        """
        Возвращает название банка из списка, название которого наиболее совпадает с искомым

        :param banks: лист названий банков
        :param bank: искомое название
        :return:
        """
        return process.extractOne(bank, banks)[0]

    async def sbp_send_push(self, request_id) -> str:
        """
        Отправляет пуш-уведомление для подтверждение и ждёт, когда пуш-сервер его получит

        :param request_id: номер заявки
        :return: код подтверждения
        """
        data = {"deviceUid": self.device.uid, "pushId": self.device.push}

        send_code_response = await self._client.post(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/contact/{request_id}/push",
            json=data,
            headers=await self.authorized_headers,
        )
        if send_code_response.status_code == 201:
            push_id = send_code_response.json()["pushId"]
            otp = await self.wait_code(push_id)
            return otp
        else:
            raise ValueError(
                f"{send_code_response.status_code} {send_code_response.text}"
            )

    async def sbp_push_verify(self, request_id, code) -> bool:
        """
        Проверяет код подтверждения

        :param request_id: номер заявки
        :param code: код подтверждения
        :return: успешно ли
        """
        verify_response = await self._client.put(
            f"https://amobile.raiffeisen.ru/rest/1/transfer/contact/{request_id}/push",
            headers=await self.authorized_headers,
            json={"code": code},
        )
        if verify_response.status_code == 204:
            return True
        return False

    async def sbp(self, phone, bank, amount, comment=None):
        """
        Единый метод для автоматического проведения всего перевода

        :param phone: номер телефона получателя
        :param bank: название банка получателя, можно в произвольной форме, типа "Тинька" или "Райф"
        :param amount: сумма перевода в рублях
        :param comment: комментарий к переводу
        :return: успешно ли
        """
        cba = (await self.sbp_settings()).cba
        await self.sbp_prepare()
        banks = await self.sbp_banks(phone=phone, cba=cba)
        bank_name = self.sbp_bank_fuzzy_search([b.name for b in banks], bank)
        bank = next((bank for bank in banks if bank.name == bank_name), None)
        if bank:
            pam = await self.sbp_pam(bank_id=bank.id, phone=phone, cba=cba)
            com = float(
                (
                    await self.sbp_commission(
                        bank=bank.id, phone=phone, amount=float(amount), cba=cba
                    )
                ).commission
            )
            init = await self.sbp_init(float(amount), bank.id, phone, comment, cba)
            code = await self.sbp_send_push(init.request_id)
            success = await self.sbp_push_verify(init.request_id, code)
            return success
