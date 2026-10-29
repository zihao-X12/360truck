import unittest

import httpx

from exceptions.exception import ServiceException
from module_gat1400.service.gat1400_digest_client import (
    Gat1400DigestClient,
    compute_digest_response,
    parse_digest_challenge,
)

DAHUA_CHALLENGE = 'Digest realm="myrealm",qop="auth",nonce="-16sx92237dd9h"'
DAHUA_NONCE = '-16sx92237dd9h'


class DigestParseTests(unittest.TestCase):
    def test_parse_dahua_challenge(self) -> None:
        challenge = parse_digest_challenge(DAHUA_CHALLENGE)

        self.assertEqual(challenge, {'realm': 'myrealm', 'qop': 'auth', 'nonce': DAHUA_NONCE})

    def test_parse_rejects_non_digest_challenge(self) -> None:
        with self.assertRaises(ServiceException):
            parse_digest_challenge('Basic realm="test"')


class DigestResponseTests(unittest.TestCase):
    def test_rfc2617_known_answer(self) -> None:
        """RFC 2617 第 3.5 节标准测试向量。"""
        response = compute_digest_response(
            username='Mufasa',
            password='Circle Of Life',
            realm='testrealm@host.com',
            method='GET',
            uri='/dir/index.html',
            nonce='dcd98b7102dd2f0e8b11d0f600bfb0c093',
            nc=1,
            cnonce='0a4f113b',
            qop='auth',
        )

        self.assertEqual(response, '6629fae49393a05397450978507c4ef1')

    def test_response_without_qop(self) -> None:
        response = compute_digest_response(
            username='system',
            password='secret',
            realm='myrealm',
            method='POST',
            uri='/VIID/System/Register',
            nonce='abc',
            nc=1,
            cnonce='deadbeef',
        )
        # 无 qop 时 nc/cnonce 不参与计算
        self.assertEqual(
            response,
            compute_digest_response('system', 'secret', 'myrealm', 'POST', '/VIID/System/Register', 'abc', 2, 'other'),
        )


class DigestClientFlowTests(unittest.IsolatedAsyncioTestCase):
    def _make_client(self, handler: httpx.MockTransport) -> Gat1400DigestClient:
        return Gat1400DigestClient(
            base_url='http://127.0.0.1:8080',
            username='system',
            password='secret',
            device_id='33010299011190000253',
            transport=handler,
        )

    async def test_401_challenge_then_authorized_retry(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if not request.headers.get('Authorization'):
                return httpx.Response(401, headers={'WWW-Authenticate': DAHUA_CHALLENGE})
            return httpx.Response(200, json={'ResponseStatusObject': {'StatusCode': 0, 'StatusString': '正常'}})

        client = self._make_client(httpx.MockTransport(handler))
        response = await client.post(
            '/VIID/System/Register', json_body={'RegisterObject': {'DeviceID': client.device_id}}
        )
        await client.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(calls), 2)
        auth = calls[1].headers.get('Authorization', '')
        self.assertIn('Digest username="system"', auth)
        self.assertIn('realm="myrealm"', auth)
        self.assertIn(f'nonce="{DAHUA_NONCE}"', auth)
        self.assertIn('uri="/VIID/System/Register"', auth)
        self.assertIn('qop=auth', auth)
        self.assertIn('nc=00000001', auth)
        self.assertIn('algorithm=MD5', auth)
        # 大华要求：请求携带 User-Identify 头，值为 DeviceID
        self.assertEqual(calls[1].headers.get('User-Identify'), '33010299011190000253')

    async def test_nc_increments_within_same_nonce(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if not request.headers.get('Authorization'):
                return httpx.Response(401, headers={'WWW-Authenticate': DAHUA_CHALLENGE})
            return httpx.Response(200, json={})

        client = self._make_client(httpx.MockTransport(handler))
        await client.post('/VIID/System/Keepalive', json_body={'KeepaliveObject': {'DeviceID': client.device_id}})
        await client.post('/VIID/System/Keepalive', json_body={'KeepaliveObject': {'DeviceID': client.device_id}})
        await client.close()

        # 请求 1 未认证，请求 2 挑战后重发 nc=1，请求 3 同 nonce 下 nc=2
        self.assertEqual(calls[2].headers.get('Authorization', '').split('nc=')[1].split(',')[0], '00000002')

    async def test_auth_failure_stops_after_one_retry(self) -> None:
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(401, headers={'WWW-Authenticate': DAHUA_CHALLENGE})

        client = self._make_client(httpx.MockTransport(handler))
        response = await client.post(
            '/VIID/System/Register', json_body={'RegisterObject': {'DeviceID': client.device_id}}
        )
        await client.close()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(call_count, 2)

    async def test_nonce_expiry_recovers_within_same_request(self) -> None:
        """nonce 被服务端重置后：携带旧 nonce 的请求收到 401 新挑战，同一次调用内换新 nonce 重试成功且 nc 重置。"""
        nonce_state = {'current': 'first-nonce'}
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            auth = request.headers.get('Authorization', '')
            if not auth or f'nonce="{nonce_state["current"]}"' not in auth:
                return httpx.Response(
                    401,
                    headers={'WWW-Authenticate': f'Digest realm="myrealm",qop="auth",nonce="{nonce_state["current"]}"'},
                )
            return httpx.Response(200, json={})

        client = self._make_client(httpx.MockTransport(handler))
        first = await client.post('/VIID/System/Keepalive', json_body={})
        # 服务端轮换 nonce（标准要求 3600s 内重置）
        nonce_state['current'] = 'second-nonce'
        after_rotation = await client.post('/VIID/System/Keepalive', json_body={})
        next_call = await client.post('/VIID/System/Keepalive', json_body={})
        await client.close()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(after_rotation.status_code, 200)
        self.assertEqual(next_call.status_code, 200)
        # 旋转后的请求：旧 nonce 被 401 挑战 → 换新 nonce 重发（nc 重置为 1）
        self.assertIn('nc=00000001', calls[3].headers.get('Authorization', ''))
        self.assertIn('nonce="second-nonce"', calls[3].headers.get('Authorization', ''))


if __name__ == '__main__':
    unittest.main()
