from typing import Literal

from pydantic import BaseModel, Field


class VerifyMethod(BaseModel):
    method: Literal["PUSHOTP", "SMSOTP", "STUBOTP", "E3DSOTP"]


class BaseVerifyInit(BaseModel):
    request_id: str = Field(..., alias="requestId")
    methods: list[VerifyMethod]
    type_id: int = Field(..., alias="typeId")

    @property
    def stub_allowed(self):
        return VerifyMethod(method="STUBOTP") in self.methods


class TemplatableVerifyInit(BaseVerifyInit):
    document: str
    templates_allowed: bool = Field(..., alias="templatesAllowed")
    templates_signed: bool = Field(..., alias="templatesSigned")
