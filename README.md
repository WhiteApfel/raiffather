# Raiffather
Враппер апишки Райффайзенбанка из их мобильного приложения

[![CodeFactor](https://www.codefactor.io/repository/github/whiteapfel/raiffather/badge/main)](https://www.codefactor.io/repository/github/whiteapfel/raiffather/overview/main)
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FWhiteApfel%2Fraiffather.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2FWhiteApfel%2Fraiffather?ref=badge_shield)
[![DeepSource](https://deepsource.io/gh/WhiteApfel/raiffather.svg/?label=active+issues&show_trend=true&token=YEVqOQuUg7C6E3vweLGD883l)](https://deepsource.io/gh/WhiteApfel/raiffather/?ref=repository-badge)
[![Updates](https://pyup.io/repos/github/WhiteApfel/raiffather/shield.svg)](https://pyup.io/repos/github/WhiteApfel/raiffather/)
[![Python 3](https://pyup.io/repos/github/WhiteApfel/raiffather/python-3-shield.svg)](https://pyup.io/repos/github/WhiteApfel/raiffather/)

### Введение

Предоставляется как есть, ``as is``, за финансовые, моральные и прочие вариации потерь 
от использования ответственность не несу, она целиком и полностью ложится на ваши плечи. 
Код может содержать баги, изъяны и прочие недостатки, являющиеся следствием
одного из процессов жизнедеятельности моего несовершенного мозга. 

Мне было нечем заняться, поэтому я решил побаловаться с автоматизацией своих 
рутинных процессов в моём ныне основном банке. 

Старался взять всё прекрасное из мейнстримовых библиотек и сделать удобную красоту.
Получилось? Кажется, немного.

### Возможности Райффазера

- [x] Получение пуш-уведомлений как в настоящем приложении
- [x] Регистрация устройства для подтверждения операций
- [x] Общий баланс по курсу ЦБ в рублях
- [x] Список счетов и привязанных к ним карт
- [x] Уведомления из разряда технических работ или сбоев
- [x] Управление картой
  - [x] Просмотр реквизитов
  - [x] Смена пин-кода
  - [ ] Блокировка карты
  - [ ] Получение кешбэка
  - [ ] Уведомления по операциям
  - [ ] Переименовка карты
  - [ ] Получение тарифа
- [ ] Управление счётом
  - [ ] Переименовать счёт
  - [ ] Закрыть счёт
- [x] Переводы по СБП
  - [x] c2c
  - [ ] me2me
  - [ ] c2b
- [x] Переводы между счетами
  - [x] В одной валюте
  - [x] В разной валюте
  - [ ] Со счёта или на счёт ИП
- [x] Обмен валюты
- [x] Переводы по номеру карты
  - [x] Отправка внутри банка
  - [x] Отправка в другие банки
  - [x] Получение внутри банка
  - [x] Получение из другого банка
- [ ] Переводы по реквизитам
  - [ ] Физ лицам
  - [ ] Юр лицам
  - [ ] Государству
- [x] Оплата по QR коду (СБП)
- [ ] Оплата услуг
  - [ ] Пополнение баланса номера телефона
  - [ ] Вывод на электронные кошельки
    - [ ] Киви
    - [ ] Юмани
  - [ ] Интернет и телефония
  - [ ] Транспорт
  - [ ] Телевидение
  - [ ] ЖКХ
- [ ] Штрафы, платежи в бюджет
  - [ ] По УИН
  - [ ] Подписка по ИНН/СНИЛС/Права/Единый лицевой счёт
- [ ] Чат поддержки
  - [ ] Эскорт истории диалога
  - [ ] Отправка сообщений
  - [ ] Отправка файлов
- [ ] Справки и документы
  - [ ] Счета 
    - [ ] О наличии счёта(ов) с балансом
    - [ ] О наличии счёта(ов) без баланса
    - [ ] О закрытии счёта
  - [ ] Кредит
    - [ ] О задолженности
    - [ ] О полном погашении
    - [ ] О процентах за пользование
    - [ ] Для маткапитала в ПФР
    - [ ] О задолженности по решению суда/судебному приказу/исполнительной надписи нотариуса
  - [ ] Кредитная карта
    - [ ] О кредитном лимите
    - [ ] О закрытии счёта кредитной карты
    - [ ] О задолженности по решению суда/судебному приказу/исполнительной надписи нотариуса
  - [ ] Об отсутствии кредитных обязательств
  - [ ] О наличии депозита
- [x] Настройка переводов по СБП
- [ ] Адреса банкоматов
  - [ ] Банки партнёры
  - [ ] Поиск ближайших к точке
  - [ ] Фильтры
  - [ ] Список всех для города 
- [ ] Курсы валют
- [ ] Управление персональными данными
- [ ] Открытие новых продуктов
  - [ ] Дебетовые карты
    - [ ] Виртуальные
    - [ ] Пластиковые
  - [ ] Расчётные счета
  - [ ] Накопительные счета
  - [ ] Вклады

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
Наденьте шапочку из фольги и свинцовый жилет, а то я уже облучаю вашу светлую голову 5G лучами
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
