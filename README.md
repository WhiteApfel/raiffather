# Raiffather
Враппер апишки Райффайзенбанка из их мобильного приложения

### Введение

Предоставляется как есть, ``as is``, за финансовые, моральные и прочие вариации потерь 
от использования ответственность не несу, она целиком и полностью ложится на ваши плечи. 
Код может содержать баги, изъяны и прочие недостатки, являющиеся следствием
одного из процессов жизнедеятельности моего несовершенного мозга. 

Мне было нечем заняться, поэтому я решил побаловаться с автоматизацией своих 
рутинных процессов в моём нынеосновном банке. 

Старался взять всё прекрасное из мейнстримовых библиотек и сделать удобную красоту.
Получилось? Кажется, немного.

### Возможности Райффазера

- [x] Получение пуш-уведомлений как в настоящем приложении
- [x] Регистрация устройства для подтверждения операций
- [x] Общий баланс по курсу ЦБ в рублях
- [x] Список счетов и привязанных к ним карт
- [ ] Уведомления из разряда технических работ или сбоев
- [x] Переводы по СБП
- [ ] Переводы между счетами
- [ ] Обмен валюты
- [ ] Переводы по номеру карты
- [ ] Переводы по реквизитам
- [ ] Переводы/оплата по QR коду
- [ ] Оплата услуг
- [ ] Штрафы, платежи в бюджет
- [ ] Чат поддержки
- [ ] Справки и документы
- [ ] Настройка переводов по СБП
- [ ] Адреса банкоматов
- [ ] Курсы валют
- [ ] Управление персональными данными

## Как устанавливать?

Если доверяете мне или можете проверить код в site_packages 
(*пока что не работает, ибо ещё не залил в pypi*)

```shell
python -m pip install raiffather
```

Если не сильно доверяете мне и не хотите проверять код в site_packages, 
но проверили его в репозитории

```shell
python -m pip install git+git@github.com:WhiteApfel/raiffather.git
```

Если не доверяете мне и коду

```
Наденьте шапочку из фальги и свинцовый жилет, а то я уже облучаю вашу светлую голову 5G лучшами
```

## Как пользоваться?

```python
from raiffather import Raiffather

raif = Raiffather('username', 'password')

async def main():
    async with raif:
        request_id = await raif.register_device()
        code = input("SMS code >>> ")
        await raif.register_device_verify(request_id, code)
```

```python
from raiffather import Raiffather

raif = Raiffather('username', 'password')

async def main():
    async with raif:
        await raif.sbp("79991398805", "Точка", 22.8, "Благодарность за библиотеку")
```

```python
from raiffather import Raiffather

raif = Raiffather('username', 'password')

async def main():
    async with raif:
        cba = (await raif.sbp_settings()).cba
        await raif.sbp_prepare()
        banks = await raif.sbp_banks(phone="79991398805", cba=cba)
        bank_name = raif.sbp_bank_fuzzy_search([b.name for b in banks], "Точка")
        bank = next((bank for bank in banks if bank.name == bank_name), None)
        if bank:
            pam = await raif.sbp_pam(bank_id=bank.id, phone="79991398805", cba=cba)
            com = float(
                (
                    await raif.sbp_commission(
                        bank=bank.id, phone="79991398805", amount=float(22), cba=cba
                    )
                ).commission
            )
            init = await raif.sbp_init(float(22), bank.id, "79991398805", "Благодарность за либу", cba)
            code = await raif.sbp_send_push(init.request_id)
            success = await raif.sbp_push_verify(init.request_id, code)
```

```python
from raiffather import Raiffather

raif = Raiffather('username', 'password')

async def main():
    async with raif:
        transactions = raif.global_history_generator()
        async for transaction in transactions:
            print(transaction)
```