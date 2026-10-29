from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from module_gat1400.entity.do.pass_record_do import TruckPassRecord
from module_gat1400.entity.vo.pass_record_vo import PassRecordPageQueryModel
from module_truck.entity.do.truck_do import TruckVehicle
from utils.page_util import PageUtil


class TruckPassRecordDao:
    @classmethod
    async def get_existing_ids(cls, db: AsyncSession, motor_vehicle_ids: list[str]) -> set[str]:
        """批量查询已存在的过车记录 ID（用于去重分流新增/更新）。"""
        if not motor_vehicle_ids:
            return set()
        statement = select(TruckPassRecord.motor_vehicle_id).where(
            TruckPassRecord.motor_vehicle_id.in_(motor_vehicle_ids)
        )
        return set((await db.execute(statement)).scalars().all())

    @classmethod
    async def add(cls, db: AsyncSession, **fields: Any) -> TruckPassRecord:
        record = TruckPassRecord(**fields)
        db.add(record)
        await db.flush()
        return record

    @classmethod
    async def update_by_motor_vehicle_id(cls, db: AsyncSession, motor_vehicle_id: str, **fields: Any) -> None:
        existing = (
            (await db.execute(select(TruckPassRecord).where(TruckPassRecord.motor_vehicle_id == motor_vehicle_id)))
            .scalars()
            .first()
        )
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
            await db.flush()

    @classmethod
    async def get_vehicle_ids_by_plates(cls, db: AsyncSession, plates: list[str]) -> dict[str, list[int]]:
        """按车牌号批量匹配本平台车辆档案，返回 {plate_no: [vehicle_id]}。"""
        if not plates:
            return {}
        statement = select(TruckVehicle.vehicle_id, TruckVehicle.plate_no).where(
            TruckVehicle.plate_no.in_(plates), TruckVehicle.del_flag == '0'
        )
        result: dict[str, list[int]] = {}
        for vehicle_id, plate_no in (await db.execute(statement)).all():
            result.setdefault(plate_no, []).append(vehicle_id)
        return result

    @classmethod
    async def get_list(
        cls,
        db: AsyncSession,
        query: PassRecordPageQueryModel,
        scope: ColumnElement,
        is_page: bool,
    ) -> Any:
        """
        过车记录分页查询（含车辆档案外连接，用于数据权限过滤与是否本平台车辆标记）。

        数据权限说明：scope 为当前用户数据范围表达式（作用于 truck_vehicle.dept_id）。
        - 全量角色（大队管理员/领导）scope 为 True，不加过滤，可见全部过车记录；
        - 中队管理员仅能看到关联到本中队车辆档案的过车记录（outerjoin 下未关联记录
          TruckVehicle 列为 NULL，自然被 scope 过滤）。
        """
        statement = select(TruckPassRecord).outerjoin(
            TruckVehicle, TruckPassRecord.vehicle_id == TruckVehicle.vehicle_id
        )
        conditions = [
            TruckPassRecord.plate_no.like(f'%{query.plate_no}%') if query.plate_no else True,
            TruckPassRecord.device_id == query.device_id if query.device_id else True,
            TruckPassRecord.pass_time >= query.start_time if query.start_time else True,
            TruckPassRecord.pass_time <= query.end_time if query.end_time else True,
            TruckPassRecord.vehicle_id.isnot(None) if query.vehicle_matched is True else True,
            TruckPassRecord.vehicle_id.is_(None) if query.vehicle_matched is False else True,
        ]
        if scope is not True:
            conditions.append(scope)
        statement = statement.where(*conditions).order_by(
            TruckPassRecord.pass_time.desc(), TruckPassRecord.record_id.desc()
        )
        return await PageUtil.paginate(db, statement, query.page_num, query.page_size, is_page)
