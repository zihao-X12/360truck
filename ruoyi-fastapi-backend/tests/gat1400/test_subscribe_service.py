import json
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from module_gat1400.service.gat1400_subscribe_service import (
    DATETIME_FORMAT,
    DEFAULT_TITLE,
    Gat1400SubscribeService,
    format_time,
    parse_time,
)


class FakeResponse:
    """模拟 httpx.Response：status_code/content/text/json 三件套。"""

    def __init__(self, status_code: int, body: dict | None) -> None:
        self.status_code = status_code
        self.content = json.dumps(body).encode('utf-8') if body is not None else b''
        self.text = self.content.decode('utf-8')

    def json(self) -> dict | None:
        return json.loads(self.content) if self.content else None


class FormatTimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_format_time_is_compact_dahua_format(self) -> None:
        dt = datetime(2017, 12, 1, 10, 30, 15)

        self.assertEqual(format_time(dt), '20171201103015')
        self.assertEqual(dt.strftime(DATETIME_FORMAT), '20171201103015')

    async def test_parse_time_roundtrip(self) -> None:
        dt = datetime(2017, 12, 1, 10, 30, 15)

        self.assertEqual(parse_time('20171201103015'), dt)

    async def test_parse_time_rejects_invalid(self) -> None:
        self.assertIsNone(parse_time('not-a-time'))
        self.assertIsNone(parse_time('20171301103015'))  # 非法月份
        self.assertIsNone(parse_time(None))


class SubscribeMessageTests(unittest.IsolatedAsyncioTestCase):
    async def test_subscribe_id_format(self) -> None:
        """SubscribeID = DeviceID(20) + '03' + yyyyMMddHHmmss + 5位流水。"""
        subscribe_id = Gat1400SubscribeService._subscribe_id('33112400005030000001', 42)

        self.assertEqual(len(subscribe_id), 41)
        self.assertTrue(subscribe_id.startswith('33112400005030000001'))
        self.assertIn('03', subscribe_id[20:22])
        self.assertRegex(subscribe_id[22:36], r'^\d{14}$')  # 时间戳段
        self.assertEqual(subscribe_id[36:], '00042')

    async def test_build_subscribe_message_matches_dahua_structure(self) -> None:
        config = {
            'subscribe_detail': '13',
            'subscribe_resource_uri': '33110000005030000001',
            'applicant_name': '松阳大队',
            'applicant_org': '松阳县公安局',
            'receive_addr': 'http://10.0.0.1/VIID/SubscribeNotifications',
        }
        begin = datetime(2026, 8, 17, 9, 0, 0)
        end = datetime(2026, 9, 16, 9, 0, 0)

        message = Gat1400SubscribeService.build_subscribe_message(
            '33112400005030000001032026081709000000001', begin, end, config
        )

        subscribe = message['SubscribeListObject']['SubscribeObject'][0]
        self.assertEqual(subscribe['SubscribeDetail'], '13')
        self.assertEqual(subscribe['ResourceURI'], '33110000005030000001')
        self.assertEqual(subscribe['BeginTime'], '20260817090000')
        self.assertEqual(subscribe['EndTime'], '20260916090000')
        self.assertEqual(subscribe['OperateType'], '0')
        self.assertEqual(subscribe['ReceiveAddr'], 'http://10.0.0.1/VIID/SubscribeNotifications')
        self.assertEqual(subscribe['Title'], DEFAULT_TITLE)

    async def test_build_cancel_message_contains_cancel_fields(self) -> None:
        config = {'applicant_name': '松阳大队', 'applicant_org': '松阳县公安局'}

        message = Gat1400SubscribeService.build_cancel_message(config)

        cancel = message['SubscribeObject']
        self.assertEqual(cancel['SubscribeCancelOrg'], '松阳县公安局')
        self.assertEqual(cancel['SubscribeCancelPerson'], '松阳大队')
        self.assertRegex(cancel['CancelTime'], r'^\d{14}$')
        self.assertEqual(cancel['CancelReason'], '服务到期')


