"""
GA/T1400 视图库 HTTP 摘要认证客户端（RFC 2617）。

对照大华《公安视频图像信息数据库对接协议 V1.2》实现：
- Digest MD5、qop=auth，realm/nonce 取自服务端 WWW-Authenticate 挑战
- 首次请求未带 Authorization 时服务端返回 401 挑战，计算后重发
- nonce 过期（标准要求 3600s 内重置）时自动重新挑战重试
- 注册成功后所有请求自动携带 User-Identify 请求头（值 = DeviceID，大华要求）
"""

import hashlib
import hmac
import secrets
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from exceptions.exception import ServiceException
from utils.log_util import logger

USER_IDENTIFY_HEADER = 'User-Identify'
HTTP_STATUS_UNAUTHORIZED = 401
DIGEST_NONCE_TTL_SECONDS = 3600


def parse_digest_authorization(header_value: str) -> dict[str, str]:
    """解析 Digest Authorization/WWW-Authenticate 参数，兼容带引号的逗号。"""
    if not header_value or not header_value.lower().startswith('digest '):
        return {}
    result: dict[str, str] = {}
    value = header_value[7:]
    current: list[str] = []
    quoted = False
    escaped = False
    items: list[str] = []
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
        elif char == '\\' and quoted:
            current.append(char)
            escaped = True
        elif char == '"':
            current.append(char)
            quoted = not quoted
        elif char == ',' and not quoted:
            items.append(''.join(current))
            current = []
        else:
            current.append(char)
    if current:
        items.append(''.join(current))
    for item in items:
        key, separator, raw_value = item.strip().partition('=')
        if separator:
            result[key.strip().lower()] = raw_value.strip().strip('"')
    return result


def issue_digest_nonce(secret: str, now: int | None = None) -> str:
    """签发可校验、有效期受限的服务端 Digest nonce。"""
    issued_at = int(now if now is not None else time.time())
    salt = secrets.token_hex(12)
    payload = f'{issued_at}:{salt}'
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f'{payload}:{signature}'


def validate_digest_nonce(secret: str, nonce: str, now: int | None = None) -> bool:
    """校验 nonce 完整性和 3600 秒有效期。"""
    try:
        issued_at_text, salt, signature = nonce.split(':', 2)
        issued_at = int(issued_at_text)
    except (AttributeError, ValueError):
        return False
    payload = f'{issued_at}:{salt}'
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    current = int(now if now is not None else time.time())
    return hmac.compare_digest(signature, expected) and 0 <= current - issued_at <= DIGEST_NONCE_TTL_SECONDS


def verify_digest_authorization(
    header_value: str,
    *,
    username: str,
    password: str,
    method: str,
    uri: str,
    nonce_secret: str,
) -> tuple[bool, dict[str, str]]:
    """校验 GA/T 1400 回调端 Digest MD5 凭证（防重放计数由调用方持久化）。"""
    values = parse_digest_authorization(header_value)
    if (
        not values
        or values.get('username') != username
        or values.get('uri') != uri
        or values.get('realm') != 'GAT1400'
    ):
        return False, values
    nonce = values.get('nonce', '')
    if not validate_digest_nonce(nonce_secret, nonce):
        return False, values
    algorithm = values.get('algorithm', 'MD5')
    qop = values.get('qop')
    try:
        nc = int(values.get('nc', '0'), 16) if qop else 0
    except ValueError:
        return False, values
    if qop and (qop != 'auth' or nc <= 0 or not values.get('cnonce')):
        return False, values
    expected = compute_digest_response(
        username=username,
        password=password,
        realm='GAT1400',
        method=method,
        uri=uri,
        nonce=nonce,
        nc=nc,
        cnonce=values.get('cnonce', ''),
        qop=qop,
        algorithm=algorithm,
    )
    return hmac.compare_digest(values.get('response', ''), expected), values


def parse_digest_challenge(header_value: str) -> dict[str, str]:
    """
    解析 WWW-Authenticate 挑战头，返回 key-value 字典。

    例如 'Digest realm="myrealm", qop="auth", nonce="-16sx92237dd9h", algorithm=MD5'
    """
    if not header_value or not header_value.lower().startswith('digest '):
        raise ServiceException(message=f'不支持的认证挑战: {header_value!r}')
    result = {}
    # 从 "Digest " 之后解析 key=value 对，value 可能带引号
    for item in header_value[7:].split(','):
        stripped = item.strip()
        if '=' not in stripped:
            continue
        key, _, value = stripped.partition('=')
        result[key.strip().lower()] = value.strip().strip('"')
    return result


