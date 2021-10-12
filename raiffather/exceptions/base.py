class RaifException(Exception):
    __module__ = "raiffather"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifErrorResponse(RaifException):
    def __init__(self, response, *args, **kwargs):
        self.status_code = response.status_code
        self.text = response.text
        self.response = response
        super().__init__(f"{self.status_code}: {self.text}", *args, **kwargs)


class RaifUnauthorized(RaifErrorResponse):
    def __init__(self, response, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifDeviceNotVerify(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifError3DS(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifProductNotFound(RaifException):
    def __init__(self, sought, products, *args, **kwargs):
        self.sought = sought
        self.products = products
        super().__init__(*args, *kwargs)


class RaifPasswordDeprecated(RaifErrorResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
