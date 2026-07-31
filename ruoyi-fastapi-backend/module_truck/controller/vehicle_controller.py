import base64
from datetime import datetime
from typing import Annotated

from fastapi import File, Form, Path, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic_validation_decorator import ValidateFields
from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.data_scope import DataScopeDependency
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from exceptions.exception import ServiceException
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.dept_service import DeptService
from module_truck.dao.vehicle_dao import TruckVehicleDao
from module_truck.entity.do.truck_do import TruckVehicle
from module_truck.entity.vo.vehicle_vo import DeleteTruckVehicleModel, TruckVehicleModel, TruckVehiclePageQueryModel
from module_truck.service.vehicle_import_service import TruckVehicleImportService
from module_truck.service.vehicle_service import TruckVehicleService
from utils.common_util import bytes2file_response
from utils.response_util import ResponseUtil

vehicle_controller = APIRouterPro(prefix='/truck/vehicle', order_num=31, tags=['大货车管理-车辆档案'], dependencies=[PreAuthDependency()])


@vehicle_controller.get('/list', response_model=PageResponseModel[TruckVehicleModel], dependencies=[UserInterfaceAuthDependency('truck:vehicle:query')])
async def get_vehicle_list(request: Request, query: Annotated[TruckVehiclePageQueryModel, Query()], db: Annotated[AsyncSession, DBSessionDependency()], scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)]) -> Response:
    return ResponseUtil.success(model_content=await TruckVehicleService.get_list(db, query, scope, True))


