from typing import Annotated

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel
from module_gat1400.service.gat1400_session_service import Gat1400SessionService
from utils.response_util import ResponseUtil

gat1400_connect_controller = APIRouterPro(
    prefix='/gat1400/connect', order_num=28, tags=['GA/T1400对接'], dependencies=[PreAuthDependency()]
)


@gat1400_connect_controller.get(
    '/status', response_model=DataResponseModel, dependencies=[UserInterfaceAuthDependency('gat1400:connect:query')]
)
async def get_gat1400_status(request: Request, db: Annotated[AsyncSession, DBSessionDependency()]) -> Response:
    """
    查询GA/T1400对接状态：注册状态、保活时间、失败次数、配置等
    """
    return ResponseUtil.success(data=await Gat1400SessionService.get_status(db, request.app.state.redis))


@gat1400_connect_controller.post(
    '/register', response_model=DataResponseModel, dependencies=[UserInterfaceAuthDependency('gat1400:connect:operate')]
)
@Log(title='GA/T1400对接', business_type=BusinessType.OTHER)
async def manual_register(request: Request, db: Annotated[AsyncSession, DBSessionDependency()]) -> Response:
    """
    手动发起注册（忽略随机重试等待）
    """
    success = await Gat1400SessionService.register(db, request.app.state.redis, force=True)
    return ResponseUtil.success(msg='注册成功' if success else '注册失败，详情见状态接口 errorMessage')


@gat1400_connect_controller.post(
    '/keepalive',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('gat1400:connect:operate')],
)
@Log(title='GA/T1400对接', business_type=BusinessType.OTHER)
async def manual_keepalive(request: Request, db: Annotated[AsyncSession, DBSessionDependency()]) -> Response:
    """
    手动发起保活
    """
    success = await Gat1400SessionService.keepalive(db, request.app.state.redis)
    return ResponseUtil.success(msg='保活成功' if success else '保活失败（可能未在线），详情见状态接口 errorMessage')


@gat1400_connect_controller.post(
    '/unregister',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('gat1400:connect:operate')],
)
@Log(title='GA/T1400对接', business_type=BusinessType.OTHER)
async def manual_unregister(request: Request, db: Annotated[AsyncSession, DBSessionDependency()]) -> Response:
    """
    手动注销对接
    """
    success = await Gat1400SessionService.unregister(db, request.app.state.redis)
    return ResponseUtil.success(msg='注销成功' if success else '注销失败，详情见状态接口 errorMessage')
