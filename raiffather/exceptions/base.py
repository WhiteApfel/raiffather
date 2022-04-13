from httpx import Response


class RaifException(Exception):
    __module__ = "raiffather"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifErrorResponse(RaifException):
    def __new__(cls, response: Response, *args, **kwargs):
        if response.status_code == 401:
            return super(RaifErrorResponse, RaifUnauthorized).__new__(
                RaifUnauthorized, response, *args, **kwargs
            )
        if response.status_code == 417:
            return super(RaifErrorResponse, RaifIncrorrectRequest).__new__(
                RaifIncrorrectRequest, response, *args, **kwargs
            )
        return super(RaifErrorResponse, cls).__new__(cls, response, *args, **kwargs)

    def __init__(self, response: Response, *args, **kwargs):
        self.status_code = response.status_code
        if "_form" in response.text:
            self.text = response.json()["_form"]
            if type(self.text) is list and len(self.text) == 1:
                self.text = self.text[0]
        else:
            self.text = response.text
        self.response = response
        super().__init__(f"{self.status_code}: {self.text}", *args, **kwargs)


class RaifIncrorrectRequest(RaifErrorResponse):
    def __init__(self, response, *args, **kwargs):
        super().__init__(response, *args, *kwargs)


class RaifUnauthorized(RaifErrorResponse):
    def __init__(self, response, *args, **kwargs):
        super().__init__(response, *args, *kwargs)


class RaifDeviceNotVerify(RaifException):
    def __init__(self, response, *args, **kwargs):
        super().__init__(response, *args, *kwargs)


class RaifError3DS(RaifException):
    def __init__(self, response, *args, **kwargs):
        super().__init__(response, *args, *kwargs)


class RaifProductNotFound(RaifException):
    def __init__(self, sought, products, *args, **kwargs):
        self.sought = sought
        self.products = products
        super().__init__(*args, *kwargs)


class RaifFoundMoreThanOneProduct(RaifException):
    def __init__(self, sought, found, products, *args, **kwargs):
        self.sought = sought
        self.found = found
        self.products = products
        super().__init__(*args, *kwargs)


class RaifPasswordDeprecated(RaifErrorResponse):
    def __init__(self, response, *args, **kwargs):
        super().__init__(*args, response, *kwargs)


class RaifValueError(ValueError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
