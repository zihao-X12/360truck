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
from common.vo import PageResponseModel
from module_gat1400.entity.vo.pass_record_vo import PassRecordModel, PassRecordPageQueryModel
from module_gat1400.service.pass_record_service import PassRecordService
from module_truck.entity.do.truck_do import TruckVehicle
from utils.common_util import bytes2file_response
from utils.response_util import ResponseUtil

pass_record_controller = APIRouterPro(
    prefix='/truck/passrecord', order_num=30, tags=['大货车管理-过车记录'], dependencies=[PreAuthDependency()]
)


@pass_record_controller.get(
    '/list',
    response_model=PageResponseModel[PassRecordModel],
    dependencies=[UserInterfaceAuthDependency('truck:passrecord:query')],
)
async def get_pass_record_list(
    request: Request,
    query: Annotated[PassRecordPageQueryModel, Query()],
    db: Annotated[AsyncSession, DBSessionDependency()],
    scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
) -> Response:
    """
    过车记录分页查询：车牌号、设备、过车时间范围、是否本平台车辆。
    数据权限：中队管理员仅可见关联本中队车辆档案的记录，大队管理员/领导可见全部。
    """
    return ResponseUtil.success(model_content=await PassRecordService.get_list(db, query, scope, True))


@pass_record_controller.post(
    '/export', response_class=StreamingResponse, dependencies=[UserInterfaceAuthDependency('truck:passrecord:export')]
)
@Log(title='大货车管理-过车记录', business_type=BusinessType.EXPORT)
async def export_pass_records(
    request: Request,
    query: Annotated[PassRecordPageQueryModel, Form()],
    db: Annotated[AsyncSession, DBSessionDependency()],
    scope: Annotated[ColumnElement, DataScopeDependency(TruckVehicle)],
) -> Response:
    """按查询条件导出过车记录 Excel。"""
    records = await PassRecordService.get_list(db, query, scope, False)
    return ResponseUtil.streaming(
        data=bytes2file_response(PassRecordService.export_pass_records(records)),
        headers={'Download-Filename': f'truck_pass_records_{query.plate_no or "all"}.xlsx'},
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
