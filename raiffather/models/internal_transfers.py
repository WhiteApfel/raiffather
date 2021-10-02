from typing import Literal
from datetime import datetime

from pydantic import BaseModel, Field


class InternalTransactionMethod(BaseModel):
    method: Literal['PUSHOTP', 'SMSOTP', 'STUBOTP']


class InternalTransactionDetail(BaseModel):
    src_cba: int = Field(..., alias="srcCba")
    dst_cba: int = Field(..., alias="dstCba")
    amount: float
    rate: int
    client: str


class InternalTransactionInit(BaseModel):
    request_id: int = Field(..., alias="requestId")
    methods: list[InternalTransactionMethod]
    detail: InternalTransactionDetail
    document: str
    type_id: int

    @property
    def stub_allowed(self):
        return InternalTransactionMethod(method='STUBOTP') in self.methods


class InternalTransactionExchangeRate(BaseModel):
    currency_source: str = Field(..., alias="currencySource")
    currency_dest: str = Field(..., alias="currencyDest")
    date: datetime
    rate: float
    discount_rate_type: int = Field(..., alias="discountRateType")
    amount_source: float = Field(..., alias="amountSource")
    amount_dest: float = Field(..., alias="amountDest")
