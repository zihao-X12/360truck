from urllib.parse import urlparse

import requests

from common.config import Config


def build_auth_cookie(token: str) -> dict:
    """
    构造管理端认证 Cookie。

    Cookie 域取自 `Config.frontend_url`，因此测试前端地址在 localhost、127.0.0.1
    或其他主机之间切换时都能正常携带认证信息，避免因硬编码域导致被重定向到登录页。

    :param token: 登录返回的访问令牌
    :return: Playwright `add_cookies` 可用的 Cookie 字典
    """
    return {
        'name': 'Admin-Token',
        'value': token,
        'domain': urlparse(Config.frontend_url).hostname,
        'path': '/',
        'httpOnly': False,
        'secure': False,
    }


class LoginHelper:
    """
    登录辅助类

    登录令牌按 `用户名@前端地址` 缓存：`/login` 接口限流为 12 次/60 秒
    （见 ApiRateLimitPreset.ANON_AUTH_LOGIN），而每个测试用例都会新建实例登录，
    不缓存时整套用例会触发 429 导致误报失败。
    """

    _token_cache: dict[str, str] = {}

    def __init__(self, base_url: str = Config.frontend_url) -> None:
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, username: str = 'admin', password: str = 'admin123', max_retries: int = 3) -> str | None:
        """
        执行登录操作（在测试环境中，验证码已禁用）
        """
        cache_key = f'{username}@{self.base_url}'
        cached_token = self._token_cache.get(cache_key)
        if cached_token:
            return cached_token

        token = self._request_token(username, password, max_retries)
        if token:
            self._token_cache[cache_key] = token
        return token

    def _request_token(self, username: str, password: str, max_retries: int) -> str | None:
        """
        向登录接口请求令牌，不在命中缓存时调用。

        :param username: 用户名
        :param password: 密码
        :param max_retries: 最大重试次数
        :return: 访问令牌，失败返回 None
        """
        for _attempt in range(max_retries):
            # 在测试环境中，验证码已禁用，所以直接登录
            login_data = {'username': username, 'password': password}

            headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Referer': f'{self.base_url}/login'}

            response = self.session.post(f'{Config.backend_url}/login', data=login_data, headers=headers)
            http_ok = 200
            if response.status_code == http_ok:
                result = response.json()
                # 检查登录是否成功 - 可能是 code=200 或 success=true
                if result.get('code') == http_ok or result.get('success'):
                    # 尝试从不同可能的位置获取token
                    token = result.get('token')  # 直接在根级别
                    if not token:
                        token = result.get('data', {}).get('token')  # 在data对象内

                    if token:
                        print('登录成功')
                        return token
                    print(f'登录失败: 响应中未找到token - {result}')
                else:
                    print(f'登录失败: {result.get("msg", "未知错误")}')
            else:
                print(f'登录请求失败: 状态码 {response.status_code}')

        print('登录失败，已达到最大重试次数')
        return None


# 使用示例
if __name__ == '__main__':
    helper = LoginHelper()
    token = helper.login()
    if token:
        print(f'获取到token: {token}')
    else:
        print('登录失败')
