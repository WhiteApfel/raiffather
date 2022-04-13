from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from raiffather.models.base import TemplatableVerifyInit, VerifyMethod


class InternalTransferDetail(BaseModel):
    src_cba: int = Field(..., alias="srcCba")
    dst_cba: int = Field(..., alias="dstCba")
    amount: float
    rate: int
    client: str


class InternalTransferInit(TemplatableVerifyInit):
    detail: InternalTransferDetail


class InternalTransferExchangeRate(BaseModel):
    currency_source: str = Field(..., alias="currencySource")
    currency_dest: str = Field(..., alias="currencyDest")
    date: datetime
    rate: float
    discount_rate_type: int = Field(..., alias="discountRateType")
    amount_source: float = Field(..., alias="amountSource")
    amount_dest: float = Field(..., alias="amountDest")
