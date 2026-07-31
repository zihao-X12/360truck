from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from module_truck.entity.do.truck_do import TruckOwner, TruckVehicle
from module_truck.entity.vo.owner_vo import TruckOwnerModel, TruckOwnerPageQueryModel
from utils.page_util import PageUtil


class TruckOwnerDao:
    @classmethod
    async def get_list(
        cls, db: AsyncSession, query: TruckOwnerPageQueryModel, scope: ColumnElement, is_page: bool
    ) -> Any:
        statement = select(TruckOwner).where(
            TruckOwner.del_flag == '0',
            TruckOwner.owner_type == query.owner_type if query.owner_type else True,
            TruckOwner.dept_id == query.dept_id if query.dept_id else True,
            TruckOwner.owner_name.like(f'%{query.owner_name}%') if query.owner_name else True,
            TruckOwner.status == query.status if query.status else True,
            scope,
        ).order_by(TruckOwner.owner_id.desc())
        return await PageUtil.paginate(db, statement, query.page_num, query.page_size, is_page)

    @classmethod
    async def get_by_id(cls, db: AsyncSession, owner_id: int, scope: ColumnElement | None = None) -> TruckOwner | None:
        statement = select(TruckOwner).where(TruckOwner.owner_id == owner_id, TruckOwner.del_flag == '0')
        if scope is not None:
            statement = statement.where(scope)
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
    async def add(cls, db: AsyncSession, owner: TruckOwnerModel) -> TruckOwner:
        record = TruckOwner(**owner.model_dump(exclude={'owner_id'}, exclude_none=True))
        db.add(record)
        await db.flush()
        return record

    @classmethod
    async def update(cls, db: AsyncSession, owner: TruckOwnerModel) -> None:
        values = owner.model_dump(exclude={'create_by', 'create_time'}, exclude_none=True)
        await db.execute(update(TruckOwner).where(TruckOwner.owner_id == owner.owner_id).values(**values))

    @classmethod
    async def delete(cls, db: AsyncSession, owner_id: int, update_by: str, update_time: datetime) -> None:
        await db.execute(
            update(TruckOwner)
            .where(TruckOwner.owner_id == owner_id)
            .values(del_flag='2', update_by=update_by, update_time=update_time)
        )

    @classmethod
    async def count_vehicles(cls, db: AsyncSession, owner_id: int) -> int:
        return (await db.execute(select(func.count()).select_from(TruckVehicle).where(TruckVehicle.owner_id == owner_id, TruckVehicle.del_flag == '0'))).scalar_one()
