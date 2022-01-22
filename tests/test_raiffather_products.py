from os import environ

import asyncio
import pytest

from raiffather import Raiffather
from raiffather.exceptions.base import RaifUnauthorized
from raiffather.models.balance import Balance


@pytest.mark.asyncio
async def test_raif_accounts():
    async with Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD")) as r:
        products = await r.get_products()
        for account in products.accounts:
            assert account == products.accounts[account.cba]
            assert account == products.accounts[account.id]
            if account.rma:
                assert account == products.accounts[account.rma]
            if account.name:
                assert account == products.accounts[account.name]


@pytest.mark.asyncio
async def test_raif_accounts_dollars():
    async with Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD")) as r:
        products = await r.get_products()
        for account in products.accounts.dollars:
            assert account.currency.code == "840"


@pytest.mark.asyncio
async def test_raif_accounts_euros():
    async with Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD")) as r:
        products = await r.get_products()
        for account in products.accounts.euros:
            assert account.currency.code == "978"


@pytest.mark.asyncio
async def test_raif_accounts_business():
    async with Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD")) as r:
        products = await r.get_products()
        for account in products.accounts.business.accounts:
            assert account.type_id == "BUSINESS"
            assert not account.rma
