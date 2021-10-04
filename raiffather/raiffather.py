from loguru import logger

from raiffather.modules import *

logger.disable("raiffather")


class Raiffather(
    RaiffatherC2C,
    RaiffatherSBP,
    RaiffatherSbpQR,
    RaiffatherTransactions,
    RaiffatherSettings,
    RaiffatherInlineTransfers,
    RaiffatherOther
):
    ...
