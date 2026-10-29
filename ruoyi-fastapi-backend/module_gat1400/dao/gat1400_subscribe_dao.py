from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from module_gat1400.entity.do.gat1400_subscribe_do import Gat1400Subscribe


class Gat1400SubscribeDao:
    @classmethod
    async def get_active_subscribe(cls, db: AsyncSession) -> Gat1400Subscribe | None:
        """获取当前有效的订阅（订阅中且未过期）。"""
        statement = (
            select(Gat1400Subscribe)
            .where(
                Gat1400Subscribe.del_flag == '0',
                Gat1400Subscribe.subscribe_status == '0',
                Gat1400Subscribe.operate_type == '0',
                Gat1400Subscribe.end_time > datetime.now(),
            )
            .order_by(Gat1400Subscribe.create_time.desc())
        )
        return (await db.execute(statement)).scalars().first()

    @classmethod
    async def get_by_id(cls, db: AsyncSession, subscribe_id: str) -> Gat1400Subscribe | None:
        return (
            (
                await db.execute(
                    select(Gat1400Subscribe).where(
                        Gat1400Subscribe.subscribe_id == subscribe_id, Gat1400Subscribe.del_flag == '0'
                    )
                )
            )
            .scalars()
            .first()
        )

    @classmethod
    async def add(cls, db: AsyncSession, **fields: Any) -> Gat1400Subscribe:
        record = Gat1400Subscribe(**fields)
        db.add(record)
        await db.flush()
        return record

    @classmethod
    async def update(cls, db: AsyncSession, subscribe_id: str, **fields: Any) -> None:
        existing = await cls.get_by_id(db, subscribe_id)
        if existing:
            for key, value in fields.items():
                setattr(existing, key, value)
            existing.update_time = datetime.now()
            await db.flush()
