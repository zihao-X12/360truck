"""
端到端集成测试：真实 Gat1400DigestClient ↔ Mock 大华视图库（ASGITransport，免端口）。

覆盖：401 挑战→认证重发、User-Identify 头、nonce 递增、注册/保活/注销状态码、
订阅报文结构（大华 SubscribeListObject）、通知推送报文构造与解析。
"""

import json
import unittest

import httpx

from module_gat1400.service.gat1400_digest_client import Gat1400DigestClient
from module_gat1400.service.gat1400_notify_service import parse_notification_list
from tests.gat1400.mock_viid_server import (
    MOCK_DEVICE_ID,
    MOCK_PASSWORD,
    MOCK_USERNAME,
    app,
    push_notification,
    state,
)


def make_client() -> Gat1400DigestClient:
    return Gat1400DigestClient(
        base_url='http://mock-viid',
        username=MOCK_USERNAME,
        password=MOCK_PASSWORD,
        device_id=MOCK_DEVICE_ID,
        transport=httpx.ASGITransport(app=app),
    )


class MockServerIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        state.reset()

    async def test_full_session_flow_with_digest_auth(self) -> None:
        """注册 → 保活 ×2 → 注销，摘要认证全程通过，nc 递增。"""
        client = make_client()
        try:
            register = await client.post(
                '/VIID/System/Register', json_body={'RegisterObject': {'DeviceID': MOCK_DEVICE_ID}}
            )
            self.assertEqual(register.status_code, 200)
            self.assertEqual(register.json()['ResponseStatusObject']['StatusCode'], 0)
            self.assertTrue(state.registered)
            self.assertEqual(state.device_id, MOCK_DEVICE_ID)

            keepalive_1 = await client.post(
                '/VIID/System/Keepalive', json_body={'KeepaliveObject': {'DeviceID': MOCK_DEVICE_ID}}
            )
            keepalive_2 = await client.post(
                '/VIID/System/Keepalive', json_body={'KeepaliveObject': {'DeviceID': MOCK_DEVICE_ID}}
            )
            self.assertEqual(keepalive_1.status_code, 200)
            self.assertEqual(keepalive_2.status_code, 200)

            unregister = await client.post(
                '/VIID/System/UnRegister', json_body={'UnRegisterObject': {'DeviceID': MOCK_DEVICE_ID}}
            )
            self.assertEqual(unregister.status_code, 200)
            self.assertFalse(state.registered)
        finally:
            await client.close()

        # 认证观测：注册后的请求均携带 User-Identify 头（值 = DeviceID，大华要求）
        self.assertTrue(all(record['user_identify'] == MOCK_DEVICE_ID for record in state.auth_headers))
        # nc 序列递增（不含推送）
        nc_sequence = [record['nc'] for record in state.auth_headers]
        self.assertEqual(nc_sequence, sorted(nc_sequence))
        self.assertEqual(len(state.auth_headers), 4)  # 注册1 + 保活2 + 注销1

    async def test_unregistered_keepalive_rejected(self) -> None:
        """未注册时保活被拒绝（模拟真实平台行为）。"""
        client = make_client()
        try:
            response = await client.post(
                '/VIID/System/Keepalive', json_body={'KeepaliveObject': {'DeviceID': MOCK_DEVICE_ID}}
            )
        finally:
            await client.close()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ResponseStatusObject']['StatusCode'], 4)  # Invalid Operation

    async def test_subscribe_message_roundtrip(self) -> None:
        """真实客户端提交订阅 → mock 收到大华结构报文 → 返回平台 Id。"""
        client = make_client()
        try:
            await client.post('/VIID/System/Register', json_body={'RegisterObject': {'DeviceID': MOCK_DEVICE_ID}})
            subscribe_body = {
                'SubscribeListObject': {
                    'SubscribeObject': [
                        {
                            'SubscribeID': f'{MOCK_DEVICE_ID}03202608171000000001',
                            'Title': '过车',
                            'SubscribeDetail': '13',
                            'ResourceURI': '33110000005030000001',
                            'ApplicantName': 'admin',
                            'ApplicantOrg': 'org',
                            'BeginTime': '20260817090000',
                            'EndTime': '20260916090000',
                            'OperateType': '0',
                            'ReceiveAddr': 'http://127.0.0.1:9099/VIID/SubscribeNotifications',
                        }
                    ]
                }
            }
            response = await client.post('/VIID/Subscribes', json_body=subscribe_body)
        finally:
            await client.close()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['ResponseStatusListObject']['ResponseStatusObject'][0]['StatusCode'], 0)
        returned_id = body['ResponseStatusListObject']['ResponseStatusObject'][0]['Id']
        self.assertEqual(returned_id, f'{MOCK_DEVICE_ID}03202608171000000001')
        self.assertIn(returned_id, state.subscribes)
        # mock 侧订阅报文与提交一致
        self.assertEqual(state.subscribes[returned_id]['SubscribeDetail'], '13')

    async def test_notification_push_constructs_parseable_payload(self) -> None:
        """mock 推送的通知报文：结构符合大华文档、带摘要认证头、可被解析逻辑还原。"""
        state.registered = True
        state.device_id = MOCK_DEVICE_ID
        state.subscribes['SUB-001'] = {
            'SubscribeID': 'SUB-001',
            'Title': '过车',
            'ReceiveAddr': 'http://mock-callback/VIID/SubscribeNotifications',
        }
        vehicles = [
            {
                'MotorVehicleID': '330101010012100000010220171018080608022060269899',
                'PlateNo': '苏NF5676',
                'PlateColor': '5',
                'PassTime': '20160912220107',
                'Speed': 8,
                'LaneNo': 1,
                'StorageUrl1': 'http://x/1.jpg',
            }
        ]
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured['body'] = json.loads(request.content)
            captured['headers'] = dict(request.headers)
            return httpx.Response(200, json={})

        record = await push_notification(
            vehicles, http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )

        self.assertEqual(record['status_code'], 200)
        notification = captured['body']['SubscribeNotificationListObject']['SubscribeNotificationObject'][0]
        self.assertEqual(notification['SubscribeID'], 'SUB-001')
        self.assertEqual(notification['MotorVehicleObjectList']['MotorVehicleObject'][0]['PlateNo'], '苏NF5676')
        # 推送带摘要认证头与 User-Identify（模拟真实平台，真实回调侧联调需确认是否校验）
        self.assertIn('authorization', captured['headers'])
        self.assertEqual(captured['headers'].get('user-identify'), MOCK_DEVICE_ID)
        # 我方解析逻辑可完整还原
        self.assertEqual(len(parse_notification_list(captured['body'])), 1)

    async def test_notification_payload_structure(self) -> None:
        """通知报文的解析兼容性：mock 构造的报文能被 parse_notification_list 完整还原。"""
        notification = {
            'SubscribeNotificationListObject': {
                'SubscribeNotificationObject': [
                    {
                        'NotificationID': 'NOTIFY-002',
                        'SubscribeID': 'SUB-002',
                        'Title': '过车',
                        'TriggerTime': '20260817100000',
                        'InfoIDs': 'MV-1;MV-2',
                        'MotorVehicleObjectList': {
                            'MotorVehicleObject': [
                                {'MotorVehicleID': 'MV-1', 'PlateNo': '浙K12345', 'PassTime': '20260817100000'},
                                {'MotorVehicleID': 'MV-2', 'PlateNo': '浙K67890', 'PassTime': '20260817100001'},
                            ]
                        },
                    }
                ]
            }
        }
        parsed = parse_notification_list(notification)
        self.assertEqual(len(parsed), 1)
        vehicles = parsed[0]['MotorVehicleObjectList']['MotorVehicleObject']
        self.assertEqual([v['MotorVehicleID'] for v in vehicles], ['MV-1', 'MV-2'])
        # 报文可正常 JSON 序列化（走 Redis 队列的要求）
        self.assertIsInstance(json.dumps(notification, ensure_ascii=False), str)


if __name__ == '__main__':
    unittest.main()
