class RaifException(Exception):
    __module__ = "raiffather"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifErrorResponse(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifUnauthorized(RaifErrorResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifDeviceNotVerify(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifError3DS(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifProductNotFound(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifPasswordDeprecated(RaifErrorResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
