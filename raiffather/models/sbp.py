from fuzzywuzzy import process
from pydantic import BaseModel, Field
from typing import Iterator, Optional

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


class SbpBanks(BaseModel):
    list: list[SbpBank]

    def __iter__(self) -> Iterator[SbpBank]:
        return iter(self.list)

    def __getitem__(self, item) -> Optional[SbpBank]:
        if str(item).isdigit():  # search by id
            return process.extractOne(str(item), [b.id for b in self.list])[0]
        elif type(item) is str:  # search by name
            return process.extractOne(item, [b.name for b in self.list])[0]


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
    allow_transfers: bool = Field(..., alias="allowTransfers")
    default_bank: bool = Field(..., alias="defaultBank")
