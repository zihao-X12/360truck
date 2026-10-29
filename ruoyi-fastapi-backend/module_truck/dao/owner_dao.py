from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from module_truck.entity.do.truck_do import TruckOwner, TruckVehicle
from module_truck.entity.vo.owner_vo import TruckOwnerModel, TruckOwnerPageQueryModel
from utils.page_util import PageUtil


class TruckOwnerDao:
    @classmethod
    async def get_list(
        cls,
        db: AsyncSession,
        query: TruckOwnerPageQueryModel,
        owner_scope: ColumnElement,
        vehicle_scope: ColumnElement,
        is_page: bool,
    ) -> Any:
        linked_vehicle_visible = exists(
            select(1).select_from(TruckVehicle).where(
                TruckVehicle.owner_id == TruckOwner.owner_id,
                TruckVehicle.del_flag == '0',
                vehicle_scope,
            )
        )
        statement = select(TruckOwner).where(
            TruckOwner.del_flag == '0',
            TruckOwner.owner_type == query.owner_type if query.owner_type else True,
            TruckOwner.dept_id == query.dept_id if query.dept_id else True,
            TruckOwner.owner_name.like(f'%{query.owner_name}%') if query.owner_name else True,
            TruckOwner.status == query.status if query.status else True,
            or_(owner_scope, linked_vehicle_visible),
        ).order_by(TruckOwner.owner_id.desc())
        return await PageUtil.paginate(db, statement, query.page_num, query.page_size, is_page)

    @classmethod
    async def get_by_id(
        cls,
        db: AsyncSession,
        owner_id: int,
        owner_scope: ColumnElement | None = None,
        vehicle_scope: ColumnElement | None = None,
    ) -> TruckOwner | None:
        statement = select(TruckOwner).where(TruckOwner.owner_id == owner_id, TruckOwner.del_flag == '0')
        if owner_scope is not None:
            visibility = owner_scope
            if vehicle_scope is not None:
                visibility = or_(
                    visibility,
                    exists(
                        select(1).select_from(TruckVehicle).where(
                            TruckVehicle.owner_id == TruckOwner.owner_id,
                            TruckVehicle.del_flag == '0',
                            vehicle_scope,
                        )
                    ),
                )
            statement = statement.where(visibility)
        return (await db.execute(statement)).scalars().first()

    @classmethod
    async def get_by_identity(cls, db: AsyncSession, owner: TruckOwnerModel) -> TruckOwner | None:
        conditions = [TruckOwner.del_flag == '0']
        if owner.credit_code:
            conditions.append(TruckOwner.credit_code == owner.credit_code)
        elif owner.id_card_no:
            conditions.append(TruckOwner.id_card_no == owner.id_card_no)
        else:
            return None
        return (await db.execute(select(TruckOwner).where(*conditions))).scalars().first()

    @classmethod
    async def get_by_name(cls, db: AsyncSession, owner_type: str, owner_name: str) -> TruckOwner | None:
        statement = select(TruckOwner).where(
            TruckOwner.del_flag == '0',
            TruckOwner.owner_type == owner_type,
            func.lower(func.trim(TruckOwner.owner_name)) == owner_name.lower(),
        )
        return (await db.execute(statement)).scalars().first()

    @classmethod
    async def add(cls, db: AsyncSession, owner: TruckOwnerModel) -> TruckOwner:
        record = TruckOwner(**owner.model_dump(exclude={'owner_id', 'vehicle_count'}, exclude_none=True))
        db.add(record)
        await db.flush()
        return record

    @classmethod
    async def update(cls, db: AsyncSession, owner: TruckOwnerModel) -> None:
        values = owner.model_dump(exclude={'create_by', 'create_time', 'vehicle_count'}, exclude_none=True)
        await db.execute(update(TruckOwner).where(TruckOwner.owner_id == owner.owner_id).values(**values))

    @classmethod
    async def delete(cls, db: AsyncSession, owner_id: int, update_by: str, update_time: datetime) -> None:
        """
        软删除主体。

        同时清空 `credit_code` 与 `id_card_no`：这两个字段是单列唯一索引，
        若保留软删记录的身份信息，重建同一主体时会被唯一约束拦下并报
        `Duplicate entry`。清空后身份标识可复用，主体名称、归属历史与
        操作日志仍保留完整审计痕迹。

        :param db: orm对象
        :param owner_id: 主体ID
        :param update_by: 更新者
        :param update_time: 更新时间
        :return: None
        """
        await db.execute(
            update(TruckOwner)
            .where(TruckOwner.owner_id == owner_id)
            .values(del_flag='2', credit_code=None, id_card_no=None, update_by=update_by, update_time=update_time)
        )

    @classmethod
    async def count_vehicles(cls, db: AsyncSession, owner_id: int) -> int:
        return (await db.execute(select(func.count()).select_from(TruckVehicle).where(TruckVehicle.owner_id == owner_id, TruckVehicle.del_flag == '0'))).scalar_one()

    @classmethod
    async def count_vehicles_by_owner_ids(
        cls, db: AsyncSession, owner_ids: list[int], vehicle_scope: ColumnElement | None = None
    ) -> dict[int, int]:
        """
        统计各主体名下车辆数。

        :param db: 数据库会话
        :param owner_ids: 主体 ID 列表
        :param vehicle_scope: 车辆数据权限过滤条件；主体归集视图要求展示跨中队全部车辆，故默认不过滤
        :return: 主体 ID 到车辆数的映射
        """
        if not owner_ids:
            return {}
        conditions = [TruckVehicle.owner_id.in_(owner_ids), TruckVehicle.del_flag == '0']
        if vehicle_scope is not None:
            conditions.append(vehicle_scope)
        records = (
            await db.execute(
                select(TruckVehicle.owner_id, func.count(TruckVehicle.vehicle_id))
                .where(*conditions)
                .group_by(TruckVehicle.owner_id)
            )
        ).all()
        return dict(records)
