from datetime import datetime

from fastapi import Request
from fastapi.responses import JSONResponse

from common.aspect.pre_auth import PreAuthDependency
from common.router import APIRouterPro
from config.env import Gat1400Config
from module_gat1400.service.gat1400_config_service import Gat1400ConfigService
from module_gat1400.service.gat1400_digest_client import (
    issue_digest_nonce,
    verify_digest_authorization,
)
from module_gat1400.service.gat1400_notify_service import Gat1400NotifyService
from utils.log_util import logger

# 回调接口排除登录认证（外部平台通过摘要认证/内网 IP 访问），传输加密已通过
# TRANSPORT_CRYPTO_EXCLUDE_PATHS 的 /VIID 排除
viid_notify_controller = APIRouterPro(
    prefix='',
    order_num=27,
    tags=['GA/T1400通知回调'],
    dependencies=[PreAuthDependency(exclude_routes=[{'path': '/VIID/SubscribeNotifications', 'methods': ['POST']}])],
)


def _build_notify_response(request: Request, status_code: int = 0, status_string: str = '正常') -> dict:
    """构建大华协议格式的响应体：ResponseStatusListObject.ResponseStatusObject[]。"""
    return {
        'ResponseStatusListObject': {
            'ResponseStatusObject': [
                {
                    'RequestURL': f'{request.base_url}{request.url.path.lstrip("/")}',
                    'StatusCode': status_code,
                    'StatusString': status_string,
                    'LocalTime': datetime.now().strftime('%Y%m%d%H%M%S'),
                }
            ]
        }
    }


def _digest_challenge(request: Request, nonce_secret: str, status_string: str = 'Digest认证失败') -> JSONResponse:
    """返回 RFC 2617 摘要认证挑战，通知发送方据此重发。"""
    nonce = issue_digest_nonce(nonce_secret)
    return JSONResponse(
        status_code=401,
        content=_build_notify_response(request, 4, status_string),
        headers={'WWW-Authenticate': f'Digest realm="GAT1400", qop="auth", nonce="{nonce}", algorithm=MD5'},
    )


@viid_notify_controller.post('/VIID/SubscribeNotifications')
async def receive_subscribe_notification(request: Request) -> JSONResponse:
    """
    接收大华平台推送的通知（过车记录）。

    同步只做：IP 白名单校验 → 原始报文入 Redis 队列 → 立即返回协议格式成功响应。
    落库由后台消费循环异步完成，满足标准"5s 内未响应则重传"的硬性要求。
    """
    config = await Gat1400ConfigService.get_runtime_config(request.app.state.redis)
    nonce_secret = config['password'] or Gat1400Config.gat1400_password or 'gat1400-notify'
    allowed_ips = [ip.strip() for ip in config['notify_allowed_ips'].split(',') if ip.strip()]
    client_ip = request.client.host if request.client else ''
    if allowed_ips and client_ip not in allowed_ips:
        logger.warning(f'⚠️ GA/T1400 通知来源 IP 不在白名单内: {client_ip}')
        return JSONResponse(status_code=403, content=_build_notify_response(request, 4, 'IP不在白名单内'))

    if not config['username'] or not config['password']:
        logger.error('GA/T1400 回调 Digest 凭据未配置，拒绝接收通知')
        return JSONResponse(status_code=503, content=_build_notify_response(request, 4, '回调鉴权未配置'))

    expected_device_id = config['device_id']
    if not expected_device_id or request.headers.get('User-Identify') != expected_device_id:
        logger.warning(f'⚠️ GA/T1400 通知 User-Identify 校验失败: {client_ip}')
        return _digest_challenge(request, nonce_secret, 'User-Identify不匹配')
    authorized, auth_values = verify_digest_authorization(
        request.headers.get('Authorization', ''),
        username=config['username'],
        password=config['password'],
        method=request.method,
        uri=request.url.path,
        nonce_secret=nonce_secret,
    )
    if not authorized:
        logger.warning(f'⚠️ GA/T1400 通知 Digest认证失败: {client_ip}')
        return _digest_challenge(request, nonce_secret)
    if auth_values.get('qop'):
        replay_key = (
            f'gat1400:notify:digest:nc:{auth_values.get("username")}:{auth_values.get("nonce")}:'
            f'{auth_values.get("cnonce")}:{request.url.path}'
        )
        current_nc = int(auth_values['nc'], 16)
        previous_nc = await request.app.state.redis.get(replay_key)
        if previous_nc is not None and current_nc <= int(previous_nc):
            logger.warning(f'⚠️ GA/T1400 通知 Digest重放请求被拒绝: {client_ip}')
            return _digest_challenge(request, nonce_secret, 'Digest请求重放')
        await request.app.state.redis.set(replay_key, str(current_nc), ex=3600)

    raw = (await request.body()).decode('utf-8', errors='replace')
    if raw:
        await Gat1400NotifyService.enqueue_notify(request.app.state.redis, raw)
    return JSONResponse(content=_build_notify_response(request))
