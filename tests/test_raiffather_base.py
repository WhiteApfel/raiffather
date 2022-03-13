import asyncio
from os import environ

import pytest

from raiffather import Raiffather
from raiffather.exceptions.base import RaifUnauthorized
from raiffather.models.balance import Balance


def test_raif_init():
    Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))


@pytest.mark.asyncio
async def test_raif_balance():
    r = Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))
    async with r:
        balance = await r.balance()
        assert type(balance) is list
        for b in balance:
            assert type(b) is Balance


@pytest.mark.asyncio
@pytest.mark.parametrize("wait", [0, 0.25, 0.5, 1, 5])
async def test_raif_task_0s(wait):
    r = Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))
    async with r:
        await asyncio.sleep(wait)


@pytest.mark.asyncio
async def test_raif_unauthorized():
    with pytest.raises(RaifUnauthorized):
        async with Raiffather("example", "example"):
            ...
