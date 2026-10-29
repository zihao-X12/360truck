from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class PassRecordPageQueryModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    plate_no: str | None = None
    device_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    vehicle_matched: bool | None = None
    page_num: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=500)


class PassRecordModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    record_id: int
    motor_vehicle_id: str
    plate_no: str | None = None
    plate_color: str | None = None
    plate_class: str | None = None
    vehicle_class: str | None = None
    vehicle_color: str | None = None
    pass_time: datetime | None = None
    name_of_passed_road: str | None = None
    lane_no: int | None = None
    speed: int | None = None
    direction: str | None = None
    tollgate_id: str | None = None
    device_id: str | None = None
    storage_url1: str | None = None
    storage_url2: str | None = None
    plate_reliability: str | None = None
    vehicle_id: int | None = None
    vehicle_matched: bool | None = None
    dept_name: str | None = None
