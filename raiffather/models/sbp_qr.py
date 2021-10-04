from pydantic import BaseModel, Field

from raiffather.models.internal_transfers import VerifyMethod


class SbpQRData(BaseModel):
    bank_id: str
    crc: str
    type: str
    qrc: str

    @property
    def qrc_type(self):
        return "QRStat" if self.type == "01" else "QRDin"


class SbpQRInitDetail(BaseModel):
    src_cba: str = Field(..., alias="srcCba")
    bank_id: str = Field(..., alias="bankId")
    qrc_id: str = Field(..., alias="qrcId")
    qrc_type: str = Field(..., alias="qrcType")
    amount: float
    payment_purpose: str = Field(..., alias="paymentPurpose")
    date: str


class SbpQRInit(BaseModel):
    detail: SbpQRInitDetail
    document: str
    methods: list[VerifyMethod]
    type_id: int = Field(..., alias="typeId")
    request_id: int = Field(..., alias="requestId")
    templates_allowed: bool = Field(..., alias="templatesAllowed")
    template_signed: bool = Field(..., alias="templateSigned")


class SbpQrInfoObject(BaseModel):
    qrc_id: str = Field(..., alias="qrcId")
    qrc_type: str = Field(..., alias="qrcType")
    amount: float
    currency: str
    payment_purpose: str = Field(..., alias="paymentPurpose")
    legal_name: str = Field(..., alias="legalName")
    brand_name: str = Field(..., alias="brandName")
    address: str
    member_id: str = Field(..., alias="memberId")
    crc: str
    mcc: str
    limits: dict


class SbpQrInfo(BaseModel):
    type_id: str = Field(..., alias="typeId")
    object: SbpQrInfoObject
