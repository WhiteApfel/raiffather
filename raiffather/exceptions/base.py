class RaifException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifResponseException(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifUnauthorizedException(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifDeviceNotVerifyException(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class Raif3DSErrorException(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
