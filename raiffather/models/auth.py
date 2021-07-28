from pydantic.dataclasses import Field
from pydantic import BaseModel
from datetime import datetime, date


class ResponseOwner(BaseModel):
    branch_id: int = Field(..., alias='branchId')
    category_id: int = Field(..., alias='categoryId')
    segment_id: int = Field(..., alias='segmentId')
    first_name: str = Field(..., alias='firstName')
    last_name: str = Field(..., alias='lastName')
    patronymic: str
    translit_name: str = Field(..., alias='translitName')
    birth_date: date = Field(..., alias='birthDate')
    email: str
    mobile_phone: str = Field(..., alias='mobilePhone')
    address: str
    inn: str
    resident: bool
    compliance: str = bool
    region_id: int = Field(..., alias='regionId')
    passport_number: str = Field(..., alias='passportNumber')
    passport_issuer: str = Field(..., alias='passportIssuer')
    passport_date: datetime = Field(..., alias='passportDate')
    gender: str
    birth_place: str = Field(..., alias='birthPlace')
    passport_issuer_code: str = Field(..., alias='passportIssuerCode')
    actual_address: str = Field(..., alias='actualAddress')


class OauthResponse(BaseModel):
    access_token: str
    expires_in: int
    resource_owner: ResponseOwner
    password_expires_in: datetime

