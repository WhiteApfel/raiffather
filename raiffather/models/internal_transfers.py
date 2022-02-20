from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class VerifyMethod(BaseModel):
    method: Literal["PUSHOTP", "SMSOTP", "STUBOTP"]


class InternalTransferDetail(BaseModel):
    src_cba: int = Field(..., alias="srcCba")
    dst_cba: int = Field(..., alias="dstCba")
    amount: float
    rate: int
    client: str


class InternalTransferInit(BaseModel):
    request_id: int = Field(..., alias="requestId")
    methods: list[VerifyMethod]
    detail: InternalTransferDetail
    document: str
    type_id: int = Field(..., alias="typeId")

    @property
    def stub_allowed(self):
        return VerifyMethod(method="STUBOTP") in self.methods


class InternalTransferExchangeRate(BaseModel):
    currency_source: str = Field(..., alias="currencySource")
    currency_dest: str = Field(..., alias="currencyDest")
    date: datetime
    rate: float
    discount_rate_type: int = Field(..., alias="discountRateType")
    amount_source: float = Field(..., alias="amountSource")
    amount_dest: float = Field(..., alias="amountDest")
