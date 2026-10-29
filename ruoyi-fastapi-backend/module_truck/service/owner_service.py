from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel
from exceptions.exception import ServiceException
from module_truck.dao.owner_dao import TruckOwnerDao
from module_truck.entity.vo.owner_vo import DeleteTruckOwnerModel, TruckOwnerModel, TruckOwnerPageQueryModel


class TruckOwnerService:
    @classmethod
    async def get_list(
        cls,
        db: AsyncSession,
        query: TruckOwnerPageQueryModel,
        owner_scope: ColumnElement,
        vehicle_scope: ColumnElement,
        is_page: bool,
    ) -> Any:
        """
        主体分页列表。

        可见性由 owner_scope（登记归属中队）或名下车辆在本中队分管共同决定；
        「名下车辆」数量展示该主体跨中队的全部在管车辆，与详情页口径保持一致。
        """
        result = await TruckOwnerDao.get_list(db, query, owner_scope, vehicle_scope, is_page)
        rows = result.rows if hasattr(result, 'rows') else result
        owner_ids = [row['ownerId'] for row in rows]
        vehicle_counts = await TruckOwnerDao.count_vehicles_by_owner_ids(db, owner_ids)
        for row in rows:
            row['vehicleCount'] = vehicle_counts.get(row['ownerId'], 0)
        return result

    @classmethod
    async def detail(
        cls,
        db: AsyncSession,
        owner_id: int,
        owner_scope: ColumnElement | None = None,
        vehicle_scope: ColumnElement | None = None,
    ) -> TruckOwnerModel:
        """
        主体详情。

        「名下车辆」由车辆列表接口按 ownerId 查询，该查询已允许跨中队可见
        （见 TruckOwnerDao.get_list 的 linked_vehicle_visible 逻辑），
        因此这里只返回主体本身，不再嵌套车辆以避免循环依赖。
        """
        owner = await TruckOwnerDao.get_by_id(db, owner_id, owner_scope, vehicle_scope)
        if not owner:
            raise ServiceException(message='归属主体不存在或无权访问')
        return TruckOwnerModel.model_validate(owner)

    @classmethod
    async def _check_unique(cls, db: AsyncSession, owner: TruckOwnerModel) -> None:
        existing = await TruckOwnerDao.get_by_identity(db, owner)
        if existing and existing.owner_id != owner.owner_id:
            raise ServiceException(message='统一社会信用代码或身份证号已存在')

    @classmethod
    async def add(cls, db: AsyncSession, owner: TruckOwnerModel) -> CrudResponseModel:
        await cls._check_unique(db, owner)
        try:
            await TruckOwnerDao.add(db, owner)
            await db.commit()
            return CrudResponseModel(is_success=True, message='新增成功')
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def edit(cls, db: AsyncSession, owner: TruckOwnerModel) -> CrudResponseModel:
        await cls.detail(db, owner.owner_id)
        await cls._check_unique(db, owner)
        try:
            await TruckOwnerDao.update(db, owner)
            await db.commit()
            return CrudResponseModel(is_success=True, message='更新成功')
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def delete(
        cls, db: AsyncSession, request: DeleteTruckOwnerModel, user_name: str, update_time: datetime
    ) -> CrudResponseModel:
        try:
            for owner_id in request.owner_ids.split(','):
                owner = await cls.detail(db, int(owner_id))
                if await TruckOwnerDao.count_vehicles(db, owner.owner_id):
                    raise ServiceException(message=f'{owner.owner_name}名下仍有关联车辆，不能删除')
                await TruckOwnerDao.delete(db, owner.owner_id, user_name, update_time)
            await db.commit()
            return CrudResponseModel(is_success=True, message='删除成功')
        except Exception:
            await db.rollback()
            raise
