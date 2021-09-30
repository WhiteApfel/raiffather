from pydantic import BaseModel, Field

from raiffather.models.balance import Currency


class SbpBankChannel(BaseModel):
    id: int
    name: str


class SbpBankLogo(BaseModel):
    url: str = Field("/none")


class SbpBank(BaseModel):
    id: str = Field(..., alias="bankId")
    name: str
    channel: SbpBankChannel
    priority: bool
    default: bool = Field(..., alias="defaultSbp")
    logo: SbpBankLogo


class SbpPamLimits(BaseModel):
    max_amount: int = Field(..., alias="maxAmount")
    min_amount: int = Field(..., alias="minAmount")
    currency: Currency


class SbpPam(BaseModel):
    recipient: str
    limits: SbpPamLimits


class SbpCommission(BaseModel):
    commission: int


class SbpInitDetail(BaseModel):
    src_cba: str = Field(..., alias="srcCba")
    phone: str
    bank_id: str = Field(..., alias="bankId")
    amount: float
    commission: str
    recipient: str
    message: str
    bank_name: str = Field(..., alias="bankName")
    channel: str
    client: str


class SbpInit(BaseModel):
    request_id: str = Field(..., alias="requestId")
    type_id: str = Field(..., alias="typeId")
    detail: SbpInitDetail
    document: str


class SbpSettings(BaseModel):
    cba: str
    allow_transferred: bool = Field(..., alias="allowTransferred")
    default_bank: bool = Field(..., alias="defaultBank")
