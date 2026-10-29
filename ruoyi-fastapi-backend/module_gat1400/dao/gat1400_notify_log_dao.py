from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from module_gat1400.entity.do.gat1400_notify_log_do import Gat1400NotifyLog


class Gat1400NotifyLogDao:
    @classmethod
    async def add(cls, db: AsyncSession, **fields: Any) -> Gat1400NotifyLog:
        record = Gat1400NotifyLog(**fields)
        db.add(record)
        await db.flush()
        return record
