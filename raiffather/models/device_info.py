from typing import Literal

from pydantic import BaseModel


class DeviceInfo(BaseModel):
    app_version: str
    router_ip: str
    router_mac: str
    ip: str
    screen_y: Literal["1920", "2340", "2400"]
    screen_x: Literal["1080"]
    os: Literal["Android"]
    name: Literal["raiffather"]
    serial_number: str
    provider: str
    mac: str
    os_version: Literal["11"]
    uid: str
    model: str
    push: str
    user_security_hash: str
    fingerprint: str
    uuid: str
    fcm_cred: dict
