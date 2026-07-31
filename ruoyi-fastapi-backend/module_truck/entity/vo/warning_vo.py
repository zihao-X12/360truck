from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class TruckWarningPageQueryModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    plate_no: str | None = None
    dept_id: int | None = None
    warning_level: str | None = None
    page_num: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=500)


class TruckWarningModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    vehicle_id: int
    plate_no: str
    plate_color: str
    vehicle_type: str | None = None
    project_name: str | None = None
    dept_id: int
    dept_name: str | None = None
    owner_name: str | None = None
    warning_level: str
    missing_device_count: int
    missing_device_types: list[str] = Field(default_factory=list)
