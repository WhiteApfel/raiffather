from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Name(BaseModel):
    name: str


class Currency(BaseModel):
    id: str
    symbol: str
    name: Name
    precision: int
    code: str
    short_name: str = Field(..., alias="shortName")
    sort: int


class BillCurrencyName(BaseModel):
    name: str


class BillCurrency(BaseModel):
    id: str
    symbol: str
    name: BillCurrencyName
    precision: int
    code: str
    short_name: str = Field(..., alias="shortName")
    sort: int


class RelatedName(BaseModel):
    name: str


class RelatedDescription(BaseModel):
    name: str


class AccountType(BaseModel):
    id: int
    name: str


class Amount(BaseModel):
    value: float
    currency_id: str = Field(..., alias="currencyId")
    currency: Currency


class Amount1(BaseModel):
    value: float
    currency_id: str = Field(..., alias="currencyId")
    currency: Currency


class Posting(BaseModel):
    type: str
    title: str
    amount: Amount1


class Payment(BaseModel):
    amount: Amount
    status: str
    source: str
    postings: List[Posting]


class Contact(BaseModel):
    type: str
    number: str


class BankInfo(BaseModel):
    name: str
    logo: str


class Item(BaseModel):
    direction: str
    channel: str
    contact: Contact
    pam: str
    bank_info: BankInfo = Field(..., alias="bankInfo")


class TransferByPhone(BaseModel):
    type: str
    item: Item


class AccountItem(BaseModel):
    cba: str
    role: str


class Accounts(BaseModel):
    type: str
    list: List[AccountItem]


class Relations(BaseModel):
    transfer_by_phone: TransferByPhone = Field(..., alias="transferByPhone")
    accounts: Accounts


class Details(BaseModel):
    type: str
    payment: Payment
    relations: Relations


class Transaction(BaseModel):
    type: str
    date: datetime
    match_date: Optional[datetime] = Field(None, alias="matchDate")
    note: str
    currency_id: str = Field(..., alias="currencyId")
    currency: Currency
    amount: float
    bill_currency_id: str = Field(..., alias="billCurrencyId")
    bill_currency: BillCurrency = Field(..., alias="billCurrency")
    bill_amount: float = Field(..., alias="billAmount")
    relation: str
    related_id: int = Field(..., alias="relatedId")
    related_name: RelatedName = Field(..., alias="relatedName")
    related_description: RelatedDescription = Field(..., alias="relatedDescription")
    account_type: Optional[AccountType] = Field(None, alias="accountType")
    merchant: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    merchant_mcc: Optional[str] = Field(None, alias="merchantMcc")
    merchant_logo_id: Optional[str] = Field(None, alias="merchantLogoId")
    details: Optional[Details] = None

    def __add__(self, other):
        if type(other) is Transaction:
            return Transactions(list=[self, other])


class Transactions(BaseModel):
    list: List[Transaction]

    def __add__(self, other):
        new_transactions = Transactions(list=self.list)
        if type(other) is Transactions or all([type(i) is Transaction for i in other]):
            new_transactions.list.extend(other)
            return new_transactions

    def __iter__(self):
        return iter(self.list)

    def __len__(self):
        return len(self.list)
