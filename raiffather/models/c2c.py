from typing import Literal

from pydantic import BaseModel, Field


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
    details: str
    template_allowed: bool = Field(..., alias="templateAllowed")
    template_signed: bool = Field(..., alias="templateSigned")


class E3DSOTPData(BaseModel):
    wait: int = Field(..., alias="await")
    acs_url: str = Field(..., alias="acs_url")
    pareq: str
