from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, validator
from pydantic.dataclasses import Field

from raiffather.exceptions.base import RaifFoundMoreThanOneProduct, RaifProductNotFound
from raiffather.models.balance import Currency


class Account(BaseModel):
    id: int
    procuration_credentials: dict = Field(..., alias="procurationCredentials")
    alien: bool
    cba: str
    rma: Optional[str]
    name: Optional[str]
    type: str
    type_id: str = Field(..., alias="typeId")
    status: str
    status_id: str = Field(..., alias="statusId")
    balance: Optional[float]
    hold: Optional[float]
    open: date
    credit_block: Optional[bool] = Field(None, alias="creditBlock")
    debit_block: Optional[bool] = Field(None, alias="debitBlock")
    currency: Currency
    favorite: bool
    lpc: Optional[str]
    gpc: Optional[str]
    rates: Optional[list]

    def __lt__(self, other):
        if type(other) is Account:
            return self.balance < other.balance
        if type(other) in [int, float]:
            return self.balance < other
        raise ValueError(
            f"Objects are compared by balance. "
            f"Cannot be compared to anything other than a int, float or other Account instance"
        )


class Card(BaseModel):
    id: int
    procuration_credentials: dict = Field(..., alias="procurationCredentials")
    account: Optional[Account]
    alien: bool
    icdb_id: int = Field(..., alias="icdbId")
    main: str
    main_id: str = Field(..., alias="mainId")
    name: Optional[str]
    pan: str
    balance: float
    hold: float
    expire: date
    open: date
    product: str
    type_id: str = Field(..., alias="typeId")
    lpc: str
    gpc: str
    cashback_balance: Optional[float] = Field(None, alias="cashbackBalance")
    cashback_currency: Optional[str] = Field(None, alias="cashbackCurrency")
    status: str
    status_id: str = Field(..., alias="statusId")
    cardholder: str
    payment_system: str = Field(..., alias="paymentSystem")
    settings: dict
    favorite: bool

    def __lt__(self, other):
        if type(other) is Card:
            return self.balance < other.balance
        if type(other) in [int, float]:
            return self.balance < other
        raise ValueError(
            f"Objects are compared by balance. "
            f"Cannot be compared to anything other than a int, float or other Card instance"
        )


class Cards(BaseModel):
    cards: list[Card]

    def get_by_id(self, card_id):
        return [c for c in self.cards if c.id == int(card_id)]

    def get_by_icdb_id(self, icdb_id):
        return [c for c in self.cards if c.icdb_id == str(icdb_id)]

    def get_by_last_digits(self, last_digits):
        return [c for c in self.cards if c.pan[-4:] == str(last_digits)[-4:]]

    def get_by_name(self, name):
        return [c for c in self.cards if c.name == str(name)]

    def __getitem__(self, item):
        found = []
        if type(item) is int and item < len(self.cards):
            return self.cards[item]

        # id, идентификатор карты в райфе
        if str(item).isdigit() and len(str(item)) == 8:
            cards = self.get_by_id(item)
            if len(cards) == 1:
                return cards[0]
            found.extend(cards)

            # icdb_id, хз что, но тоже, вроде, уникальное и на 8 цифр
            if len(cards) == 0:
                cards = self.get_by_icdb_id(item)
                if len(cards) == 1:
                    return cards[0]
                found.extend(cards)
        elif str(item).isdigit() and len(str(item)) == 4:
            cards = self.get_by_last_digits(item)
            if len(cards) == 1:
                return cards[0]
            found.extend(cards)
        if len(found) == 0 and type(item) is str:  # name, название счёта
            cards = self.get_by_name(item)
            if len(cards) == 1:
                return cards[0]
            found.extend(cards)

        if found:
            raise RaifFoundMoreThanOneProduct(item, found, self.cards)
        raise RaifProductNotFound(item, self.cards)

    @property
    def visa(self):
        return Cards(cards=[c for c in self.cards if c.payment_system == "Visa"])

    @property
    def mastercard(self):
        return Cards(cards=[c for c in self.cards if c.payment_system == "MasterCard"])


class Accounts(BaseModel):
    accounts: list[Account]

    def get_by_id(self, account_id):
        return [a for a in self.accounts if a.id == int(account_id)]

    def get_by_cba(self, cba):
        return [a for a in self.accounts if a.cba == str(cba)]

    def get_by_rma(self, rma):
        return [a for a in self.accounts if a.rma == str(rma)]

    def get_by_name(self, name):
        return [a for a in self.accounts if a.id == str(name)]

    def __getitem__(self, item):
        found = []
        if type(item) is int and item < len(self.accounts):
            return self.accounts[item]
        if str(item).isdigit() and len(str(item)) == 20:  # cba, номер счёта
            accounts = self.get_by_cba(item)
            if len(accounts) == 1:
                return accounts[0]
            found.extend(accounts)
        elif (
            str(item).isdigit() and len(str(item)) == 8
        ):  # id, идентификатор счёта в райфе
            accounts = self.get_by_id(item)
            if len(accounts) == 1:
                return accounts[0]
            found.extend(accounts)
        elif (
            str(item).isdigit() and len(str(item)) == 10
        ):  # rma, хз что, но тоже, вроде, уникальное
            accounts = self.get_by_rma(item)
            if len(accounts) == 1:
                return accounts[0]
            found.extend(accounts)
        if len(found) == 0 and type(item) is str:  # name, название счёта
            accounts = self.get_by_name(item)
            if len(accounts) == 1:
                return accounts[0]
            found.extend(accounts)

        if found:
            raise RaifFoundMoreThanOneProduct(item, found, self.accounts)
        raise RaifProductNotFound(item, self.accounts)

    def __len__(self):
        return len(self.accounts)

    def __iter__(self):
        for a in self.accounts:
            yield a

    @property
    def business(self):
        return Accounts(accounts=[a for a in self.accounts if a.type_id == "BUSINESS"])

    @property
    def current(self):
        return Accounts(accounts=[a for a in self.accounts if a.type_id == "CURRENT"])

    @property
    def rubles(self):
        return Accounts(accounts=[a for a in self.accounts if a.currency.id == "RUR"])

    @property
    def dollars(self):
        return Accounts(accounts=[a for a in self.accounts if a.currency.id == "USD"])

    @property
    def euros(self):
        return Accounts(accounts=[a for a in self.accounts if a.currency.id == "EUR"])


class Products(BaseModel):
    cards: Cards = Field(..., alias="card")
    accounts: Accounts = Field(..., alias="account")

    @validator("accounts", pre=True)
    def validators_accounts_pre(cls, v):
        return Accounts(accounts=v)

    @validator("cards", pre=True)
    def validators_cards_pre(cls, v):
        return Cards(cards=v)
