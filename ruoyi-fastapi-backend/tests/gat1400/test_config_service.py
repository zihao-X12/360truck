import unittest
from unittest.mock import AsyncMock, MagicMock

from module_gat1400.service.gat1400_config_service import (
    CONFIG_KEYS,
    Gat1400ConfigService,
    decrypt_password,
    encrypt_password,
)


class PasswordCryptoTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self) -> None:
        plain = 'MySecret123'
        stored = encrypt_password(plain)

        self.assertTrue(stored.startswith('enc:'))
        self.assertNotIn(plain, stored)
        self.assertEqual(decrypt_password(stored), plain)

    def test_decrypt_legacy_plain_returns_as_is(self) -> None:
        self.assertEqual(decrypt_password('plain-password'), 'plain-password')
        self.assertEqual(decrypt_password(''), '')

    def test_encrypt_empty_returns_empty(self) -> None:
        self.assertEqual(encrypt_password(''), '')


class ConfigServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_runtime_config_prefers_redis_cache(self) -> None:
        redis = AsyncMock()
        values = {
            'sys_config:gat1400.enabled': 'true',
            'sys_config:gat1400.platform.addr': 'http://10.0.0.1:8080',
            'sys_config:gat1400.device.id': '33112400005030000001',
        }

        async def fake_get(key: str) -> bytes | None:
            value = values.get(key)
            return value.encode() if value is not None else None

        redis.get = fake_get

        config = await Gat1400ConfigService.get_runtime_config(redis)

        self.assertEqual(config['enabled'], 'true')
        self.assertEqual(config['platform_addr'], 'http://10.0.0.1:8080')
        self.assertEqual(config['device_id'], '33112400005030000001')
        # 未在 Redis 的键回退 .env 默认值
        self.assertEqual(config['subscribe_detail'], '13')

    async def test_get_runtime_config_decrypts_password(self) -> None:
        redis = AsyncMock()
        redis.get = AsyncMock(return_value=encrypt_password('secret123').encode())

        config = await Gat1400ConfigService.get_runtime_config(redis)

        self.assertEqual(config['password'], 'secret123')

    async def test_get_config_for_api_masks_password(self) -> None:
        db = AsyncMock()
        row = MagicMock()
        row.config_key = 'gat1400.auth.password'
        row.config_value = encrypt_password('secret123')
        db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[row]))))
        )

        result = await Gat1400ConfigService.get_config_for_api(db)

        self.assertTrue(result['passwordSet'])
        self.assertEqual(result['password'], '********')
        self.assertEqual(result['enabled'], 'false')  # 未配置键回退 .env 默认

    async def test_save_config_encrypts_password_and_refreshes_cache(self) -> None:
        db = AsyncMock()
        redis = AsyncMock()
        existing_row = MagicMock()
        existing_row.config_key = 'gat1400.enabled'
        db.execute = AsyncMock(
            return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[existing_row])))
            )
        )

        await Gat1400ConfigService.save_config(
            db,
            redis,
            {'enabled': True, 'password': 'new-secret', 'platform_addr': 'http://10.0.0.1:8080'},
        )

        # 已有行更新 + 两个新行（password / platform_addr）
        self.assertEqual(existing_row.config_value, 'true')
        added = {row.config_key: row for row in [call.args[0] for call in db.add.call_args_list]}
        self.assertEqual(set(added.keys()), {'gat1400.auth.password', 'gat1400.platform.addr'})
        self.assertTrue(added['gat1400.auth.password'].config_value.startswith('enc:'))  # 密码加密存储
        # Redis 缓存刷新
        redis.set.assert_any_call('sys_config:gat1400.enabled', 'true')
        redis.set.assert_any_call('sys_config:gat1400.auth.password', added['gat1400.auth.password'].config_value)
        db.commit.assert_awaited_once()

    async def test_save_config_keeps_password_when_masked(self) -> None:
        db = AsyncMock()
        redis = AsyncMock()
        db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
        )

        await Gat1400ConfigService.save_config(db, redis, {'password': '********'})

        # 掩码值不写库
        added = [call.args[0] for call in db.add.call_args_list]
        self.assertFalse(any(getattr(row, 'config_key', '') == CONFIG_KEYS['password'] for row in added))


if __name__ == '__main__':
    unittest.main()
