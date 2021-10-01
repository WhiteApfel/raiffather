from typing import Literal

from pydantic import BaseModel, Field

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


class C2cTpc(BaseModel):
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


class C2cRetrieve(BaseModel):
    cards_ext: list[C2cCard] = Field(..., alias="cardsExt")
    tpc: list[C2cTpc]
    disabled_bins_for_c2c: list[int] = Field(..., alias="disabledBinsForC2C")
    us_bins: list[int] = Field(..., alias="usBins")
