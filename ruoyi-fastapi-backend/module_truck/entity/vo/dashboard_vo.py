from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class TruckDashboardSummaryModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    vehicle_total: int = 0
    local_vehicle_count: int = 0
    nonlocal_vehicle_count: int = 0
    owner_total: int = 0
    enterprise_count: int = 0
    individual_count: int = 0
    supervision_count: int = 0
    level_one_count: int = 0
    level_two_count: int = 0


class TruckDeptStatModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    dept_id: int
    dept_name: str
    vehicle_count: int = 0
    enterprise_count: int = 0
    individual_count: int = 0


class TruckDeviceCoverageModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    device_type: str
    device_name: str
    installed_count: int = 0
    vehicle_total: int = 0
    coverage_rate: float = 0
