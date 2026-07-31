from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from module_truck.dao.dashboard_dao import TruckDashboardDao
from module_truck.entity.do.truck_do import TruckVehicle
from module_truck.entity.vo.dashboard_vo import (
    TruckDashboardSummaryModel,
    TruckDeptStatModel,
    TruckDeviceCoverageModel,
)


class TruckDashboardService:
    DEVICE_NAMES = {'brake_assist': '刹车辅助系统', 'panoramic_360': '360全景影像'}

    @classmethod
    async def get_summary(
        cls, db: AsyncSession, vehicle_scope: ColumnElement, owner_scope: ColumnElement
    ) -> TruckDashboardSummaryModel:
        values = await TruckDashboardDao.get_vehicle_summary(db, vehicle_scope)
        values.update(await TruckDashboardDao.get_owner_summary(db, owner_scope))
        return TruckDashboardSummaryModel(**values)

    @classmethod
    async def get_dept_stats(
        cls, db: AsyncSession, vehicle_scope: ColumnElement, owner_scope: ColumnElement
    ) -> list[TruckDeptStatModel]:
        vehicle_counts = dict(await TruckDashboardDao.get_dept_vehicle_counts(db, vehicle_scope))
        owner_counts = {row[0]: (row[1] or 0, row[2] or 0) for row in await TruckDashboardDao.get_dept_owner_counts(db, owner_scope)}
        result = []
        for dept_id, dept_name in await TruckDashboardDao.get_departments(db):
            enterprise_count, individual_count = owner_counts.get(dept_id, (0, 0))
            result.append(
                TruckDeptStatModel(
                    dept_id=dept_id,
                    dept_name=dept_name,
                    vehicle_count=vehicle_counts.get(dept_id, 0),
                    enterprise_count=enterprise_count,
                    individual_count=individual_count,
                )
            )
        return result

    @classmethod
    async def get_device_coverage(
        cls, db: AsyncSession, vehicle_scope: ColumnElement
    ) -> list[TruckDeviceCoverageModel]:
        vehicle_total = (
            await db.execute(
                select(func.count(TruckVehicle.vehicle_id)).where(
                    TruckVehicle.del_flag == '0',
                    TruckVehicle.vehicle_status.notin_(['transferred', 'scrapped']),
                    vehicle_scope,
                )
            )
        ).scalar_one()
        installed = dict(await TruckDashboardDao.get_device_counts(db, vehicle_scope))
        return [
            TruckDeviceCoverageModel(
                device_type=device_type,
                device_name=device_name,
                installed_count=installed.get(device_type, 0),
                vehicle_total=vehicle_total,
                coverage_rate=round(installed.get(device_type, 0) * 100 / vehicle_total, 2) if vehicle_total else 0,
            )
            for device_type, device_name in cls.DEVICE_NAMES.items()
        ]
