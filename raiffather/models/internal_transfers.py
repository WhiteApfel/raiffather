from typing import Literal

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
