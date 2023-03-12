import asyncio
from os import environ

import pytest

from raiffather import Raiffather


@pytest.mark.asyncio
async def test_raif_top_up_mobile_account():
    r = Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))
    async with r:
        print(await r.change_card_pin(card=r.products.cards[1].id, pin="7195"))
        await asyncio.sleep(2)


asyncio.run(test_raif_top_up_mobile_account())
