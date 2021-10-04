from loguru import logger

from raiffather.modules import *

logger.disable("raiffather")


class Raiffather(
    RaiffatherC2C,
    RaiffatherSBP,
    RaiffatherTransactions,
    RaiffatherSettings,
    RaiffatherInlineTransfers,
    RaiffatherOther
):
    ...
