"""
GA/T1400 订阅管理：创建订阅、取消订阅、到期续订。

报文结构对照大华《公安视频图像信息数据库对接协议 V1.2》"订阅相关接口"：
- 批量订阅 POST /VIID/Subscribes，消息体为 SubscribeListObject.SubscribeObject[]
- 取消订阅 PUT /VIID/Subscribes/<ID>，消息体为 SubscribeObject（含取消单位/人/时间/原因）
- 时间字段统一 yyyyMMddHHmmss

SubscribeID 生成规则（参考大华示例 330101020001032017113010580006371）：
机构代码 + '03'（订阅子类型） + yyyyMMddHHmmss + 5位流水号。
我方无 12 位机构代码，使用 20 位 DeviceID 作为机构代码段，联调时按对方要求调整。
"""

import uuid
from datetime import datetime, timedelta

from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from module_gat1400.dao.gat1400_subscribe_dao import Gat1400SubscribeDao
from module_gat1400.entity.do.gat1400_subscribe_do import Gat1400Subscribe
from module_gat1400.service.gat1400_config_service import Gat1400ConfigService
from module_gat1400.service.gat1400_digest_client import Gat1400DigestClient
from module_gat1400.service.gat1400_session_service import HTTP_STATUS_OK, Gat1400SessionService, _extract_status_code
from utils.log_util import logger

SUBSCRIBE_URI = '/VIID/Subscribes'

# 订阅序列号 Redis 键
SUBSCRIBE_SEQ_KEY = 'gat1400:subscribe:seq'
# 订阅到期前多久触发续订（秒）
RENEW_BEFORE_SECONDS = 86400
RENEW_LOCK_KEY = 'gat1400:subscribe:renew:lock'
RENEW_LOCK_TTL = 60
# 默认订阅标题
DEFAULT_TITLE = '过车'

DATETIME_FORMAT = '%Y%m%d%H%M%S'


def format_time(dt: datetime) -> str:
    """大华时间格式 yyyyMMddHHmmss。"""
    return dt.strftime(DATETIME_FORMAT)


def parse_time(value: str) -> datetime | None:
    """解析大华时间格式，非法值返回 None。"""
    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except (TypeError, ValueError):
        return None


def _extract_response_id(body: dict | None) -> str | None:
    """从平台响应提取返回的资源 ID（兼容对象/列表及 ResponseStatusListObject 包装形式）。"""
    if not isinstance(body, dict):
        return None
    status_object = body.get('ResponseStatusObject')
    if status_object is None and isinstance(body.get('ResponseStatusListObject'), dict):
        status_object = body['ResponseStatusListObject'].get('ResponseStatusObject')
    if isinstance(status_object, list):
        status_object = status_object[0] if status_object else None
    if isinstance(status_object, dict):
        value = status_object.get('Id')
        return str(value) if value is not None else None
    return None


