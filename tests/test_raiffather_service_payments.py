from os import environ

import pytest

from raiffather import Raiffather


@pytest.mark.asyncio
async def test_raif_top_up_mobile_account():
    r = Raiffather(environ.get("RAIF_USER"), environ.get("RAIF_PASSWD"))
    async with r:
        max_balance_card = sorted(r.products.cards)[-1]
        provider_info = await r.top_up_mobile_account_get_provider_info("9301048477")
        verify_init = await r.top_up_mobile_account_init(
            phone_number="9301048477",
            amount=provider_info.min_amount,
            card=max_balance_card,
            provider_id=provider_info.id,
        )
        push_id = await r.top_up_mobile_account_send_push(verify_init.request_id)
        code = await r.wait_code(push_id)
        assert await r.top_up_mobile_account_verify(verify_init.request_id, code)
