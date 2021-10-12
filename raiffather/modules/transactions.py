from typing import AsyncGenerator

from loguru import logger

from raiffather.exceptions.base import RaifErrorResponse, RaifUnauthorized
from raiffather.models.transactions import Transactions, Transaction
from raiffather.modules.base import RaiffatherBase

logger.disable("raiffather")


class RaiffatherTransactions(RaiffatherBase):
    async def transactions(
        self, size: int = 25, page: int = 0, desc: bool = True
    ) -> Transactions:
        """
        Получить транзакции, можно только последние три месяца пока что это ограничения со стороны Райфа

        :param size: всегда 25, лучше не менять, райф не умеет с этим работать, хотя зачем-то заявляет
        :param page: страница. После какой-то будет игнорироваться
        :param desc: Не работает, но поле райф предоставил
        :return: Transactions
        """
        transactions_response = await self._client.get(
            f"https://amobile.raiffeisen.ru/rths/history/v1/transactions?"
            f"size={size}&sort=date&page={page}&order={'desc' if desc else 'asc'}",
            headers=await self.authorized_headers,
            timeout=20,
        )
        if transactions_response.status_code == 200:
            return Transactions(**transactions_response.json())
        elif transactions_response.status_code == 401:
            raise RaifUnauthorized(transactions_response)
        else:
            raise RaifErrorResponse(transactions_response)

    async def global_history_generator(self) -> AsyncGenerator[Transaction, None]:
        """
        Генератор для итерации страниц из истории операций, но дальше трёх страниц уйти получить не получится
        Но оно само остановится, когда увидит, что пошло по старой. Может быть полезно, да. И удобно. Благодарите.

        Можно ещё звезду на гитхабе поставить https://github.com/WhiteApfel/raiffather

        :return:
        """
        first_transaction: Transaction = None
        page = 0
        while True:
            transactions = await self.transactions(page=page)
            if first_transaction != transactions.list[0]:
                if not first_transaction:
                    first_transaction = transactions.list[0]
                for transaction in transactions.list:
                    yield transaction
                page += 1
            else:
                break
