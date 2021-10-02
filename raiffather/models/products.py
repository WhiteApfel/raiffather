from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, validator
from pydantic.dataclasses import Field

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
    balance: float
    hold: Optional[float]
    open: date
    credit_block: Optional[bool] = Field(None, alias="creditBlock")
    debit_block: Optional[bool] = Field(None, alias="debitBlock")
    currency: Currency
    favorite: bool
    lpc: Optional[str]
    gpc: Optional[str]
    rates: Optional[list]


class Card(BaseModel):
    id: int
    procuration_credentials: dict = Field(..., alias="procurationCredentials")
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


class Accounts(BaseModel):
    accounts: list[Account]

    def __getitem__(self, item):
        if len(str(item)) == 20:  # cba, номер счёта
            for a in self.accounts:
                if a.cba == str(item):
                    return item
        elif len(str(item)) == 8:  # id, идентификатор счёта в райфе
            for a in self.accounts:
                if a.id == int(item):
                    return item
        elif len(str(item)) == 10:  # rma, хз что, но тоже, вроде, уникальное
            for a in self.accounts:
                if a.rma == str(item):
                    return item
        elif type(item) is str:  # name, название счёта
            for a in self.accounts:
                if a.name == str(item):
                    return item
        else:
            raise KeyError(f"Not found {item} in accounts ({len(self.accounts)})")


class Products(BaseModel):
    cards: list[Card] = Field(..., alias="card")
    accounts: Accounts = Field(..., alias="account")

    @validator('accounts', pre=True)
    def validators_accounts_pre(cls, v):
        return Accounts(accounts=v)
