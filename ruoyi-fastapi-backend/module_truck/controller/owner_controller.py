from datetime import datetime
from typing import Annotated

from fastapi import Path, Query, Request, Response
from pydantic_validation_decorator import ValidateFields
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.data_scope import DataScopeDependency
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import CurrentUserDependency, PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel, PageResponseModel, ResponseBaseModel
from module_admin.entity.do.dept_do import SysDept
from module_admin.entity.vo.user_vo import CurrentUserModel
from module_admin.service.dept_service import DeptService
from module_truck.entity.do.truck_do import TruckOwner
from module_truck.entity.vo.owner_vo import DeleteTruckOwnerModel, TruckOwnerModel, TruckOwnerPageQueryModel
from module_truck.service.owner_service import TruckOwnerService
from utils.response_util import ResponseUtil

owner_controller = APIRouterPro(prefix='/truck/owner', order_num=30, tags=['大货车管理-归属主体'], dependencies=[PreAuthDependency()])


@owner_controller.get('/list', response_model=PageResponseModel[TruckOwnerModel], dependencies=[UserInterfaceAuthDependency('truck:owner:query')])
async def get_owner_list(request: Request, query: Annotated[TruckOwnerPageQueryModel, Query()], db: Annotated[AsyncSession, DBSessionDependency()], scope: Annotated[ColumnElement, DataScopeDependency(TruckOwner)]) -> Response:
    return ResponseUtil.success(model_content=await TruckOwnerService.get_list(db, query, scope, True))


@owner_controller.get('/{owner_id}', response_model=DataResponseModel[TruckOwnerModel], dependencies=[UserInterfaceAuthDependency('truck:owner:query')])
async def get_owner_detail(request: Request, owner_id: Annotated[int, Path()], db: Annotated[AsyncSession, DBSessionDependency()], scope: Annotated[ColumnElement, DataScopeDependency(TruckOwner)]) -> Response:
    return ResponseUtil.success(data=await TruckOwnerService.detail(db, owner_id, scope))


@owner_controller.post('', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:owner:add')])
@ValidateFields(validate_model='owner')
@Log(title='大货车归属主体', business_type=BusinessType.INSERT)
async def add_owner(request: Request, owner: TruckOwnerModel, db: Annotated[AsyncSession, DBSessionDependency()], current_user: Annotated[CurrentUserModel, CurrentUserDependency()], dept_scope: Annotated[ColumnElement, DataScopeDependency(SysDept)]) -> Response:
    await DeptService.check_dept_data_scope_services(db, owner.dept_id, dept_scope)
    owner.create_by = owner.update_by = current_user.user.user_name
    owner.create_time = owner.update_time = datetime.now()
    return ResponseUtil.success(msg=(await TruckOwnerService.add(db, owner)).message)


@owner_controller.put('', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:owner:edit')])
@ValidateFields(validate_model='owner')
@Log(title='大货车归属主体', business_type=BusinessType.UPDATE)
async def edit_owner(request: Request, owner: TruckOwnerModel, db: Annotated[AsyncSession, DBSessionDependency()], current_user: Annotated[CurrentUserModel, CurrentUserDependency()], dept_scope: Annotated[ColumnElement, DataScopeDependency(SysDept)]) -> Response:
    await DeptService.check_dept_data_scope_services(db, owner.dept_id, dept_scope)
    owner.update_by, owner.update_time = current_user.user.user_name, datetime.now()
    return ResponseUtil.success(msg=(await TruckOwnerService.edit(db, owner)).message)


@owner_controller.delete('/{owner_ids}', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:owner:remove')])
@Log(title='大货车归属主体', business_type=BusinessType.DELETE)
async def delete_owner(request: Request, owner_ids: Annotated[str, Path()], db: Annotated[AsyncSession, DBSessionDependency()], current_user: Annotated[CurrentUserModel, CurrentUserDependency()], scope: Annotated[ColumnElement, DataScopeDependency(TruckOwner)]) -> Response:
    for owner_id in owner_ids.split(','):
        await TruckOwnerService.detail(db, int(owner_id), scope)
    result = await TruckOwnerService.delete(db, DeleteTruckOwnerModel(ownerIds=owner_ids), current_user.user.user_name, datetime.now())
    return ResponseUtil.success(msg=result.message)
