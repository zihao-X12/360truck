"""
GA/T1400 对接配置服务：可视化配置（sys_config 表 + Redis 缓存）与 .env 回退。

设计：
- 配置存 sys_config 表（config_key 以 gat1400. 开头），Redis 缓存键 sys_config:{key}，
  页面可改，保存后立即生效（下次心跳/请求读取新配置）
- .env（Gat1400Config）作为默认值回退——sys_config 中未配置的键回退到 .env
- 认证密码加密存储：AES-256-GCM，密钥由 JWT_SECRET_KEY 派生；API 回显时脱敏
"""

import base64
import hashlib
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from redis import asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.env import Gat1400Config, JwtConfig
from module_admin.entity.do.config_do import SysConfig
from utils.log_util import logger

# 配置键定义（与 m12 迁移中的 sys_config 一致）
CONFIG_KEYS = {
    'enabled': 'gat1400.enabled',
    'platform_addr': 'gat1400.platform.addr',
    'device_id': 'gat1400.device.id',
    'username': 'gat1400.auth.username',
    'password': 'gat1400.auth.password',
    'keepalive_interval': 'gat1400.keepalive.interval',
    'subscribe_detail': 'gat1400.subscribe.detail',
    'subscribe_resource_uri': 'gat1400.subscribe.resource.uri',
    'applicant_name': 'gat1400.subscribe.applicant.name',
    'applicant_org': 'gat1400.subscribe.applicant.org',
    'subscribe_days': 'gat1400.subscribe.days',
    'receive_addr': 'gat1400.subscribe.receive.addr',
    'notify_allowed_ips': 'gat1400.notify.allowed.ips',
}

# 默认值（与 config/env.py Gat1400Settings 保持一致）
DEFAULT_VALUES = {
    'enabled': str(Gat1400Config.gat1400_enabled).lower(),
    'platform_addr': Gat1400Config.gat1400_platform_addr,
    'device_id': Gat1400Config.gat1400_device_id,
    'username': Gat1400Config.gat1400_username,
    'password': Gat1400Config.gat1400_password,
    'keepalive_interval': str(Gat1400Config.gat1400_keepalive_interval),
    'subscribe_detail': Gat1400Config.gat1400_subscribe_detail,
    'subscribe_resource_uri': Gat1400Config.gat1400_subscribe_resource_uri,
    'applicant_name': Gat1400Config.gat1400_subscribe_applicant_name,
    'applicant_org': Gat1400Config.gat1400_subscribe_applicant_org,
    'subscribe_days': str(Gat1400Config.gat1400_subscribe_days),
    'receive_addr': Gat1400Config.gat1400_subscribe_receive_addr,
    'notify_allowed_ips': Gat1400Config.gat1400_notify_allowed_ips,
}

_ENCRYPTED_PREFIX = 'enc:'
KEEPALIVE_MIN = 10
KEEPALIVE_MAX = 300
DEFAULT_KEEPALIVE_INTERVAL = 60


def _crypto_key() -> bytes:
    """由 JWT_SECRET_KEY 派生 AES-256 密钥（配置变更后密码自动失效，需重新填写）。"""
    return hashlib.sha256(JwtConfig.jwt_secret_key.encode('utf-8')).digest()


def encrypt_password(plain: str) -> str:
    """密码加密存储：AES-256-GCM，输出 enc:base64(iv+ciphertext)。"""
    if not plain:
        return ''
    nonce = os.urandom(12)
    ciphertext = AESGCM(_crypto_key()).encrypt(nonce, plain.encode('utf-8'), None)

    return f'{_ENCRYPTED_PREFIX}{base64.b64encode(nonce + ciphertext).decode("ascii")}'


def decrypt_password(stored: str) -> str:
    """解密存储的密码；非加密格式（历史明文）原样返回。"""
    if not stored:
        return ''
    if not stored.startswith(_ENCRYPTED_PREFIX):
        return stored

    try:
        raw = base64.b64decode(stored[len(_ENCRYPTED_PREFIX) :])
        nonce, ciphertext = raw[:12], raw[12:]
        return AESGCM(_crypto_key()).decrypt(nonce, ciphertext, None).decode('utf-8')
    except Exception:
        logger.warning('⚠️ GA/T1400 配置密码解密失败（可能密钥已变更），按空密码处理')
        return ''


class Gat1400ConfigService:
    @classmethod
    async def get_runtime_config(cls, redis: aioredis.Redis) -> dict[str, str]:
        """
        对接服务运行时配置：Redis 缓存（sys_config）优先，缺失回退 .env 默认值。
        密码返回明文（解密后），供认证客户端使用。
        """
        result: dict[str, str] = {}
        for field, key in CONFIG_KEYS.items():
            cached = await redis.get(f'sys_config:{key}')
            # decode_responses=True 时返回 str，否则返回 bytes
            value = cached if isinstance(cached, str) else cached.decode('utf-8') if cached is not None else DEFAULT_VALUES[field]
            if field == 'password' and value.startswith(_ENCRYPTED_PREFIX):
                value = decrypt_password(value)
            result[field] = value
        return result

    @classmethod
    async def get_config_for_api(cls, db: AsyncSession) -> dict[str, Any]:
        """
        管理端读取：返回各配置项 + 密码脱敏状态（password_set），供前端表单回显。
        """
        rows = {
            row.config_key: row.config_value
            for row in (await db.execute(select(SysConfig).where(SysConfig.config_key.in_(CONFIG_KEYS.values()))))
            .scalars()
            .all()
        }
        result: dict[str, Any] = {}
        for field, key in CONFIG_KEYS.items():
            value = rows.get(key)
            if field == 'password':
                stored = value if value is not None else DEFAULT_VALUES['password']
                result['passwordSet'] = bool(stored)
                result['password'] = '********' if stored else ''
            else:
                result[field] = value if value is not None else DEFAULT_VALUES[field]
        return result

    @classmethod
    async def save_config(cls, db: AsyncSession, redis: aioredis.Redis, params: dict[str, Any]) -> None:
        """
        保存配置：upsert sys_config 表并刷新 Redis 缓存。
        - password 传空或 '********' 表示不修改（保留原值）
        - password 传新值则加密存储
        """
        existing = {
            row.config_key: row
            for row in (await db.execute(select(SysConfig).where(SysConfig.config_key.in_(CONFIG_KEYS.values()))))
            .scalars()
            .all()
        }
        for field, key in CONFIG_KEYS.items():
            if field not in params:
                continue
            value = params[field]
            if field == 'password':
                if value in ('', '********'):
                    continue  # 不修改密码
                value = encrypt_password(value)
            elif isinstance(value, bool):
                value = str(value).lower()
            else:
                value = str(value)
            row = existing.get(key)
            if row:
                row.config_value = value
            else:
                db.add(
                    SysConfig(
                        config_name=key,
                        config_key=key,
                        config_value=value,
                        config_type='N',
                        create_by='admin',
                        remark='GA/T1400可视化配置',
                    )
                )
            await redis.set(f'sys_config:{key}', value)
        await db.commit()
        logger.info('✅ GA/T1400 配置已保存并刷新缓存')

    @classmethod
    async def get_keepalive_interval(cls, redis: aioredis.Redis) -> int:
        """读取保活间隔（秒），非法值回退默认 60。"""
        config = await cls.get_runtime_config(redis)
        try:
            interval = int(config['keepalive_interval'])
            return interval if KEEPALIVE_MIN <= interval <= KEEPALIVE_MAX else DEFAULT_KEEPALIVE_INTERVAL
        except (TypeError, ValueError):
            return DEFAULT_KEEPALIVE_INTERVAL
