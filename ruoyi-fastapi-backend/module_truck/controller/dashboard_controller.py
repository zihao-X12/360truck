from typing import Annotated

from fastapi import Request, Response
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from common.aspect.data_scope import DataScopeDependency
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from common.vo import DataResponseModel
from module_truck.entity.do.truck_do import TruckOwner, TruckVehicle
from module_truck.entity.vo.dashboard_vo import TruckDashboardSummaryModel, TruckDeptStatModel, TruckDeviceCoverageModel
from module_truck.service.dashboard_service import TruckDashboardService
from utils.response_util import ResponseUtil

dashboard_controller = APIRouterPro(prefix='/truck/dashboard', order_num=29, tags=['大货车管理-业务看板'], dependencies=[PreAuthDependency()])


@dashboard_controller.get('/summary', response_model=DataResponseModel[TruckDashboardSummaryModel], dependencies=[UserInterfaceAuthDependency('truck:dashboard:list')])
async def get_dashboard_summary(
    request: Request,
    db: Annotated[AsyncSession, DBSessionDependency()],
    vehicle_scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
    owner_scope: Annotated[ColumnElement, DataScopeDependency(TruckOwner)],
) -> Response:
    return ResponseUtil.success(data=await TruckDashboardService.get_summary(db, vehicle_scope, owner_scope))


@dashboard_controller.get('/dept-stat', response_model=DataResponseModel[list[TruckDeptStatModel]], dependencies=[UserInterfaceAuthDependency('truck:dashboard:list')])
async def get_dashboard_dept_stat(
    request: Request,
    db: Annotated[AsyncSession, DBSessionDependency()],
    vehicle_scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
    owner_scope: Annotated[ColumnElement, DataScopeDependency(TruckOwner)],
) -> Response:
    return ResponseUtil.success(data=await TruckDashboardService.get_dept_stats(db, vehicle_scope, owner_scope))


@dashboard_controller.get('/device-coverage', response_model=DataResponseModel[list[TruckDeviceCoverageModel]], dependencies=[UserInterfaceAuthDependency('truck:dashboard:list')])
async def get_dashboard_device_coverage(
    request: Request,
    db: Annotated[AsyncSession, DBSessionDependency()],
    vehicle_scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
) -> Response:
    return ResponseUtil.success(data=await TruckDashboardService.get_device_coverage(db, vehicle_scope))
