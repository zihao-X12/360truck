import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from module_gat1400.service.gat1400_session_service import (
    MAX_FAIL_COUNT,
    NEXT_RETRY_KEY,
    STATUS_OFFLINE,
    STATUS_ONLINE,
    STATUS_UNREGISTERED,
    Gat1400SessionService,
    _extract_status_code,
)


class FakeResponse:
    """模拟 httpx.Response：供 parse_response_body 静态方法解析。"""

    def __init__(self, status_code: int, body: dict | None) -> None:
        self.status_code = status_code
        self.content = json.dumps(body).encode('utf-8') if body is not None else b''
        self.text = self.content.decode('utf-8')

    def json(self) -> dict | None:
        return json.loads(self.content) if self.content else None


class FakeClient:
    """模拟摘要认证客户端，记录发出的请求路径与消息体。"""

    def __init__(self) -> None:
        self.device_id = '33010299011190000253'
        self.post_calls: list[tuple[str, dict]] = []
        self.next_response = FakeResponse(200, {'ResponseStatusObject': {'StatusCode': 0}})

    async def post(self, path: str, json_body: dict | None = None) -> 'FakeResponse':
        self.post_calls.append((path, json_body))
        return self.next_response

    async def close(self) -> None:
        pass


class ExtractStatusCodeTests(unittest.TestCase):
    def test_object_form(self) -> None:
        self.assertEqual(_extract_status_code({'ResponseStatusObject': {'StatusCode': 0}}), 0)

    def test_list_form(self) -> None:
        self.assertEqual(_extract_status_code({'ResponseStatusObject': [{'StatusCode': 4}]}), 4)

    def test_missing_field(self) -> None:
        # 有 ResponseStatusObject 但缺 StatusCode：返回 -1（非成功，调用方按失败处理）
        self.assertEqual(_extract_status_code({'ResponseStatusObject': {}}), -1)
        self.assertIsNone(_extract_status_code({}))
        self.assertIsNone(_extract_status_code(None))


def make_row(status: str = STATUS_UNREGISTERED, fail_count: int = 0) -> MagicMock:
    row = MagicMock()
    row.register_status = status
    row.fail_count = fail_count
    row.keepalive_count = 0
    row.error_message = ''
    row.last_keepalive_time = None
    return row


def patch_session(db: AsyncMock, row: MagicMock) -> tuple[FakeClient, MagicMock]:
    """打桩：客户端与 DAO，返回 (fake_client, dao_mock)。"""
    client = FakeClient()
    patcher_client = patch.object(Gat1400SessionService, '_get_client', return_value=client)
    patcher_dao = patch('module_gat1400.service.gat1400_session_service.Gat1400ConnectDao')
    patcher_client.start()
    dao = patcher_dao.start()
    dao.get_or_create = AsyncMock(return_value=row)
    dao.get_status = AsyncMock(return_value=row)

    async def update_status(_db: AsyncMock, _row: MagicMock, **fields) -> None:
        for key, value in fields.items():
            setattr(_row, key, value)

    dao.update_status = AsyncMock(side_effect=update_status)
    return client, dao


def stop_patch() -> None:
    patch.stopall()


class SessionServiceTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        stop_patch()
        return super().tearDown()

    async def test_register_success_sets_online(self) -> None:
        db = AsyncMock()
        row = make_row()
        client, _ = patch_session(db, row)
        redis = AsyncMock()

        result = await Gat1400SessionService.register(db, redis, force=True)

        self.assertTrue(result)
        self.assertEqual(row.register_status, STATUS_ONLINE)
        self.assertEqual(row.fail_count, 0)
        db.commit.assert_awaited_once()
        # 注册消息体：RegisterObject 包装 DeviceID（对照大华文档示例）
        self.assertEqual(
            client.post_calls[0], ('/VIID/System/Register', {'RegisterObject': {'DeviceID': client.device_id}})
        )
        # 注册成功后清除重试时间缓存
        redis.delete.assert_awaited_once_with(NEXT_RETRY_KEY)

    async def test_register_failure_goes_offline_and_schedules_retry(self) -> None:
        db = AsyncMock()
        row = make_row()
        client, _ = patch_session(db, row)
        redis = AsyncMock()
        client.next_response = FakeResponse(401, {'ResponseStatusObject': {'StatusCode': 4}})

        result = await Gat1400SessionService.register(db, redis, force=True)

        self.assertFalse(result)
        self.assertEqual(row.register_status, STATUS_OFFLINE)
        self.assertEqual(row.fail_count, 1)
        self.assertTrue(row.error_message)
        # 安排了随机延迟重试（Redis 缓存了下次重试时间）
        redis.set.assert_awaited_once()

    async def test_register_skips_when_retry_not_due(self) -> None:
        db = AsyncMock()
        row = make_row(status=STATUS_OFFLINE)
        client, _ = patch_session(db, row)
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b'2099-01-01 00:00:00')

        result = await Gat1400SessionService.register(db, redis, force=False)

        self.assertFalse(result)
        # 未到重试时间，未发起注册请求
        self.assertEqual(client.post_calls, [])

    async def test_register_proceeds_when_retry_due(self) -> None:
        db = AsyncMock()
        row = make_row(status=STATUS_OFFLINE)
        client, _ = patch_session(db, row)
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)

        result = await Gat1400SessionService.register(db, redis, force=False)

        self.assertTrue(result)
        self.assertEqual(len(client.post_calls), 1)

    async def test_keepalive_three_failures_force_offline(self) -> None:
        db = AsyncMock()
        row = make_row(status=STATUS_ONLINE)
        client, _ = patch_session(db, row)
        redis = AsyncMock()
        client.next_response = FakeResponse(500, None)

        for _ in range(MAX_FAIL_COUNT):
            result = await Gat1400SessionService.keepalive(db, redis)
            self.assertFalse(result)

        self.assertEqual(row.register_status, STATUS_OFFLINE)
        self.assertEqual(row.fail_count, MAX_FAIL_COUNT)

    async def test_keepalive_success_resets_fail_count(self) -> None:
        db = AsyncMock()
        row = make_row(status=STATUS_ONLINE, fail_count=2)
        client, _ = patch_session(db, row)
        redis = AsyncMock()

        result = await Gat1400SessionService.keepalive(db, redis)

        self.assertTrue(result)
        self.assertEqual(row.fail_count, 0)
        self.assertEqual(row.keepalive_count, 1)
        self.assertIsNotNone(row.last_keepalive_time)
        self.assertEqual(
            client.post_calls[0], ('/VIID/System/Keepalive', {'KeepaliveObject': {'DeviceID': client.device_id}})
        )

    async def test_unregister_success_sets_unregistered(self) -> None:
        db = AsyncMock()
        row = make_row(status=STATUS_ONLINE)
        client, _ = patch_session(db, row)
        redis = AsyncMock()

        result = await Gat1400SessionService.unregister(db, redis)

        self.assertTrue(result)
        self.assertEqual(row.register_status, STATUS_UNREGISTERED)
        self.assertEqual(
            client.post_calls[0], ('/VIID/System/UnRegister', {'UnRegisterObject': {'DeviceID': client.device_id}})
        )


if __name__ == '__main__':
    unittest.main()
