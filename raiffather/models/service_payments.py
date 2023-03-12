from pydantic import BaseModel, Field, validator

from raiffather.models.base import TemplatableVerifyInit
from raiffather.models.products import BaseVerifyInit


class TopUpMobileAccountProviderInfo(BaseModel):
    id: int
    name: str
    short_name: str = Field(..., alias="shortName")
    clearing_operator_id: int = Field(..., alias="clearingOperatorId")
    active: bool
    min_amount: float = Field(..., alias="minAmount")
    max_amount: float = Field(..., alias="maxAmount")
    parameters: list
    scan_code_available: bool = Field(..., alias="scanCodeAvailable")

    @validator("name", pre=True)
    def improve_name(cls, pre_name):
        return pre_name["name"]

    @validator("short_name", pre=True)
    def improve_short_name(cls, pre_short_name):
        return pre_short_name["name"]


class TopUpMobileAccountVerify(TemplatableVerifyInit):
    detail: dict
