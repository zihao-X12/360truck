from typing import Any

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from module_truck.entity.do.truck_do import TruckVehicle, TruckWarningRule
from module_truck.entity.vo.warning_vo import TruckWarningPageQueryModel
from utils.page_util import PageUtil


class TruckWarningDao:
    @classmethod
    async def get_active_vehicles(cls, db: AsyncSession, scope: ColumnElement) -> list[TruckVehicle]:
        return (
            await db.execute(
                select(TruckVehicle).where(
                    TruckVehicle.del_flag == '0',
                    TruckVehicle.vehicle_status.notin_(['transferred', 'scrapped']),
                    scope,
                )
            )
        ).scalars().all()

    @classmethod
    async def get_list(
        cls, db: AsyncSession, query: TruckWarningPageQueryModel, scope: ColumnElement, is_page: bool
    ) -> Any:
        statement = (
            select(TruckVehicle)
            .where(
                TruckVehicle.del_flag == '0',
                TruckVehicle.supervision_flag == '1',
                TruckVehicle.plate_no.like(f'%{query.plate_no}%') if query.plate_no else True,
                TruckVehicle.dept_id == query.dept_id if query.dept_id else True,
                TruckVehicle.warning_level == query.warning_level if query.warning_level else True,
                scope,
            )
            .order_by(TruckVehicle.warning_level, TruckVehicle.vehicle_id.desc())
        )
        return await PageUtil.paginate(db, statement, query.page_num, query.page_size, is_page)

    @classmethod
    async def get_enabled_rule(cls, db: AsyncSession) -> TruckWarningRule | None:
        return (
            await db.execute(select(TruckWarningRule).where(TruckWarningRule.status == '0').order_by(TruckWarningRule.rule_id))
        ).scalars().first()

    @classmethod
    async def update_warning(cls, db: AsyncSession, vehicle_id: int, missing_count: int, level: str) -> None:
        await db.execute(
            update(TruckVehicle)
            .where(TruckVehicle.vehicle_id == vehicle_id)
            .values(
                missing_device_count=missing_count,
                warning_level=level,
                supervision_flag='1' if missing_count else '0',
            )
        )
