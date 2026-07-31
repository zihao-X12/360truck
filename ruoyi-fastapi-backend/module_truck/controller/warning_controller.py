from typing import Annotated

from fastapi import Form, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import ColumnElement
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.data_scope import DataScopeDependency
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import PageResponseModel, ResponseBaseModel
from module_truck.entity.do.truck_do import TruckVehicle
from module_truck.entity.vo.warning_vo import TruckWarningModel, TruckWarningPageQueryModel
from module_truck.service.warning_service import TruckWarningService
from utils.common_util import bytes2file_response
from utils.response_util import ResponseUtil

warning_controller = APIRouterPro(prefix='/truck/warning', order_num=32, tags=['大货车管理-重点监管预警'], dependencies=[PreAuthDependency()])


@warning_controller.get('/list', response_model=PageResponseModel[TruckWarningModel], dependencies=[UserInterfaceAuthDependency('truck:warning:query')])
async def get_warning_list(
    request: Request,
    query: Annotated[TruckWarningPageQueryModel, Query()],
    db: Annotated[AsyncSession, DBSessionDependency()],
    scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
) -> Response:
    return ResponseUtil.success(model_content=await TruckWarningService.get_list(db, query, scope, True))


@warning_controller.post('/recalculate', response_model=ResponseBaseModel, dependencies=[UserInterfaceAuthDependency('truck:warning:recalculate')])
@Log(title='重点监管预警', business_type=BusinessType.UPDATE)
async def recalculate_warnings(
    request: Request,
    db: Annotated[AsyncSession, DBSessionDependency()],
    scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
) -> Response:
    result = await TruckWarningService.recalculate(db, scope)
    return ResponseUtil.success(msg=result.message, data=result.result)


@warning_controller.post('/export', response_class=StreamingResponse, dependencies=[UserInterfaceAuthDependency('truck:warning:export')])
@Log(title='重点监管预警', business_type=BusinessType.EXPORT)
async def export_warnings(
    request: Request,
    query: Annotated[TruckWarningPageQueryModel, Form()],
    db: Annotated[AsyncSession, DBSessionDependency()],
    scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
) -> Response:
    rows = await TruckWarningService.get_list(db, query, scope, False)
    return ResponseUtil.streaming(
        data=bytes2file_response(TruckWarningService.export_warnings(rows)),
        headers={'Download-Filename': 'truck_warnings.xlsx'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
