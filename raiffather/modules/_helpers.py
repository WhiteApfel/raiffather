import types
from typing import TypeVar, Union, get_origin

from raiffather.models.products import Account, Card

T = TypeVar("T")


def extend_product_types(func: T) -> T:
    def wrapper(self, **kwargs) -> T:

        def check_and_set_product(kwname, product) -> bool:
            if (
                not isinstance(kwargs[kwname], product)
                and
                (
                    isinstance(kwargs[kwname], str)
                    or isinstance(kwargs[kwname], int)
                )
            ):
                if product is Card:
                    kwargs[kwname] = self.products.cards[kwargs[kwname]]
                    return True
                elif product is Account:
                    kwargs[kwname] = self.products.accounts[kwargs[kwname]]
                    return True
            return False

        for kwparam, hint in func.__annotations__.items():
            if kwparam == 'return':
                continue
            if isinstance(hint, types.UnionType):
                hint: types.UnionType
                if types.NoneType in hint.__args__:
                    continue
                if Account in hint.__args__:
                    if check_and_set_product(kwparam, Account):
                        continue
                if Card in hint.__args__:
                    if check_and_set_product(kwparam, Card):
                        continue
            elif get_origin(hint) is Union:
                hint: types.UnionType
                if types.NoneType in hint.__args__:
                    continue
                if Account in hint.__args__:
                    if check_and_set_product(kwparam, Account):
                        continue
                if Card in hint.__args__:
                    if check_and_set_product(kwparam, Card):
                        continue
            else:
                if issubclass(hint, Account):
                    if check_and_set_product(kwparam, Account):
                        continue
                if issubclass(hint, Card):
                    if check_and_set_product(kwparam, Card):
                        continue
        return func(self, **kwargs)
    return wrapper
