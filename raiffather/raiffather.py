from loguru import logger

from raiffather.modules import *  # noqa: F403

logger.disable("raiffather")


class Raiffather(
    RaiffatherC2C,
    RaiffatherSBP,
    RaiffatherSbpQR,
    RaiffatherTransactions,
    RaiffatherSettings,
    RaiffatherInlineTransfers,
    RaiffatherOther,
    RaiffatherProducts,
):
    ...
