"""
Mock 大华视图库平台（GA/T 1400 服务端），用于集成测试与本地端到端联调。

能力（对照大华《公安视频图像信息数据库对接协议 V1.2》）：
- Digest 摘要认证服务端：无 Authorization 返回 401 + WWW-Authenticate 挑战，
  收到 Authorization 后按 RFC 2617 公式用已知密码重算并校验 response；
  校验 User-Identify 头（注册后必带，值 = DeviceID）
- 端点：Register / UnRegister / Keepalive / Time / Subscribes（订阅+取消）
- 主动推送：push_notification() 向订阅的 ReceiveAddr POST 过车通知（含摘要认证头）

用法（进程方式）：uvicorn mock_viid_server:app --port 18080
用法（测试内联）：httpx.AsyncClient(transport=ASGITransport(app=app))
"""

import hashlib
import re
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

MOCK_REALM = 'myrealm'
MOCK_QOP = 'auth'
MOCK_NONCE = 'test-nonce-0001'
MOCK_USERNAME = 'system'
MOCK_PASSWORD = 'secret'
MOCK_DEVICE_ID = '33112400005030000001'

NOTIFY_DATETIME_FORMAT = '%Y%m%d%H%M%S'


def _parse_digest_header(header: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in re.sub(r'^Digest\s+', '', header).split(','):
        key, _, value = part.strip().partition('=')
        result[key.strip().lower()] = value.strip().strip('"')
    return result


def _compute_expected_response(
    username: str, password: str, realm: str, method: str, uri: str, nonce: str, nc: int, cnonce: str, qop: str | None
) -> str:
    ha1 = hashlib.md5(f'{username}:{realm}:{password}'.encode()).hexdigest()
    ha2 = hashlib.md5(f'{method.upper()}:{uri}'.encode()).hexdigest()
    if qop:
        return hashlib.md5(f'{ha1}:{nonce}:{nc:08x}:{cnonce}:{qop}:{ha2}'.encode()).hexdigest()
    return hashlib.md5(f'{ha1}:{nonce}:{ha2}'.encode()).hexdigest()


class MockViidState:
    """Mock 平台内存状态：注册状态、订阅列表、认证观测记录。"""

    def __init__(self) -> None:
        self.registered = False
        self.device_id: str | None = None
        self.subscribes: dict[str, dict] = {}
        self.auth_headers: list[dict] = []
        self.notify_push_calls: list[dict] = []
        self._nc_seen: dict[str, int] = {}

    def reset(self) -> None:
        self.registered = False
        self.device_id = None
        self.subscribes.clear()
        self.auth_headers.clear()
        self.notify_push_calls.clear()
        self._nc_seen.clear()


state = MockViidState()


def _challenge_header() -> str:
    return f'Digest realm="{MOCK_REALM}", qop="{MOCK_QOP}", nonce="{MOCK_NONCE}", algorithm=MD5'


def _status_response(
    request: Request, status_code: int = 0, status_string: str = '正常', resource_id: str = ''
) -> dict:
    return {
        'ResponseStatusObject': {
            'RequestURL': f'http://{request.url.netloc}{request.url.path}',
            'StatusCode': status_code,
            'StatusString': status_string,
            'Id': resource_id,
            'LocalTime': datetime.now().strftime(NOTIFY_DATETIME_FORMAT),
        }
    }


def _status_list_response(request: Request, items: list[dict]) -> dict:
    return {'ResponseStatusListObject': {'ResponseStatusObject': items}}


async def _authenticate(request: Request) -> dict | None:
    """
    摘要认证校验。返回 None 表示通过；否则返回需要直接响应的 401 挑战体。
    """
    auth = request.headers.get('Authorization')
    if not auth:
        return {'headers': {'WWW-Authenticate': _challenge_header()}}
    parts = _parse_digest_header(auth)
    if parts.get('username') != MOCK_USERNAME:
        return {'headers': {'WWW-Authenticate': _challenge_header()}}
    nonce = parts.get('nonce', '')
    nc = int(parts.get('nc', '0'), 16)
    cnonce = parts.get('cnonce', '')
    qop = parts.get('qop')
    # 防重放：同一 nonce 下 nc 必须递增
    if nonce in state._nc_seen and nc <= state._nc_seen[nonce]:
        return {'headers': {'WWW-Authenticate': _challenge_header()}}
    state._nc_seen[nonce] = nc
    expected = _compute_expected_response(
        username=MOCK_USERNAME,
        password=MOCK_PASSWORD,
        realm=MOCK_REALM,
        method=request.method,
        uri=parts.get('uri', request.url.path),
        nonce=nonce,
        nc=nc,
        cnonce=cnonce,
        qop=qop,
    )
    if parts.get('response') != expected:
        return {'headers': {'WWW-Authenticate': _challenge_header()}}
    state.auth_headers.append(
        {'nc': nc, 'nonce': nonce, 'user_identify': request.headers.get('User-Identify'), 'path': request.url.path}
    )
    return None


app = FastAPI(title='Mock 大华视图库', docs_url=None, redoc_url=None)


@app.middleware('http')
async def digest_auth_middleware(request: Request, call_next):  # noqa: ANN001, ANN201
    if not request.url.path.startswith('/VIID'):
        return await call_next(request)
    challenge = await _authenticate(request)
    if challenge:
        return JSONResponse(status_code=401, content={}, headers=challenge['headers'])
    return await call_next(request)


@app.post('/VIID/System/Register')
async def mock_register(request: Request) -> JSONResponse:
    body = await request.json()
    register_object = body.get('RegisterObject') or {}
    device_id = register_object.get('DeviceID')
    if not device_id:
        return JSONResponse(content=_status_response(request, 6, 'Invalid JSON Content'))
    state.registered = True
    state.device_id = device_id
    return JSONResponse(content=_status_response(request, 0, '正常', device_id))


@app.post('/VIID/System/Keepalive')
async def mock_keepalive(request: Request) -> JSONResponse:
    if not state.registered:
        return JSONResponse(content=_status_response(request, 4, '未注册'))
    return JSONResponse(content=_status_response(request, 0, '正常', state.device_id or ''))


@app.post('/VIID/System/UnRegister')
async def mock_unregister(request: Request) -> JSONResponse:
    state.registered = False
    state.device_id = None
    return JSONResponse(content=_status_response(request, 0, '正常'))


@app.api_route('/VIID/System/Time', methods=['GET', 'POST'])
async def mock_time(request: Request) -> JSONResponse:
    return JSONResponse(
        content={
            'SystemTimeObject': {
                'VIIDServerID': state.device_id or MOCK_DEVICE_ID,
                'TimeMode': '1',
                'LocalTime': datetime.now().strftime(NOTIFY_DATETIME_FORMAT),
                'TimeZone': 'UTC+8',
            }
        }
    )


@app.post('/mock/push')
async def mock_push(request: Request) -> JSONResponse:
    """管理端点：触发向当前订阅的 ReceiveAddr 推送过车通知（E2E 脚本跨进程使用）。"""
    body = await request.json()
    vehicles = body.get('vehicles') or []
    notification_id = body.get('notificationId', 'NOTIFY-E2E')
    record = await push_notification(vehicles, notification_id=notification_id)
    return JSONResponse(content={'status_code': record['status_code'], 'receive_addr': record['receive_addr']})


@app.post('/VIID/Subscribes')
async def mock_subscribe(request: Request) -> JSONResponse:
    body = await request.json()
    wrapper = body.get('SubscribeListObject') or {}
    items = wrapper.get('SubscribeObject') or []
    results = []
    for item in items:
        subscribe_id = item.get('SubscribeID')
        if not subscribe_id:
            results.append({'RequestURL': str(request.url), 'StatusCode': 6, 'StatusString': '缺少SubscribeID'})
            continue
        state.subscribes[subscribe_id] = dict(item)
        results.append({'RequestURL': str(request.url), 'StatusCode': 0, 'StatusString': '正常', 'Id': subscribe_id})
    return JSONResponse(content=_status_list_response(request, results))


@app.put('/VIID/Subscribes/{subscribe_id}')
async def mock_cancel_subscribe(request: Request, subscribe_id: str) -> JSONResponse:
    if subscribe_id not in state.subscribes:
        return JSONResponse(content=_status_response(request, 6, '订阅不存在'))
    state.subscribes.pop(subscribe_id, None)
    return JSONResponse(content=_status_response(request, 0, '正常', subscribe_id))


async def push_notification(
    vehicles: list[dict], notification_id: str = 'NOTIFY-001', http_client: httpx.AsyncClient | None = None
) -> dict:
    """
    向当前有效订阅的 ReceiveAddr 推送过车通知（带摘要认证头，模拟真实平台行为）。

    :param http_client: 可注入的 httpx 客户端（测试用 MockTransport）；默认新建真实客户端
    返回 {'receive_addr': ..., 'status_code': ..., 'body': 推送的报文}
    """
    if not state.subscribes:
        raise RuntimeError('Mock 平台没有有效订阅，无法推送')
    subscribe_id, subscribe = next(iter(state.subscribes.items()))
    receive_addr = subscribe.get('ReceiveAddr')
    if not receive_addr:
        raise RuntimeError(f'订阅 {subscribe_id} 缺少 ReceiveAddr')
    notify_body: dict[str, Any] = {
        'SubscribeNotificationListObject': {
            'SubscribeNotificationObject': [
                {
                    'NotificationID': notification_id,
                    'SubscribeID': subscribe_id,
                    'Title': subscribe.get('Title', '过车'),
                    'TriggerTime': datetime.now().strftime(NOTIFY_DATETIME_FORMAT),
                    'InfoIDs': ';'.join(str(v.get('MotorVehicleID', '')) for v in vehicles),
                    'MotorVehicleObjectList': {'MotorVehicleObject': vehicles},
                }
            ]
        }
    }
    # 摘要认证头（与客户端同公式）
    nc = state._nc_seen.get('push-nonce', 0) + 1
    state._nc_seen['push-nonce'] = nc
    cnonce = 'mockcnonce'
    response = _compute_expected_response(
        username=MOCK_USERNAME,
        password=MOCK_PASSWORD,
        realm=MOCK_REALM,
        method='POST',
        uri='/VIID/SubscribeNotifications',
        nonce='push-nonce',
        nc=nc,
        cnonce=cnonce,
        qop=MOCK_QOP,
    )
    headers = {
        'Content-Type': 'application/json;charset=utf-8',
        'User-Identify': state.device_id or '',
        'Authorization': (
            f'Digest username="{MOCK_USERNAME}", realm="{MOCK_REALM}", nonce="push-nonce", '
            f'uri="/VIID/SubscribeNotifications", response="{response}", qop={MOCK_QOP}, '
            f'nc={nc:08x}, cnonce="{cnonce}", algorithm=MD5'
        ),
    }
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=10)
    async with http_client as http:
        push_response = await http.post(receive_addr, json=notify_body, headers=headers)
    record = {'receive_addr': receive_addr, 'status_code': push_response.status_code, 'body': notify_body}
    state.notify_push_calls.append(record)
    return record
