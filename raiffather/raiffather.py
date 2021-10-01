from raiffather.modules import *
from loguru import logger

logger.disable("raiffather")


class Raiffather(
    RaiffatherC2C, RaiffatherSBP, RaiffatherTransactions, RaiffatherSettings
):
    ...
