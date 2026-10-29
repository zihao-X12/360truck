from typing import Annotated

from fastapi import Request, Response
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession

from common.annotation.log_annotation import Log
from common.aspect.db_seesion import DBSessionDependency
from common.aspect.interface_auth import UserInterfaceAuthDependency
from common.aspect.pre_auth import PreAuthDependency
from common.enums import BusinessType
from common.router import APIRouterPro
from common.vo import DataResponseModel
from module_gat1400.service.gat1400_config_service import Gat1400ConfigService
from utils.response_util import ResponseUtil

gat1400_config_controller = APIRouterPro(
    prefix='/gat1400/config', order_num=28, tags=['GA/T1400对接'], dependencies=[PreAuthDependency()]
)


class Gat1400ConfigModel(BaseModel):
    """对接配置入参（password 传空或 ******** 表示不修改）。"""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    enabled: bool | None = None
    platform_addr: str | None = None
    device_id: str | None = None
    username: str | None = None
    password: str | None = None
    keepalive_interval: int | None = None
    subscribe_detail: str | None = None
    subscribe_resource_uri: str | None = None
    applicant_name: str | None = None
    applicant_org: str | None = None
    subscribe_days: int | None = None
    receive_addr: str | None = None
    notify_allowed_ips: str | None = None


@gat1400_config_controller.get(
    '', response_model=DataResponseModel, dependencies=[UserInterfaceAuthDependency('gat1400:connect:query')]
)
async def get_gat1400_config(request: Request, db: Annotated[AsyncSession, DBSessionDependency()]) -> Response:
    """
    读取对接配置（密码脱敏回显：password=******** / passwordSet 标记是否已配置）。
    """
    return ResponseUtil.success(data=await Gat1400ConfigService.get_config_for_api(db))


@gat1400_config_controller.put(
    '', response_model=DataResponseModel, dependencies=[UserInterfaceAuthDependency('gat1400:connect:operate')]
)
@Log(title='GA/T1400对接', business_type=BusinessType.UPDATE)
async def save_gat1400_config(
    request: Request, config: Gat1400ConfigModel, db: Annotated[AsyncSession, DBSessionDependency()]
) -> Response:
    """
    保存对接配置（立即生效：写入 sys_config 并刷新 Redis 缓存，下次心跳使用新配置）。
    """
    params = config.model_dump(exclude_none=True, by_alias=False)
    await Gat1400ConfigService.save_config(db, request.app.state.redis, params)
    return ResponseUtil.success(msg='配置保存成功，将在下一次心跳巡检时生效')
