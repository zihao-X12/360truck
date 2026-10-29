from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_validation_decorator import NotBlank


class TruckOwnerModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    owner_id: int | None = None
    owner_type: Literal['enterprise', 'individual'] | None = None
    owner_name: str | None = None
    credit_code: str | None = None
    id_card_no: str | None = None
    # 主体登记归属中队：仅用于登记统计与列表筛选，不决定名下车辆的分管中队。
    # 挂靠场景下同一主体的车辆可由不同中队分管，车辆分管以 truck_vehicle.dept_id 为准。
    dept_id: int | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    address: str | None = None
    status: Literal['0', '1'] | None = '0'
    remark: str | None = None
    create_by: str | None = None
    create_time: datetime | None = None
    update_by: str | None = None
    update_time: datetime | None = None
    vehicle_count: int = 0

    @NotBlank(field_name='owner_type', message='主体类型不能为空')
    def get_owner_type(self) -> str | None:
        return self.owner_type

    @NotBlank(field_name='owner_name', message='主体名称不能为空')
    def get_owner_name(self) -> str | None:
        return self.owner_name

    @NotBlank(field_name='dept_id', message='所属中队不能为空')
    def get_dept_id(self) -> int | None:
        return self.dept_id

    def validate_fields(self) -> None:
        self.get_owner_type()
        self.get_owner_name()
        self.get_dept_id()


class TruckOwnerPageQueryModel(TruckOwnerModel):
    page_num: int = Field(default=1)
    page_size: int = Field(default=10)


class DeleteTruckOwnerModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)
    owner_ids: str
