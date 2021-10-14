from typing import Literal, Optional

from pydantic import BaseModel, Field, validator

from raiffather.exceptions.base import RaifFoundMoreThanOneProduct, RaifProductNotFound
from raiffather.models.products import Card


class C2cInitMethod(BaseModel):
    method: Literal["E3DSOTP"]


class C2cInitDetailsMoney(BaseModel):
    sum: float
    currency: int


class C2cInitDetails(BaseModel):
    src_card: str = Field(..., alias="srcCard")
    dst_card: str = Field(..., alias="dstCard")
    amount: C2cInitDetailsMoney
    src_amount: C2cInitDetailsMoney = Field(..., alias="srcAmount")
    dst_amount: C2cInitDetailsMoney = Field(..., alias="dstAmount")
    comission_amount: C2cInitDetailsMoney


class C2cInit(BaseModel):
    request_id: str = Field(..., alias="requestId")
    operation_type: int = Field(..., alias="operationType")
    document: str
    methods: list[C2cInitMethod]
    details: dict
    templates_allowed: bool = Field(..., alias="templatesAllowed")
    templates_signed: bool = Field(..., alias="templatesSigned")


class E3DSOTPData(BaseModel):
    wait: int = Field(..., alias="await")
    acs_url: str = Field(..., alias="acsUrl")
    pareq: str


class C2cTpcOne(BaseModel):
    id: int
    name: str
    bin: int
    last_digits: int = Field(..., alias="lastDigits")
    active: bool
    payment_system: str = Field(..., alias="paymentSystem")


class C2cCashLimit(BaseModel):
    left_day: float = Field(..., alias="leftDay")
    left_month: float = Field(..., alias="leftMonth")


class C2cCard(BaseModel):
    card: Card
    cash_limit: C2cCashLimit = Field(..., alias="cashLimit")


class C2cCards(BaseModel):
    cards: list[C2cCard]

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        for a in self.cards:
            yield a

    def __getitem__(self, item):
        found = []
        if type(item) is int and item < len(self.cards):
            return self.cards[item]
        if len(str(item)) == 8:
            for c in self.cards:
                if c.card.id == int(item):
                    found.append(c)
            if len(found) == 1:
                return found[0]
        elif len(str(item)) == 4:
            for c in self.cards:
                if c.card.pan[-4:] == str(item):
                    found.append(c)
            if len(found) == 1:
                return found[0]
        if len(found) == 0 and type(item) is str:
            for c in self.cards:
                if c.card.name == str(item):
                    found.append(c)
            if len(found) == 1:
                return found[0]

        if found:
            raise RaifFoundMoreThanOneProduct(item, found, self.cards)
        raise RaifProductNotFound(item, self.cards)


class C2cTpc(BaseModel):
    cards: list[C2cTpcOne]

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        for a in self.cards:
            yield a

    def __getitem__(self, item):
        found = []
        if type(item) is int and item < len(self.cards):
            return self.cards[item]
        if len(str(item)) == 6:
            for c in self.cards:
                if c.id == int(item):
                    found.append(c)
            if len(found) == 1:
                return found[0]
        elif len(str(item)) == 4:
            for c in self.cards:
                if c.last_digits == int(item):
                    found.append(c)
            if len(found) == 1:
                return found[0]
        if len(found) == 0 and type(item) is str:
            for c in self.cards:
                if c.name == str(item):
                    found.append(c)
            if len(found) == 1:
                return found[0]

        if found:
            raise RaifFoundMoreThanOneProduct(item, found, self.cards)
        raise RaifProductNotFound(item, self.cards)

    @property
    def visa(self):
        return C2cTpc(cards=[c for c in self.cards if c.payment_system == "Visa"])

    @property
    def mastercard(self):
        return C2cTpc(cards=[c for c in self.cards if c.payment_system == "MasterCard"])


class C2cRetrieve(BaseModel):
    cards_ext: C2cCards = Field(..., alias="cardsExt")
    tpc: C2cTpc
    disabled_bins_for_c2c: list[int] = Field(..., alias="disabledBinsForC2C")
    us_bins: list[int] = Field(..., alias="usBins")

    @validator("cards_ext", pre=True)
    def validators_cards_ext_pre(cls, v):
        return C2cCards(cards=v)

    @validator("tpc", pre=True)
    def validators_tpc_pre(cls, v):
        return C2cTpc(cards=v)


class C2cNewCard(BaseModel):
    number: str = Field(..., alias="pan")
    expiry: Optional[str]
    cvv: Optional[str]
    name: Optional[str]
    add_to_list: bool = Field(False, alias="addToList")


class BinInfoPaymentSystem(BaseModel):
    id: str
    name: str


class BinInfoName(BaseModel):
    name: str


class BinInfoLetter(BaseModel):
    name: str


class BinInfo(BaseModel):
    bin: str
    country: str
    is_delayed: bool = Field(..., alias="isDelayed")
    payment_system: BinInfoPaymentSystem = Field(..., alias="paymentSystem")
    name: BinInfoName
    letter: BinInfoLetter
    color: str
    is_rb_group: bool = Field(..., alias="isRbGroup")
    is_rb_russia: bool = Field(..., alias="isRbRussia")
