from raiffather.exceptions.base import RaifException


class SBPRecipientNotFound(RaifException):
    __module__ = "Raiffather"

    def __init__(self, message):
        super().__init__(message)

    def __str__(self):
        return ""

    def __repr__(self):
        return ""
