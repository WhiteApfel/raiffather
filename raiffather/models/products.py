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

    def __getitem__(self, item):
        found = []
        if type(item) is int and item < len(self.cards):
            return self.cards[item]

        # id, идентификатор карты в райфе
        if str(item).isdigit() and len(str(item)) == 8:
            for a in self.cards:
                if a.id == int(item):
                    found.append(a)
            if len(found) == 1:
                return found[0]

            # icdb_id, хз что, но тоже, вроде, уникальное и на 8 цифр
            if len(found) == 0:
                for a in self.cards:
                    if a.icdb_id == str(item):
                        found.append(a)
                if len(found) == 1:
                    return found[0]
        elif str(item).isdigit() and len(str(item)) == 4:
            for a in self.cards:
                if a.pan[-4:] == str(item):
                    found.append(a)
            if len(found) == 1:
                return found[0]
        if len(found) == 0 and type(item) is str:  # name, название счёта
            for a in self.cards:
                if a.name == str(item):
                    found.append(a)
            if len(found) == 1:
                return found[0]

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

    def __getitem__(self, item):
        found = []
        if type(item) is int and item < len(self.accounts):
            return self.accounts[item]
        if str(item).isdigit() and len(str(item)) == 20:  # cba, номер счёта
            for a in self.accounts:
                if a.cba == str(item):
                    found.append(a)
            if len(found) == 1:
                return found[0]
        elif (
            str(item).isdigit() and len(str(item)) == 8
        ):  # id, идентификатор счёта в райфе
            for a in self.accounts:
                if a.id == int(item):
                    found.append(a)
            if len(found) == 1:
                return found[0]
        elif (
            str(item).isdigit() and len(str(item)) == 10
        ):  # rma, хз что, но тоже, вроде, уникальное
            for a in self.accounts:
                if a.rma == str(item):
                    found.append(a)
            if len(found) == 1:
                return found[0]
        if len(found) == 0 and type(item) is str:  # name, название счёта
            for a in self.accounts:
                if a.name == str(item):
                    found.append(a)
            if len(found) == 1:
                return found[0]

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
