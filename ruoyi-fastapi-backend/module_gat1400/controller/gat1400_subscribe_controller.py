from typing import Annotated

from fastapi import Path, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel
from module_gat1400.entity.do.gat1400_subscribe_do import Gat1400Subscribe
from module_gat1400.service.gat1400_subscribe_service import Gat1400SubscribeService
from utils.common_util import CamelCaseUtil
from utils.response_util import ResponseUtil

gat1400_subscribe_controller = APIRouterPro(
    prefix='/gat1400/subscribe', order_num=29, tags=['GA/T1400对接'], dependencies=[PreAuthDependency()]
)


@gat1400_subscribe_controller.get(
    '/list', response_model=DataResponseModel, dependencies=[UserInterfaceAuthDependency('gat1400:connect:query')]
)
async def list_subscribes(request: Request, db: Annotated[AsyncSession, DBSessionDependency()]) -> Response:
    """查询订阅列表（含历史订阅记录）。"""
    statement = (
        select(Gat1400Subscribe).where(Gat1400Subscribe.del_flag == '0').order_by(Gat1400Subscribe.create_time.desc())
    )
    records = (await db.execute(statement)).scalars().all()
    return ResponseUtil.success(data=CamelCaseUtil.transform_result(records))


@gat1400_subscribe_controller.post(
    '/create', response_model=DataResponseModel, dependencies=[UserInterfaceAuthDependency('gat1400:connect:operate')]
)
@Log(title='GA/T1400对接', business_type=BusinessType.OTHER)
async def create_subscribe(request: Request, db: Annotated[AsyncSession, DBSessionDependency()]) -> Response:
    """手动创建订阅。"""
    record = await Gat1400SubscribeService.create_subscribe(db, request.app.state.redis)
    if not record:
        return ResponseUtil.error(msg='订阅失败，请检查对接状态与配置')
    return ResponseUtil.success(msg=f'订阅创建成功: {record.subscribe_id}', data={'subscribeId': record.subscribe_id})


@gat1400_subscribe_controller.put(
    '/cancel/{subscribe_id}',
    response_model=DataResponseModel,
    dependencies=[UserInterfaceAuthDependency('gat1400:connect:operate')],
)
@Log(title='GA/T1400对接', business_type=BusinessType.OTHER)
async def cancel_subscribe(
    request: Request, db: Annotated[AsyncSession, DBSessionDependency()], subscribe_id: Annotated[str, Path()]
) -> Response:
    """取消指定订阅。"""
    success = await Gat1400SubscribeService.cancel_subscribe(db, request.app.state.redis, subscribe_id)
    return ResponseUtil.success(msg='订阅已取消' if success else '取消失败，请检查对接状态与订阅ID')
