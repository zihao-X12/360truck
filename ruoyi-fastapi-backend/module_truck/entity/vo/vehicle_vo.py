from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from pydantic_validation_decorator import NotBlank

VIN_LENGTH = 17


class TruckVehicleDeviceModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    device_id: int | None = None
    device_type: str
    product_name: str | None = None
    brand: str | None = None
    install_date: date | None = None
    status: Literal['0', '1'] = '0'
    remark: str | None = None


class TruckVehicleModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    vehicle_id: int | None = None
    project_name: str | None = None
    plate_no: str | None = None
    plate_color: str | None = None
    vehicle_type: str | None = None
    vehicle_brand: str | None = None
    vin: str | None = None
    rated_load: Decimal | None = None
    source_type: Literal['local', 'nonlocal'] | None = None
    motor_owner_name: str | None = None
    driver_name: str | None = None
    driver_phone: str | None = None
    affiliated_company: str | None = None
    insurance_status: str | None = None
    insurance_info: str | None = None
    owner_id: int | None = None
    owner_type: Literal['enterprise', 'individual'] | None = None
    dept_id: int | None = None
    photo_file_id: str | None = None
    vehicle_status: Literal['normal', 'stopped', 'transferred', 'scrapped'] = 'normal'
    supervision_flag: Literal['0', '1'] = '0'
    warning_level: Literal['level_one', 'level_two', 'none'] | None = None
    missing_device_count: int = 0
    remark: str | None = None
    devices: list[TruckVehicleDeviceModel] = Field(default_factory=list)
    change_reason: str | None = None
    create_by: str | None = None
    create_time: datetime | None = None
    update_by: str | None = None
    update_time: datetime | None = None

    @field_validator('plate_no')
    @classmethod
    def normalize_plate_no(cls, value: str | None) -> str | None:
        return value.strip().upper().replace(' ', '') if value else value

    @field_validator('vin')
    @classmethod
    def validate_vin(cls, value: str | None) -> str | None:
        if not value:
            return value
        normalized = value.strip().upper()
        if len(normalized) != VIN_LENGTH:
            raise ValueError('车架号必须为17位')
        return normalized

    @NotBlank(field_name='plate_no', message='车牌号不能为空')
    def get_plate_no(self) -> str | None:
        return self.plate_no

    @NotBlank(field_name='plate_color', message='车牌颜色不能为空')
    def get_plate_color(self) -> str | None:
        return self.plate_color

    @NotBlank(field_name='dept_id', message='所属中队不能为空')
    def get_dept_id(self) -> int | None:
        return self.dept_id

    def validate_fields(self) -> None:
        self.get_plate_no()
        self.get_plate_color()
        self.get_dept_id()


class TruckVehiclePageQueryModel(TruckVehicleModel):
    vehicle_status: Literal['normal', 'stopped', 'transferred', 'scrapped'] | None = None
    supervision_flag: Literal['0', '1'] | None = None
    page_num: int = Field(default=1)
    page_size: int = Field(default=10)


class DeleteTruckVehicleModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)
    vehicle_ids: str
