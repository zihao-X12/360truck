from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from module_truck.entity.do.truck_do import TruckVehicle, TruckVehicleDevice, TruckVehicleOwnerHistory
from module_truck.entity.vo.vehicle_vo import TruckVehicleModel, TruckVehiclePageQueryModel
from utils.page_util import PageUtil


class TruckVehicleDao:
    @classmethod
    async def get_list(
        cls, db: AsyncSession, query: TruckVehiclePageQueryModel, scope: ColumnElement, is_page: bool
    ) -> Any:
        statement = select(TruckVehicle).where(
            TruckVehicle.del_flag == '0',
            TruckVehicle.plate_no.like(f'%{query.plate_no}%') if query.plate_no else True,
            TruckVehicle.dept_id == query.dept_id if query.dept_id else True,
            TruckVehicle.owner_id == query.owner_id if query.owner_id else True,
            TruckVehicle.vehicle_type == query.vehicle_type if query.vehicle_type else True,
            TruckVehicle.vehicle_status == query.vehicle_status if query.vehicle_status else True,
            TruckVehicle.source_type == query.source_type if query.source_type else True,
            TruckVehicle.supervision_flag == query.supervision_flag if query.supervision_flag else True,
            TruckVehicle.warning_level == query.warning_level if query.warning_level else True,
            scope,
        ).order_by(TruckVehicle.vehicle_id.desc())
        return await PageUtil.paginate(db, statement, query.page_num, query.page_size, is_page)

    @classmethod
    async def get_by_id(cls, db: AsyncSession, vehicle_id: int, scope: ColumnElement | None = None) -> TruckVehicle | None:
        statement = select(TruckVehicle).where(TruckVehicle.vehicle_id == vehicle_id, TruckVehicle.del_flag == '0')
        if scope is not None:
            statement = statement.where(scope)
        return (await db.execute(statement)).scalars().first()

    @classmethod
    async def get_by_plate(cls, db: AsyncSession, plate_no: str, plate_color: str) -> TruckVehicle | None:
        return (await db.execute(select(TruckVehicle).where(TruckVehicle.plate_no == plate_no, TruckVehicle.plate_color == plate_color))).scalars().first()

    @classmethod
    async def get_by_vin(cls, db: AsyncSession, vin: str) -> TruckVehicle | None:
        return (await db.execute(select(TruckVehicle).where(TruckVehicle.vin == vin))).scalars().first()

    @classmethod
    async def add(cls, db: AsyncSession, vehicle: TruckVehicleModel) -> TruckVehicle:
        record = TruckVehicle(**vehicle.model_dump(exclude={'vehicle_id', 'devices', 'change_reason'}, exclude_none=True))
        db.add(record)
        await db.flush()
        return record

    @classmethod
    async def update(cls, db: AsyncSession, vehicle: TruckVehicleModel) -> None:
        values = vehicle.model_dump(exclude={'devices', 'change_reason', 'create_by', 'create_time'}, exclude_none=True)
        await db.execute(update(TruckVehicle).where(TruckVehicle.vehicle_id == vehicle.vehicle_id).values(**values))

    @classmethod
    async def soft_delete(cls, db: AsyncSession, vehicle_id: int, update_by: str, update_time: datetime) -> None:
        await db.execute(update(TruckVehicle).where(TruckVehicle.vehicle_id == vehicle_id).values(del_flag='2', update_by=update_by, update_time=update_time))

    @classmethod
    async def replace_devices(cls, db: AsyncSession, vehicle_id: int, devices: list, user_name: str) -> None:
        await db.execute(delete(TruckVehicleDevice).where(TruckVehicleDevice.vehicle_id == vehicle_id))
        db.add_all([TruckVehicleDevice(vehicle_id=vehicle_id, create_by=user_name, update_by=user_name, **device.model_dump(exclude={'device_id'})) for device in devices])

    @classmethod
    async def get_devices(cls, db: AsyncSession, vehicle_id: int) -> Sequence[TruckVehicleDevice]:
        return (await db.execute(select(TruckVehicleDevice).where(TruckVehicleDevice.vehicle_id == vehicle_id).order_by(TruckVehicleDevice.device_id))).scalars().all()

    @classmethod
    async def get_device_types(cls, db: AsyncSession, vehicle_ids: list[int]) -> dict[int, set[str]]:
        if not vehicle_ids:
            return {}
        records = (
            await db.execute(
                select(TruckVehicleDevice.vehicle_id, TruckVehicleDevice.device_type).where(
                    TruckVehicleDevice.vehicle_id.in_(vehicle_ids), TruckVehicleDevice.status == '0'
                )
            )
        ).all()
        result: dict[int, set[str]] = {}
        for vehicle_id, device_type in records:
            result.setdefault(vehicle_id, set()).add(device_type)
        return result

    @classmethod
    async def add_history(cls, db: AsyncSession, vehicle_id: int, old_owner_id: int | None, new_owner_id: int | None, old_dept_id: int | None, new_dept_id: int | None, reason: str | None, user_name: str) -> None:
        db.add(TruckVehicleOwnerHistory(vehicle_id=vehicle_id, old_owner_id=old_owner_id, new_owner_id=new_owner_id, old_dept_id=old_dept_id, new_dept_id=new_dept_id, change_reason=reason, change_by=user_name))
