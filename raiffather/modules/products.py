from loguru import logger

from raiffather.models.products import Card
from raiffather.modules.base import RaiffatherBase

logger.disable("raiffather")


class RaiffatherProducts(RaiffatherBase):
    async def get_card_details(self, card: Card):
        logger.debug("Get card details...")
        ...
