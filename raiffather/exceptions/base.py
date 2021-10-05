class RaifException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifErrorResponse(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifUnauthorized(RaifException):
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


class RaifPasswordDeprecated(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
