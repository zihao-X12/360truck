from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from module_gat1400.entity.do.gat1400_connect_do import Gat1400Connect


class Gat1400ConnectDao:
    @classmethod
    async def get_status(cls, db: AsyncSession) -> Gat1400Connect | None:
        statement = select(Gat1400Connect).where(Gat1400Connect.del_flag == '0').order_by(Gat1400Connect.connect_id)
        return (await db.execute(statement)).scalars().first()

    @classmethod
    async def get_or_create(cls, db: AsyncSession) -> Gat1400Connect:
        row = await cls.get_status(db)
        if not row:
            row = Gat1400Connect(register_status='unregistered')
            db.add(row)
            await db.flush()
        return row

    @classmethod
    async def update_status(cls, db: AsyncSession, row: Gat1400Connect, **fields: Any) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await db.flush()