def compute_digest_response(
    username: str,
    password: str,
    realm: str,
    method: str,
    uri: str,
    nonce: str,
    nc: int,
    cnonce: str,
    qop: str | None = None,
    algorithm: str = 'MD5',
) -> str:
    """
    计算 RFC 2617 摘要认证的 response 值。

    HA1 = MD5(username:realm:password)
    HA2 = MD5(method:uri)
    qop=auth 时: response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
    """
    algorithm_lower = (algorithm or 'MD5').lower()
    if algorithm_lower != 'md5':
        raise ServiceException(message=f'不支持的摘要算法: {algorithm}')
    ha1 = hashlib.md5(f'{username}:{realm}:{password}'.encode()).hexdigest()
    ha2 = hashlib.md5(f'{method.upper()}:{uri}'.encode()).hexdigest()
    if qop:
        return hashlib.md5(f'{ha1}:{nonce}:{nc:08x}:{cnonce}:{qop}:{ha2}'.encode()).hexdigest()
    return hashlib.md5(f'{ha1}:{nonce}:{ha2}'.encode()).hexdigest()


class Gat1400DigestClient:
    """
    GA/T1400 摘要认证异步客户端。

    状态说明：nonce/realm/qop 在首次 401 挑战后缓存，同 nonce 下 nc 递增；
    nonce 变化（服务端重置）时重新挑战并重置 nc。
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        device_id: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.device_id = device_id
        self._realm: str | None = None
        self._nonce: str | None = None
        self._qop: str | None = None
        self._opaque: str | None = None
        self._nc = 0
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(timeout), transport=transport)

    def _uri(self, path: str) -> str:
        """计算摘要认证使用的请求 URI（base_url 带路径前缀时拼到前面）。"""
        base_path = urlparse(self.base_url).path.rstrip('/')
        return f'{base_path}/{path.lstrip("/")}' if base_path else path

    def _build_auth_header(self, method: str, uri: str, nonce: str, nc: int) -> str:
        cnonce = secrets.token_hex(16)
        response = compute_digest_response(
            username=self.username,
            password=self.password,
            realm=self._realm or '',
            method=method,
            uri=uri,
            nonce=nonce,
            nc=nc,
            cnonce=cnonce,
            qop=self._qop,
        )
        parts = [
            f'Digest username="{self.username}"',
            f'realm="{self._realm or ""}"',
            f'nonce="{nonce}"',
            f'uri="{uri}"',
            f'response="{response}"',
        ]
        if self._qop:
            parts.append(f'qop={self._qop}')
            parts.append(f'nc={nc:08x}')
            parts.append(f'cnonce="{cnonce}"')
        if self._opaque:
            parts.append(f'opaque="{self._opaque}"')
        parts.append('algorithm=MD5')
        return ', '.join(parts)

    def _update_challenge(self, header_value: str | None) -> None:
        """从 401 响应的 WWW-Authenticate 头更新挑战参数。"""
        if not header_value:
            raise ServiceException(message='平台返回 401 但未携带 WWW-Authenticate 挑战头')
        challenge = parse_digest_challenge(header_value)
        new_nonce = challenge.get('nonce', '')
        if not new_nonce:
            raise ServiceException(message='WWW-Authenticate 挑战头缺少 nonce')
        if new_nonce != self._nonce:
            self._nonce = new_nonce
            self._realm = challenge.get('realm', self._realm)
            self._qop = challenge.get('qop', self._qop)
            self._opaque = challenge.get('opaque', self._opaque)
            self._nc = 0

    def _headers(self, method: str, uri: str) -> dict[str, str]:
        headers = {'Content-Type': 'application/json;charset=utf-8', 'Accept': 'application/json;charset=utf-8'}
        # 大华要求：注册成功后所有请求携带 User-Identify，值为 DeviceID
        if self.device_id:
            headers[USER_IDENTIFY_HEADER] = self.device_id
        if self._nonce:
            self._nc += 1
            headers['Authorization'] = self._build_auth_header(method, uri, self._nonce, self._nc)
        return headers

    async def _request(
        self, method: str, path: str, *, json_body: dict | None = None, params: dict | None = None
    ) -> httpx.Response:
        """发送请求，自动处理 401 摘要认证挑战（挑战后重试一次）。"""
        uri = self._uri(path)
        response = await self._http.request(
            method, f'{self.base_url}{path}', json=json_body, params=params, headers=self._headers(method, uri)
        )
        if response.status_code != HTTP_STATUS_UNAUTHORIZED:
            return response
        # 首次挑战或 nonce 刷新：更新挑战参数后重试一次
        self._update_challenge(response.headers.get('WWW-Authenticate'))
        return await self._http.request(
            method, f'{self.base_url}{path}', json=json_body, params=params, headers=self._headers(method, uri)
        )

    async def post(self, path: str, json_body: dict | None = None) -> httpx.Response:
        return await self._request('POST', path, json_body=json_body)

    async def get(self, path: str, params: dict | None = None) -> httpx.Response:
        return await self._request('GET', path, params=params)

    async def put(self, path: str, json_body: dict | None = None) -> httpx.Response:
        return await self._request('PUT', path, json_body=json_body)

    async def delete(self, path: str, params: dict | None = None) -> httpx.Response:
        return await self._request('DELETE', path, params=params)

    async def close(self) -> None:
        await self._http.aclose()

    @staticmethod
    def parse_response_body(response: httpx.Response) -> Any:
        """解析响应体 JSON，空响应返回 None。"""
        try:
            return response.json() if response.content else None
        except Exception:
            logger.warning(f'响应非 JSON（status={response.status_code}），body={response.text[:200]!r}')
            return None
