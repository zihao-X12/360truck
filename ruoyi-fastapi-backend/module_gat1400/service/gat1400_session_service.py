"""
GA/T1400 对接会话状态机：注册 → 保活 → 注销。

标准依据（GA/T 1400.4—2017）：
- 5.1.1：注册失败时应延迟 300s 内的随机时间后重新注册；注册成功后 90s 内未交互则心跳保活
- 5.2.1/5.3.5：连续多次（3 次）重试失败视为链路问题，缓存信息并重新注册
大华文档补充：注册成功后所有请求携带 User-Identify 头；注册有效期一般为 5 分钟，
任何成功请求都触发保活重置，故默认保活间隔 60s（可配置，需小于 90s 标准要求）。

状态流转：
    unregistered ──register成功──→ online ──keepalive失败3次──→ offline
    offline/unregistered ──到达随机重试时间──→ (registering) → online/offline
    online ──unregister──→ unregistered
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any

from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from config.env import Gat1400Config
from module_gat1400.dao.gat1400_connect_dao import Gat1400ConnectDao
from module_gat1400.service.gat1400_config_service import Gat1400ConfigService
from module_gat1400.service.gat1400_digest_client import Gat1400DigestClient
from utils.log_util import logger

STATUS_UNREGISTERED = 'unregistered'
STATUS_REGISTERING = 'registering'
STATUS_ONLINE = 'online'
STATUS_OFFLINE = 'offline'

REGISTER_URI = '/VIID/System/Register'
UNREGISTER_URI = '/VIID/System/UnRegister'
KEEPALIVE_URI = '/VIID/System/Keepalive'

# 连续保活/注册失败次数上限，达到后按标准要求重新注册
MAX_FAIL_COUNT = 3
# HTTP 成功状态码
HTTP_STATUS_OK = 200
# 注册失败后的随机重试延迟区间（秒），标准要求 300s 内随机
RETRY_DELAY_MIN = 5
RETRY_DELAY_MAX = 300
# tick 分布式锁：多 worker 部署时同一时刻只有一个 worker 执行注册/保活
TICK_LOCK_KEY = 'gat1400:tick:lock'
TICK_LOCK_TTL = 30
# 下次重试时间缓存键（Redis，多 worker 共享）
NEXT_RETRY_KEY = 'gat1400:register:next_retry_at'


def _extract_status_code(body: Any) -> int | None:
    """
    从响应体提取 StatusCode，兼容大华文档中的两种返回形式：
    单对象 {"ResponseStatusObject": {...}}、列表 {"ResponseStatusObject": [...]}，
    以及订阅/通知接口的包装形式 {"ResponseStatusListObject": {"ResponseStatusObject": [...]}}。
    """
    if not isinstance(body, dict):
        return None
    status_object = body.get('ResponseStatusObject')
    if status_object is None and isinstance(body.get('ResponseStatusListObject'), dict):
        status_object = body['ResponseStatusListObject'].get('ResponseStatusObject')
    if isinstance(status_object, list):
        status_object = status_object[0] if status_object else None
    if isinstance(status_object, dict):
        try:
            return int(status_object.get('StatusCode', -1))
        except (TypeError, ValueError):
            return None
    return None


class Gat1400SessionService:
    _client: Gat1400DigestClient | None = None
    _client_key: tuple[str, str, str, str] | None = None
    _lock = asyncio.Lock()
    _tick_task: asyncio.Task | None = None

    @classmethod
    async def _get_client(cls, db: AsyncSession, redis: aioredis.Redis | None) -> Gat1400DigestClient | None:
        """
        获取（或按需重建）摘要认证客户端。

        配置动态读取：sys_config（Redis 缓存）优先，回退 .env；配置变化时重建客户端，
        保证页面保存配置后无需重启即可生效。
        """
        config = await Gat1400ConfigService.get_runtime_config(redis) if redis else None
        enabled = (config or {}).get('enabled') == 'true' if config else Gat1400Config.gat1400_enabled
        platform_addr = (config or {}).get('platform_addr') if config else Gat1400Config.gat1400_platform_addr
        username = (config or {}).get('username') if config else Gat1400Config.gat1400_username
        password = (config or {}).get('password') if config else Gat1400Config.gat1400_password
        device_id = (config or {}).get('device_id') if config else Gat1400Config.gat1400_device_id
        if not enabled or not platform_addr or not device_id:
            return None
        client_key = (platform_addr, username, password, device_id)
        if cls._client is not None and cls._client_key != client_key:
            await cls._close_client()
        if cls._client is None:
            cls._client = Gat1400DigestClient(
                base_url=platform_addr,
                username=username,
                password=password,
                device_id=device_id,
                timeout=Gat1400Config.gat1400_register_timeout,
            )
            cls._client_key = client_key
        return cls._client

    @classmethod
    async def _schedule_retry(cls, redis: aioredis.Redis | None) -> None:
        delay = random.uniform(RETRY_DELAY_MIN, RETRY_DELAY_MAX)
        next_retry = datetime.now() + timedelta(seconds=delay)
        if redis:
            await redis.set(NEXT_RETRY_KEY, next_retry.strftime('%Y-%m-%d %H:%M:%S'), ex=RETRY_DELAY_MAX + 60)
        logger.info(f'⏱️ GA/T1400 注册将在 {delay:.0f}s 后重试')

    @classmethod
    async def _retry_due(cls, redis: aioredis.Redis | None) -> bool:
        if redis:
            cached = await redis.get(NEXT_RETRY_KEY)
            if cached:
                return datetime.now() >= datetime.strptime(cached.decode(), '%Y-%m-%d %H:%M:%S')
        return True

    @classmethod
    async def register(cls, db: AsyncSession, redis: aioredis.Redis | None, force: bool = False) -> bool:
        """
        向视图库发起注册。成功返回 True。

        :param force: True 时忽略随机重试等待（手动触发/首次启动）
        """
        client = await cls._get_client(db, redis)
        if not client:
            return False
        if not force and not await cls._retry_due(redis):
            return False
        async with cls._lock:
            row = await Gat1400ConnectDao.get_or_create(db)
            if row.register_status == STATUS_ONLINE and not force:
                return True
            try:
                response = await client.post(REGISTER_URI, json_body={'RegisterObject': {'DeviceID': client.device_id}})
                body = Gat1400DigestClient.parse_response_body(response)
                success = response.status_code == HTTP_STATUS_OK and _extract_status_code(body) == 0
            except Exception as e:
                logger.error(f'❌ GA/T1400 注册请求异常: {e}')
                success = False
                body = None
            if success:
                await Gat1400ConnectDao.update_status(
                    db,
                    row,
                    register_status=STATUS_ONLINE,
                    fail_count=0,
                    last_register_time=datetime.now(),
                    error_message='',
                )
                await db.commit()
                if redis:
                    await redis.delete(NEXT_RETRY_KEY)
                logger.info('✅ GA/T1400 注册成功，进入在线状态')
                return True
            await Gat1400ConnectDao.update_status(
                db,
                row,
                register_status=STATUS_OFFLINE,
                fail_count=(row.fail_count or 0) + 1,
                error_message=f'注册失败: {response.status_code} {body}' if body is not None else '注册请求异常',
            )
            await db.commit()
            await cls._schedule_retry(redis)
            logger.warning(f'⚠️ GA/T1400 注册失败（第 {row.fail_count} 次），已安排随机延迟重试')
            return False

    @classmethod
    async def keepalive(cls, db: AsyncSession, redis: aioredis.Redis | None) -> bool:
        """向视图库发送保活请求，连续 3 次失败则转 offline 等待重新注册。"""
        client = await cls._get_client(db, redis)
        if not client:
            return False
        async with cls._lock:
            row = await Gat1400ConnectDao.get_or_create(db)
            if row.register_status != STATUS_ONLINE:
                return False
            try:
                response = await client.post(
                    KEEPALIVE_URI, json_body={'KeepaliveObject': {'DeviceID': client.device_id}}
                )
                body = Gat1400DigestClient.parse_response_body(response)
                success = response.status_code == HTTP_STATUS_OK and _extract_status_code(body) == 0
            except Exception as e:
                logger.error(f'❌ GA/T1400 保活请求异常: {e}')
                success = False
            if success:
                await Gat1400ConnectDao.update_status(
                    db,
                    row,
                    fail_count=0,
                    last_keepalive_time=datetime.now(),
                    keepalive_count=(row.keepalive_count or 0) + 1,
                    error_message='',
                )
                await db.commit()
                return True
            fail_count = (row.fail_count or 0) + 1
            fields: dict[str, Any] = {'fail_count': fail_count, 'error_message': f'保活失败，连续 {fail_count} 次'}
            if fail_count >= MAX_FAIL_COUNT:
                fields['register_status'] = STATUS_OFFLINE
                logger.error(f'❌ GA/T1400 保活连续失败 {fail_count} 次，转入离线状态并安排重新注册')
                await cls._schedule_retry(redis)
            await Gat1400ConnectDao.update_status(db, row, **fields)
            await db.commit()
            return False

    @classmethod
    async def unregister(cls, db: AsyncSession, redis: aioredis.Redis | None = None) -> bool:
        """主动注销，成功后回到未注册状态并关闭客户端。"""
        client = await cls._get_client(db, redis)
        if not client:
            return False
        async with cls._lock:
            row = await Gat1400ConnectDao.get_or_create(db)
            try:
                response = await client.post(
                    UNREGISTER_URI, json_body={'UnRegisterObject': {'DeviceID': client.device_id}}
                )
                body = Gat1400DigestClient.parse_response_body(response)
                success = response.status_code == HTTP_STATUS_OK and _extract_status_code(body) == 0
            except Exception as e:
                logger.error(f'❌ GA/T1400 注销请求异常: {e}')
                success = False
            await Gat1400ConnectDao.update_status(
                db,
                row,
                register_status=STATUS_UNREGISTERED if success else row.register_status,
                error_message='' if success else '注销失败',
            )
            await db.commit()
            if success:
                await cls._close_client()
                logger.info('✅ GA/T1400 注销成功')
            return success

    @classmethod
    async def _tick_once(cls, redis: aioredis.Redis) -> None:
        """单次心跳巡检：在线则保活，离线/未注册则按随机重试时间注册。"""
        locked = await redis.set(TICK_LOCK_KEY, '1', nx=True, ex=TICK_LOCK_TTL)
        if not locked:
            return
        try:
            async with AsyncSessionLocal() as db:
                row = await Gat1400ConnectDao.get_status(db)
                status = row.register_status if row else STATUS_UNREGISTERED
                if status == STATUS_ONLINE:
                    await cls.keepalive(db, redis)
                    # 在线时确保存在有效订阅（无订阅或临近到期自动创建/续订）
                    from module_gat1400.service.gat1400_subscribe_service import (  # noqa: PLC0415 - 函数内导入避免与 subscribe_service 形成循环导入
                        Gat1400SubscribeService,
                    )

                    await Gat1400SubscribeService.ensure_subscribe(db, redis)
                elif status in (STATUS_UNREGISTERED, STATUS_OFFLINE):
                    await cls.register(db, redis)
        except Exception as e:
            logger.error(f'❌ GA/T1400 心跳巡检异常: {e}')
        finally:
            await redis.delete(TICK_LOCK_KEY)

    @classmethod
    async def _tick_loop(cls, redis: aioredis.Redis) -> None:
        while True:
            interval = await Gat1400ConfigService.get_keepalive_interval(redis)
            await asyncio.sleep(interval)
            await cls._tick_once(redis)

    @classmethod
    async def start(cls, redis: aioredis.Redis) -> None:
        """启动动态 supervisor；即使初始禁用，也能在页面启用后自动接管。"""
        if cls._tick_task and not cls._tick_task.done():
            return
        await cls._tick_once(redis)
        cls._tick_task = asyncio.create_task(cls._tick_loop(redis))
        interval = await Gat1400ConfigService.get_keepalive_interval(redis)
        logger.info(f'🔁 GA/T1400 心跳巡检已启动（间隔 {interval}s）')

    @classmethod
    async def _close_client(cls) -> None:
        if cls._client:
            await cls._client.close()
            cls._client = None

    @classmethod
    async def stop(cls) -> None:
        """应用关闭时取消巡检任务并释放 HTTP 客户端。"""
        if cls._tick_task:
            cls._tick_task.cancel()
            try:
                await cls._tick_task
            except asyncio.CancelledError:
                pass
            cls._tick_task = None
        await cls._close_client()

    @classmethod
    async def get_status(cls, db: AsyncSession, redis: aioredis.Redis | None = None) -> dict[str, Any]:
        """查询对接状态，供管理端接口使用。"""
        row = await Gat1400ConnectDao.get_status(db)
        next_retry_at = None
        config = await Gat1400ConfigService.get_runtime_config(redis) if redis else None
        if redis:
            cached = await redis.get(NEXT_RETRY_KEY)
            if cached:
                next_retry_at = cached.decode()
        status = {
            'registerStatus': row.register_status if row else STATUS_UNREGISTERED,
            'failCount': row.fail_count if row else 0,
            'lastRegisterTime': row.last_register_time if row else None,
            'lastKeepaliveTime': row.last_keepalive_time if row else None,
            'keepaliveCount': row.keepalive_count if row else 0,
            'errorMessage': row.error_message if row else '',
            'nextRetryAt': next_retry_at,
            'enabled': (config or {}).get('enabled') == 'true' if config else Gat1400Config.gat1400_enabled,
            'platformAddr': (config or {}).get('platform_addr') if config else Gat1400Config.gat1400_platform_addr,
            'deviceId': (config or {}).get('device_id') if config else Gat1400Config.gat1400_device_id,
            'keepaliveInterval': (
                (config or {}).get('keepalive_interval') if config else Gat1400Config.gat1400_keepalive_interval
            ),
        }
        return status
