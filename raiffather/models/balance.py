from typing import Literal

from pydantic import BaseModel
from pydantic.dataclasses import Field


class Currency(BaseModel):
    id: Literal['RUR', 'USD', 'EUR']
    symbol: str
    name: str
    precision: int
    code: str
    short_name: str = Field(..., alias="shortName")
    sort: int


class Balance(BaseModel):
    balance: float
    currency: Currency
