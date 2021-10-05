class RaifException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)


class RaifResponseException(RaifException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