@vehicle_controller.get('/import-template', response_class=StreamingResponse, dependencies=[UserInterfaceAuthDependency('truck:vehicle:import')])
@vehicle_controller.post('/import-template', response_class=StreamingResponse, dependencies=[UserInterfaceAuthDependency('truck:vehicle:import')])
async def download_vehicle_import_template(request: Request) -> Response:
    return ResponseUtil.streaming(
        data=bytes2file_response(TruckVehicleImportService.get_template()),
        headers={'Download-Filename': 'truck_vehicle_import_template.xlsx'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@vehicle_controller.post('/import', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:vehicle:import')])
@Log(title='大货车车辆档案', business_type=BusinessType.IMPORT)
async def import_vehicles(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, DBSessionDependency()],
    current_user: Annotated[CurrentUserModel, CurrentUserDependency()],
    dept_scope: Annotated[ColumnElement, DataScopeDependency(SysDept)],
) -> Response:
    result = await TruckVehicleImportService.import_file(
        db, request.app.state.redis, file, current_user.user.user_name, dept_scope
    )
    message = f"成功导入{result['successCount']}行"
    if result['errorCount']:
        message += f"，失败{result['errorCount']}行"
    return ResponseUtil.success(msg=message, data=result)


@vehicle_controller.get('/import-error/{batch_id}', response_class=StreamingResponse, dependencies=[UserInterfaceAuthDependency('truck:vehicle:import')])
async def download_vehicle_import_errors(request: Request, batch_id: Annotated[str, Path()]) -> Response:
    cached = await request.app.state.redis.get(f'{TruckVehicleImportService.ERROR_CACHE_PREFIX}:{batch_id}')
    if not cached:
        raise ServiceException(message='错误文件不存在或已过期，请重新导入')
    return ResponseUtil.streaming(
        data=bytes2file_response(base64.b64decode(cached)),
        headers={'Download-Filename': f'truck_vehicle_import_errors_{batch_id}.xlsx'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@vehicle_controller.post('/export', response_class=StreamingResponse, dependencies=[UserInterfaceAuthDependency('truck:vehicle:export')])
@Log(title='大货车车辆档案', business_type=BusinessType.EXPORT)
async def export_vehicles(
    request: Request,
    query: Annotated[TruckVehiclePageQueryModel, Form()],
    db: Annotated[AsyncSession, DBSessionDependency()],
    scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
) -> Response:
    vehicles = await TruckVehicleService.get_list(db, query, scope, False)
    departments = {
        record.dept_id: record.dept_name
        for record in (await db.execute(select(SysDept).where(SysDept.del_flag == '0'))).scalars().all()
    }
    device_types = await TruckVehicleDao.get_device_types(db, [item['vehicleId'] for item in vehicles])
    for vehicle in vehicles:
        vehicle['deptName'] = departments.get(vehicle.get('deptId'), '')
        installed = device_types.get(vehicle['vehicleId'], set())
        vehicle['brakeAssist'] = '是' if 'brake_assist' in installed else '否'
        vehicle['panoramic360'] = '是' if 'panoramic_360' in installed else '否'
    return ResponseUtil.streaming(
        data=bytes2file_response(TruckVehicleImportService.export_vehicles(vehicles)),
        headers={'Download-Filename': 'truck_vehicles.xlsx'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@vehicle_controller.get('/{vehicle_id}', response_model=DataResponseModel[TruckVehicleModel], dependencies=[UserInterfaceAuthDependency('truck:vehicle:query')])
async def get_vehicle_detail(request: Request, vehicle_id: Annotated[int, Path()], db: Annotated[AsyncSession, DBSessionDependency()], scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)]) -> Response:
    return ResponseUtil.success(data=await TruckVehicleService.detail(db, vehicle_id, scope))


@vehicle_controller.post('', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:vehicle:add')])
@ValidateFields(validate_model='vehicle')
@Log(title='大货车车辆档案', business_type=BusinessType.INSERT)
async def add_vehicle(request: Request, vehicle: TruckVehicleModel, db: Annotated[AsyncSession, DBSessionDependency()], current_user: Annotated[CurrentUserModel, CurrentUserDependency()], dept_scope: Annotated[ColumnElement, DataScopeDependency(SysDept)]) -> Response:
    await DeptService.check_dept_data_scope_services(db, vehicle.dept_id, dept_scope)
    vehicle.create_by = vehicle.update_by = current_user.user.user_name
    vehicle.create_time = vehicle.update_time = datetime.now()
    result = await TruckVehicleService.add(db, vehicle)
    return ResponseUtil.success(msg=result.message, data=result.result)


@vehicle_controller.put('', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:vehicle:edit')])
@ValidateFields(validate_model='vehicle')
@Log(title='大货车车辆档案', business_type=BusinessType.UPDATE)
async def edit_vehicle(request: Request, vehicle: TruckVehicleModel, db: Annotated[AsyncSession, DBSessionDependency()], current_user: Annotated[CurrentUserModel, CurrentUserDependency()], vehicle_scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)], dept_scope: Annotated[ColumnElement, DataScopeDependency(SysDept)]) -> Response:
    await TruckVehicleService.detail(db, vehicle.vehicle_id, vehicle_scope)
    await DeptService.check_dept_data_scope_services(db, vehicle.dept_id, dept_scope)
    vehicle.update_by, vehicle.update_time = current_user.user.user_name, datetime.now()
    return ResponseUtil.success(msg=(await TruckVehicleService.edit(db, vehicle)).message)


@vehicle_controller.delete('/{vehicle_ids}', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:vehicle:remove')])
@Log(title='大货车车辆档案', business_type=BusinessType.DELETE)
async def delete_vehicle(request: Request, vehicle_ids: Annotated[str, Path()], db: Annotated[AsyncSession, DBSessionDependency()], current_user: Annotated[CurrentUserModel, CurrentUserDependency()], scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)]) -> Response:
    for vehicle_id in vehicle_ids.split(','):
        await TruckVehicleService.detail(db, int(vehicle_id), scope)
    result = await TruckVehicleService.delete(db, DeleteTruckVehicleModel(vehicleIds=vehicle_ids), current_user.user.user_name, datetime.now())
    return ResponseUtil.success(msg=result.message)
