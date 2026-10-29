from datetime import datetime
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel
from exceptions.exception import ServiceException
from module_admin.entity.do.dept_do import SysDept
from module_truck.dao.owner_dao import TruckOwnerDao
from module_truck.dao.vehicle_dao import TruckVehicleDao
from module_truck.entity.vo.vehicle_vo import (
    DeleteTruckVehicleModel,
    TruckVehicleDeviceModel,
    TruckVehicleModel,
    TruckVehiclePageQueryModel,
)


class TruckVehicleService:
    @classmethod
    async def get_list(
        cls,
        db: AsyncSession,
        query: TruckVehiclePageQueryModel,
        scope: ColumnElement,
        is_page: bool,
        owner_scope: ColumnElement | None = None,
    ) -> Any:
        """
        车辆分页列表。

        普通查询按车辆分管中队隔离；按主体（ownerId）查询时跨中队展示该主体名下
        全部车辆，与主体列表的「名下车辆」口径一致。跨中队读取前先校验主体可见性
        （主体登记在本中队，或本中队分管其名下车辆），避免借 ownerId 越权。
        结果补充分管中队名称，便于识别每辆车的归属。
        """
        if query.owner_id and owner_scope is not None:
            owner = await TruckOwnerDao.get_by_id(db, query.owner_id, owner_scope, scope)
            if not owner:
                raise ServiceException(message='归属主体不存在或无权访问')
        result = await TruckVehicleDao.get_list(db, query, scope, is_page)
        rows = result.rows if hasattr(result, 'rows') else result
        dept_ids = {row['deptId'] for row in rows if row.get('deptId')}
        if dept_ids:
            dept_names = dict((await db.execute(select(SysDept.dept_id, SysDept.dept_name).where(SysDept.dept_id.in_(dept_ids)))).all())
            for row in rows:
                row['deptName'] = dept_names.get(row.get('deptId'))
        return result

    @classmethod
    async def detail(cls, db: AsyncSession, vehicle_id: int, scope: ColumnElement | None = None) -> TruckVehicleModel:
        vehicle = await TruckVehicleDao.get_by_id(db, vehicle_id, scope)
        if not vehicle:
            raise ServiceException(message='车辆不存在或无权访问')
        result = TruckVehicleModel.model_validate(vehicle)
        result.devices = [
            TruckVehicleDeviceModel.model_validate(device) for device in await TruckVehicleDao.get_devices(db, vehicle_id)
        ]
        return result

    @classmethod
    async def _check_unique(cls, db: AsyncSession, vehicle: TruckVehicleModel) -> None:
        plate = await TruckVehicleDao.get_by_plate(db, vehicle.plate_no, vehicle.plate_color)
        if plate and plate.vehicle_id != vehicle.vehicle_id:
            raise ServiceException(message=f'车牌号{vehicle.plate_no}和车牌颜色组合已存在')
        if vehicle.vin:
            vin = await TruckVehicleDao.get_by_vin(db, vehicle.vin)
            if vin and vin.vehicle_id != vehicle.vehicle_id:
                raise ServiceException(message=f'车架号{vehicle.vin}已存在')

    @classmethod
    async def _resolve_owner(cls, db: AsyncSession, vehicle: TruckVehicleModel) -> None:
        if not vehicle.owner_id:
            vehicle.owner_type = None
            return
        owner = await TruckOwnerDao.get_by_id(db, vehicle.owner_id)
        if not owner:
            raise ServiceException(message='关联归属主体不存在')
        vehicle.owner_type = owner.owner_type

    @classmethod
    async def _validate_devices(cls, vehicle: TruckVehicleModel) -> None:
        device_types = [device.device_type for device in vehicle.devices]
        if len(device_types) != len(set(device_types)):
            raise ServiceException(message='同一车辆不能重复添加同类安全设备')

    @classmethod
    async def add(cls, db: AsyncSession, vehicle: TruckVehicleModel) -> CrudResponseModel:
        await cls._check_unique(db, vehicle)
        await cls._resolve_owner(db, vehicle)
        await cls._validate_devices(vehicle)
        try:
            record = await TruckVehicleDao.add(db, vehicle)
            vehicle_id = record.vehicle_id
            await TruckVehicleDao.replace_devices(db, vehicle_id, vehicle.devices, vehicle.create_by or '')
            await db.commit()
            return CrudResponseModel(is_success=True, message='新增成功', result={'vehicleId': vehicle_id})
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def edit(cls, db: AsyncSession, vehicle: TruckVehicleModel) -> CrudResponseModel:
        current = await TruckVehicleDao.get_by_id(db, vehicle.vehicle_id)
        if not current:
            raise ServiceException(message='车辆不存在')
        if current.vehicle_status in {'transferred', 'scrapped'}:
            raise ServiceException(message='车辆已转出或报废，不能继续编辑')
        await cls._check_unique(db, vehicle)
        await cls._resolve_owner(db, vehicle)
        await cls._validate_devices(vehicle)
        try:
            await TruckVehicleDao.update(db, vehicle)
            await TruckVehicleDao.replace_devices(db, vehicle.vehicle_id, vehicle.devices, vehicle.update_by or '')
            if current.owner_id != vehicle.owner_id or current.dept_id != vehicle.dept_id:
                await TruckVehicleDao.add_history(db, vehicle.vehicle_id, current.owner_id, vehicle.owner_id, current.dept_id, vehicle.dept_id, vehicle.change_reason, vehicle.update_by or '')
            await db.commit()
            return CrudResponseModel(is_success=True, message='更新成功')
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def delete(
        cls, db: AsyncSession, request: DeleteTruckVehicleModel, user_name: str, update_time: datetime
    ) -> CrudResponseModel:
        try:
            for vehicle_id in request.vehicle_ids.split(','):
                vehicle = await cls.detail(db, int(vehicle_id))
                await TruckVehicleDao.soft_delete(db, vehicle.vehicle_id, user_name, update_time)
            await db.commit()
            return CrudResponseModel(is_success=True, message='删除成功')
        except Exception:
            await db.rollback()
            raise
