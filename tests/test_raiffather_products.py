from os import environ

import pytest

from raiffather import Raiffather
from raiffather.exceptions.base import RaifIncrorrectRequest


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
        for account in products.accounts.business:
            assert account.type_id == "BUSINESS"
            assert not account.rma


@pytest.mark.asyncio
async def test_raif_cards():
    async with Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD")) as r:
        products = await r.get_products()
        for card in products.cards:
            assert card == products.cards[card.id]
            assert card == products.cards[card.icdb_id]
            assert card == products.cards[card.pan[-4:]]
            if card.name:
                assert card == products.cards[card.name]


@pytest.mark.asyncio
async def test_raif_cards_details():
    async with Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD")) as r:
        products = await r.get_products()
        for card in products.cards:
            card_details = await r.get_card_details(card)
            assert card.pan[:6] == card_details.number[:6]
            assert card.pan[-4:] == card_details.number[-4:]


@pytest.mark.asyncio
async def test_raif_change_card_pin():
    async with Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD")) as r:
        products = await r.get_products()
        for card in products.cards:
            await r.change_card_pin(card, 7898)
