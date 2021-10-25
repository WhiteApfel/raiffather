from os import environ

import asyncio
import pytest

from raiffather import Raiffather
from raiffather.exceptions.base import RaifUnauthorized
from raiffather.models.balance import Balance


def test_raif_init():
    r = Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))


@pytest.mark.asyncio
async def test_raif_balance():
    r = Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))
    async with r:
        balance = await r.balance()
        assert type(balance) is list
        for b in balance:
            assert type(b) is Balance


@pytest.mark.asyncio
async def test_raif_empty_with():
    r = Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))
    async with r:
        ...


@pytest.mark.asyncio
async def test_raif_unauthorized():
    with pytest.raises(RaifUnauthorized) as unauthorised:
        async with Raiffather("example", "example") as r:
            ...
