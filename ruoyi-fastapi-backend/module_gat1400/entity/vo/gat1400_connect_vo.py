from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Gat1400ConnectModel(BaseModel):
    """
    GA/T1400对接状态出参模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    connect_id: int | None = None
    register_status: str | None = None
    fail_count: int | None = None
    last_register_time: datetime | None = None
    last_keepalive_time: datetime | None = None
    keepalive_count: int | None = None
    error_message: str | None = None
    platform_addr: str | None = None
    device_id: str | None = None
    enabled: bool | None = None
    keepalive_interval: int | None = None
