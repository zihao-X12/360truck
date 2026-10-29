from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from module_admin.entity.do.dept_do import SysDept
from module_truck.entity.do.truck_do import TruckOwner, TruckVehicle, TruckVehicleDevice

TRUCK_BRIGADE_DEPT_ID = 9100


class TruckDashboardDao:
    @classmethod
    async def get_vehicle_summary(cls, db: AsyncSession, scope: ColumnElement) -> dict[str, int]:
        row = (
            await db.execute(
                select(
                    func.count(TruckVehicle.vehicle_id),
                    func.sum(case((TruckVehicle.source_type == 'local', 1), else_=0)),
                    func.sum(case((TruckVehicle.source_type == 'nonlocal', 1), else_=0)),
                    func.sum(case((TruckVehicle.supervision_flag == '1', 1), else_=0)),
                    func.sum(case((TruckVehicle.warning_level == 'level_one', 1), else_=0)),
                    func.sum(case((TruckVehicle.warning_level == 'level_two', 1), else_=0)),
                ).where(TruckVehicle.del_flag == '0', scope)
            )
        ).one()
        return {
            'vehicle_total': row[0] or 0,
            'local_vehicle_count': row[1] or 0,
            'nonlocal_vehicle_count': row[2] or 0,
            'supervision_count': row[3] or 0,
            'level_one_count': row[4] or 0,
            'level_two_count': row[5] or 0,
        }

    @classmethod
    async def get_owner_summary(cls, db: AsyncSession, scope: ColumnElement) -> dict[str, int]:
        row = (
            await db.execute(
                select(
                    func.count(TruckOwner.owner_id),
                    func.sum(case((TruckOwner.owner_type == 'enterprise', 1), else_=0)),
                    func.sum(case((TruckOwner.owner_type == 'individual', 1), else_=0)),
                ).where(TruckOwner.del_flag == '0', scope)
            )
        ).one()
        return {'owner_total': row[0] or 0, 'enterprise_count': row[1] or 0, 'individual_count': row[2] or 0}

    @classmethod
    async def get_dept_vehicle_counts(cls, db: AsyncSession, scope: ColumnElement) -> list:
        return (
            await db.execute(
                select(TruckVehicle.dept_id, func.count(TruckVehicle.vehicle_id))
                .where(TruckVehicle.del_flag == '0', scope)
                .group_by(TruckVehicle.dept_id)
            )
        ).all()

    @classmethod
    async def get_dept_owner_counts(cls, db: AsyncSession, vehicle_scope: ColumnElement) -> list:
        """
        按分管中队统计车辆所属主体数（企业/个人）。

        口径必须与同一行的车辆数一致：车辆数按「车辆分管中队」统计，主体是车辆的
        归集维度且允许跨中队（挂靠车辆），因此这里按车辆分管中队归集主体，
        而不是按主体的登记归属中队。否则同一行两个数字口径不同、无法对齐。
        """
        return (
            await db.execute(
                select(
                    TruckVehicle.dept_id,
                    func.count(func.distinct(case((TruckOwner.owner_type == 'enterprise', TruckOwner.owner_id)))),
                    func.count(func.distinct(case((TruckOwner.owner_type == 'individual', TruckOwner.owner_id)))),
                )
                .select_from(TruckVehicle)
                .join(TruckOwner, TruckOwner.owner_id == TruckVehicle.owner_id)
                .where(TruckVehicle.del_flag == '0', TruckOwner.del_flag == '0', vehicle_scope)
                .group_by(TruckVehicle.dept_id)
            )
        ).all()

    @classmethod
    async def get_departments(cls, db: AsyncSession) -> list:
        return (
            await db.execute(
                select(SysDept.dept_id, SysDept.dept_name)
                .where(SysDept.del_flag == '0', SysDept.parent_id == TRUCK_BRIGADE_DEPT_ID)
                .order_by(SysDept.order_num)
            )
        ).all()

    @classmethod
    async def get_device_counts(cls, db: AsyncSession, scope: ColumnElement) -> list:
        return (
            await db.execute(
                select(TruckVehicleDevice.device_type, func.count(func.distinct(TruckVehicleDevice.vehicle_id)))
                .join(TruckVehicle, TruckVehicle.vehicle_id == TruckVehicleDevice.vehicle_id)
                .where(
                    TruckVehicle.del_flag == '0',
                    TruckVehicle.vehicle_status.notin_(['transferred', 'scrapped']),
                    TruckVehicleDevice.status == '0',
                    scope,
                )
                .group_by(TruckVehicleDevice.device_type)
            )
        ).all()