class Gat1400SubscribeService:
    @classmethod
    def _subscribe_id(cls, device_id: str, seq: int) -> str:
        now = datetime.now()
        return f'{device_id}03{now.strftime(DATETIME_FORMAT)}{seq % 100000:05d}'

    @classmethod
    def build_subscribe_message(
        cls, subscribe_id: str, begin_time: datetime, end_time: datetime, config: dict[str, str]
    ) -> dict:
        """
        构建大华批量订阅消息体：SubscribeListObject.SubscribeObject[]
        :param config: 运行时配置（来自 Gat1400ConfigService.get_runtime_config）
        """
        return {
            'SubscribeListObject': {
                'SubscribeObject': [
                    {
                        'SubscribeID': subscribe_id,
                        'Title': DEFAULT_TITLE,
                        'SubscribeDetail': config['subscribe_detail'],
                        'ResourceURI': config['subscribe_resource_uri'],
                        'ApplicantName': config['applicant_name'],
                        'ApplicantOrg': config['applicant_org'],
                        'BeginTime': format_time(begin_time),
                        'EndTime': format_time(end_time),
                        'OperateType': '0',
                        'Reason': '大货车过车记录订阅',
                        'ReceiveAddr': config['receive_addr'],
                    }
                ]
            }
        }

    @classmethod
    def build_cancel_message(cls, config: dict[str, str]) -> dict:
        """构建取消订阅消息体：SubscribeObject 含取消单位/人/时间/原因。"""
        return {
            'SubscribeObject': {
                'SubscribeCancelOrg': config.get('applicant_org', ''),
                'SubscribeCancelPerson': config.get('applicant_name', ''),
                'CancelTime': format_time(datetime.now()),
                'CancelReason': '服务到期',
            }
        }

    @classmethod
    async def create_subscribe(cls, db: AsyncSession, redis: aioredis.Redis) -> Gat1400Subscribe | None:
        """
        创建订阅。成功返回订阅记录（subscribe_id 以平台返回的 Id 为准），失败返回 None。
        配置动态读取：sys_config（Redis 缓存）优先，回退 .env。
        """
        config = await Gat1400ConfigService.get_runtime_config(redis)
        if not config['receive_addr']:
            logger.warning('⚠️ 未配置回调地址（gat1400.subscribe.receive.addr），跳过订阅')
            return None
        client = await Gat1400SessionService._get_client(db, redis)
        if not client:
            return None
        seq = int(await redis.incr(SUBSCRIBE_SEQ_KEY)) if redis else 1
        subscribe_id = cls._subscribe_id(client.device_id, seq)
        begin_time = datetime.now()
        try:
            end_time = begin_time + timedelta(days=int(config['subscribe_days']))
        except (TypeError, ValueError):
            end_time = begin_time + timedelta(days=30)
        try:
            response = await client.post(
                SUBSCRIBE_URI, json_body=cls.build_subscribe_message(subscribe_id, begin_time, end_time, config)
            )
            body = Gat1400DigestClient.parse_response_body(response)
            success = response.status_code == HTTP_STATUS_OK and _extract_status_code(body) == 0
        except Exception as e:
            logger.error(f'❌ GA/T1400 订阅请求异常: {e}')
            return None
        if not success:
            logger.warning(f'⚠️ GA/T1400 订阅失败: HTTP {response.status_code} {body}')
            return None
        # 以平台返回的 Id 为准（ResponseStatusObject 可能为对象或列表）
        returned_id = _extract_response_id(body) or subscribe_id
        record = await Gat1400SubscribeDao.add(
            db,
            subscribe_id=returned_id,
            title=DEFAULT_TITLE,
            subscribe_detail=config['subscribe_detail'],
            resource_uri=config['subscribe_resource_uri'],
            applicant_name=config['applicant_name'],
            applicant_org=config['applicant_org'],
            begin_time=begin_time,
            end_time=end_time,
            receive_addr=config['receive_addr'],
            operate_type='0',
            subscribe_status='0',
            create_by='system',
        )
        await db.commit()
        logger.info(f'✅ GA/T1400 订阅创建成功: {returned_id}')
        return record

    @classmethod
    async def cancel_subscribe(
        cls, db: AsyncSession, redis: aioredis.Redis | None = None, subscribe_id: str | None = None
    ) -> bool:
        """
        取消订阅。未指定 subscribe_id 时取消当前有效订阅。
        """
        config = await Gat1400ConfigService.get_runtime_config(redis) if redis else None
        client = await Gat1400SessionService._get_client(db, redis)
        if not client:
            return False
        record = (
            await Gat1400SubscribeDao.get_by_id(db, subscribe_id)
            if subscribe_id
            else await Gat1400SubscribeDao.get_active_subscribe(db)
        )
        if not record:
            return False
        try:
            response = await client.put(
                f'{SUBSCRIBE_URI}/{record.subscribe_id}',
                json_body=cls.build_cancel_message(config or {}),
            )
            body = Gat1400DigestClient.parse_response_body(response)
            success = response.status_code == HTTP_STATUS_OK and _extract_status_code(body) == 0
        except Exception as e:
            logger.error(f'❌ GA/T1400 取消订阅请求异常: {e}')
            success = False
        await Gat1400SubscribeDao.update(
            db,
            record.subscribe_id,
            subscribe_status='1' if success else record.subscribe_status,
            cancel_org=(config or {}).get('applicant_org', ''),
            cancel_person=(config or {}).get('applicant_name', ''),
            cancel_time=datetime.now(),
            cancel_reason='服务到期',
        )
        await db.commit()
        if success:
            logger.info(f'✅ GA/T1400 订阅已取消: {record.subscribe_id}')
        return success

    @classmethod
    async def ensure_subscribe(cls, db: AsyncSession, redis: aioredis.Redis) -> None:
        """
        在线状态下确保存在有效订阅：无有效订阅或临近到期时创建新订阅。
        由会话巡检任务在 ONLINE 状态调用。
        """
        lock_value = uuid.uuid4().hex
        if not await redis.set(RENEW_LOCK_KEY, lock_value, nx=True, ex=RENEW_LOCK_TTL):
            return
        try:
            # 获取锁后重新查询，避免多 worker/多 tick 在同一窗口重复订阅。
            active = await Gat1400SubscribeDao.get_active_subscribe(db)
            if active and active.end_time > datetime.now() + timedelta(seconds=RENEW_BEFORE_SECONDS):
                return
            if active:
                logger.info(f'⏰ GA/T1400 订阅 {active.subscribe_id} 临近到期，自动续订')
            renewed = await cls.create_subscribe(db, redis)
            if renewed and active:
                # 新订阅创建成功后再取消旧订阅，避免续订过程出现推送空窗。
                cancelled = await cls.cancel_subscribe(db, redis, active.subscribe_id)
                if not cancelled:
                    logger.warning(f'⚠️ GA/T1400 新订阅已创建，但旧订阅取消失败: {active.subscribe_id}')
        finally:
            if await redis.get(RENEW_LOCK_KEY) == lock_value:
                await redis.delete(RENEW_LOCK_KEY)