def make_runtime_config(**overrides: str) -> dict:
    """构造运行时配置字典（create_subscribe 测试用）。"""
    config = {
        'enabled': 'true',
        'platform_addr': 'http://mock',
        'device_id': '33112400005030000001',
        'username': 'system',
        'password': 'secret',
        'keepalive_interval': '60',
        'subscribe_detail': '13',
        'subscribe_resource_uri': '33110000005030000001',
        'applicant_name': 'admin',
        'applicant_org': 'org',
        'subscribe_days': '30',
        'receive_addr': 'http://10.0.0.1/VIID/SubscribeNotifications',
        'notify_allowed_ips': '',
    }
    config.update(overrides)
    return config


class CreateSubscribeTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_subscribe_skips_when_receive_addr_missing(self) -> None:
        db = AsyncMock()
        redis = AsyncMock()
        with patch(
            'module_gat1400.service.gat1400_config_service.Gat1400ConfigService.get_runtime_config',
            AsyncMock(return_value=make_runtime_config(receive_addr='')),
        ):
            record = await Gat1400SubscribeService.create_subscribe(db, redis)

        self.assertIsNone(record)

    async def test_create_subscribe_uses_platform_returned_id(self) -> None:
        db = AsyncMock()
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=1)
        fake_client = AsyncMock()
        fake_client.device_id = '33112400005030000001'
        fake_client.post = AsyncMock(
            return_value=FakeResponse(
                200,
                {
                    'ResponseStatusListObject': {
                        'ResponseStatusObject': [{'StatusCode': 0, 'Id': 'PLATFORM-RETURNED-ID'}]
                    }
                },
            )
        )

        with (
            patch(
                'module_gat1400.service.gat1400_subscribe_service.Gat1400SessionService._get_client',
                AsyncMock(return_value=fake_client),
            ),
            patch(
                'module_gat1400.service.gat1400_config_service.Gat1400ConfigService.get_runtime_config',
                AsyncMock(return_value=make_runtime_config()),
            ),
            patch(
                'module_gat1400.service.gat1400_subscribe_service.Gat1400SubscribeDao.add', new_callable=AsyncMock
            ) as dao_add,
        ):
            dao_add.return_value = type('Rec', (), {'subscribe_id': 'PLATFORM-RETURNED-ID'})()
            record = await Gat1400SubscribeService.create_subscribe(db, redis)

        self.assertEqual(record.subscribe_id, 'PLATFORM-RETURNED-ID')
        # 平台返回 Id 时以平台为准，落库用返回 ID
        self.assertEqual(dao_add.await_args.kwargs['subscribe_id'], 'PLATFORM-RETURNED-ID')

    async def test_create_subscribe_keeps_local_id_when_response_has_no_id(self) -> None:
        db = AsyncMock()
        redis = AsyncMock()
        redis.incr = AsyncMock(return_value=7)
        fake_client = AsyncMock()
        fake_client.device_id = '33112400005030000001'
        fake_client.post = AsyncMock(
            return_value=FakeResponse(200, {'ResponseStatusListObject': {'ResponseStatusObject': [{'StatusCode': 0}]}})
        )
        with (
            patch(
                'module_gat1400.service.gat1400_subscribe_service.Gat1400SessionService._get_client',
                AsyncMock(return_value=fake_client),
            ),
            patch(
                'module_gat1400.service.gat1400_config_service.Gat1400ConfigService.get_runtime_config',
                AsyncMock(return_value=make_runtime_config()),
            ),
            patch(
                'module_gat1400.service.gat1400_subscribe_service.Gat1400SubscribeDao.add', new_callable=AsyncMock
            ) as dao_add,
        ):
            dao_add.return_value = type('Rec', (), {'subscribe_id': 'local'})()
            await Gat1400SubscribeService.create_subscribe(db, redis)

        # 平台未返回 Id 时回退到本地生成的 SubscribeID（41位，含时间戳，用正则校验）
        local_id = dao_add.await_args.kwargs['subscribe_id']
        self.assertRegex(local_id, r'^33112400005030000001\d{21}$')


if __name__ == '__main__':
    unittest.main()
