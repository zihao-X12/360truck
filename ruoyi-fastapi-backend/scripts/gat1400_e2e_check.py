"""
GA/T1400 完整链路本地验证脚本（P4）。

验证链路（真实部署形态）：
Mock 平台(18080) 推送 → 运行中的后端(9099 /VIID/SubscribeNotifications 回调) →
Redis 队列 → 后端消费循环落库 → 过车记录查询。

前置条件：
1. 本地 MySQL（3306）与 Redis（6379）已启动
2. 后端已启动（local-dev-start.ps1 或手动，代码需为包含 module_gat1400 的最新版本）
3. .env.dev 中 GAT1400_SUBSCRIBE_RECEIVE_ADDR 未配置时本脚本通过 patch 注入

用法：
    cd ruoyi-fastapi-backend
    .venv/Scripts/python.exe scripts/gat1400_e2e_check.py
"""

import asyncio
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

MOCK_PORT = 18080
BACKEND_URL = 'http://127.0.0.1:9099'
MOCK_URL = f'http://127.0.0.1:{MOCK_PORT}'
# 回调地址指向运行中的真实后端（PreAuth 白名单 + /VIID 传输加密排除已就绪）
CALLBACK_URL = f'{BACKEND_URL}/VIID/SubscribeNotifications'
E2E_DEVICE_ID = '33112400005030000001'
E2E_USERNAME = 'system'
E2E_PASSWORD = 'secret'

# 本轮测试的车辆（固定 MotorVehicleID 以便幂等验证）
E2E_VEHICLES = [
    {
        'MotorVehicleID': 'E2E-MV-000000000000000000000000000001',
        'InfoKind': 1,
        'DeviceID': '65010000001190000001',
        'TollgateID': 'TG-E2E-1',
        'PlateNo': '浙K88888',
        'PlateColor': '5',
        'VehicleClass': '1',
        'PassTime': '20260817103000',
        'NameOfPassedRoad': '松阳大道',
        'LaneNo': 1,
        'Speed': 65,
        'Direction': '1',
        'StorageUrl1': 'http://mock/photo/1.jpg',
    },
    {
        'MotorVehicleID': 'E2E-MV-000000000000000000000000000002',
        'InfoKind': 1,
        'DeviceID': '65010000001190000001',
        'TollgateID': 'TG-E2E-1',
        'PlateNo': '浙K66666',
        'PlateColor': '6',
        'VehicleClass': '2',
        'PassTime': '20260817103100',
        'NameOfPassedRoad': '古市大道',
        'LaneNo': 2,
        'Speed': 58,
        'Direction': '2',
    },
]


async def _wait_for_record_count(expected: int, timeout: float = 90.0) -> int:
    """
    轮询等待过车记录数达到期望值（等后端消费循环落库）。

    注意：每次轮询必须使用新 session——MySQL REPEATABLE READ 下同一事务内的
    多次查询共享首次 SELECT 的一致性快照，若首次查询早于后端 COMMIT，
    后续轮询将永远看到旧值。
    """
    from sqlalchemy import func, select

    from config.database import SessionLocal
    from module_gat1400.entity.do.pass_record_do import TruckPassRecord

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        async with SessionLocal() as db:
            count = (db.execute(select(func.count()).select_from(TruckPassRecord))).scalar()
        if count >= expected:
            return count
        await asyncio.sleep(1.0)
    return count


async def run_async() -> None:
    from config.database import SessionLocal
    from config.get_redis import RedisUtil
    from module_gat1400.dao.gat1400_subscribe_dao import Gat1400SubscribeDao
    from module_gat1400.entity.vo.pass_record_vo import PassRecordPageQueryModel
    from module_gat1400.service.gat1400_session_service import STATUS_ONLINE, Gat1400SessionService
    from module_gat1400.service.gat1400_subscribe_service import Gat1400SubscribeService
    from module_gat1400.service.pass_record_service import PassRecordService

    # ---- 1. 配置注入（写入 sys_config Redis 缓存，模拟页面可视化配置；真实部署由平台页面配置） ----
    redis = await RedisUtil.create_redis_pool(log_enabled=False)
    e2e_config_keys = {
        'gat1400.enabled': 'true',
        'gat1400.platform.addr': MOCK_URL,
        'gat1400.device.id': E2E_DEVICE_ID,
        'gat1400.auth.username': E2E_USERNAME,
        'gat1400.auth.password': E2E_PASSWORD,
        'gat1400.keepalive.interval': '60',
        'gat1400.subscribe.detail': '13',
        'gat1400.subscribe.resource.uri': '33110000005030000001',
        'gat1400.subscribe.applicant.name': 'E2E测试',
        'gat1400.subscribe.applicant.org': '松阳县公安局',
        'gat1400.subscribe.days': '30',
        'gat1400.subscribe.receive.addr': CALLBACK_URL,
        'gat1400.notify.allowed.ips': '',
    }
    for key, value in e2e_config_keys.items():
        await redis.set(f'sys_config:{key}', value)

    # ---- 2. 注册 → 保活（走真实 HTTP 到 Mock 平台） ----
    async with SessionLocal() as db:
        assert Gat1400SessionService.register(db, redis, force=True), '注册失败'
        assert Gat1400SessionService.keepalive(db, redis), '保活失败'
        status = Gat1400SessionService.get_status(db, redis)
        assert status['registerStatus'] == STATUS_ONLINE, f'状态异常: {status["registerStatus"]}'
        print(f'[OK] 注册/保活成功，状态={status["registerStatus"]}，保活次数={status["keepaliveCount"]}')

        # ---- 3. 订阅（走真实 HTTP 到 Mock 平台） ----
        Gat1400SubscribeService.ensure_subscribe(db, redis)
        subscribe = Gat1400SubscribeDao.get_active_subscribe(db)
        assert subscribe, '订阅未创建成功'
        print(f'[OK] 订阅创建成功: {subscribe.subscribe_id}（类别 {subscribe.subscribe_detail}）')

    # ---- 4. Mock 推送 → 9099 后端回调 → Redis 队列 → 后端消费落库 ----
    async with httpx.AsyncClient(timeout=10) as http:
        push_response = await http.post(f'{MOCK_URL}/mock/push', json={'vehicles': E2E_VEHICLES})
        assert push_response.status_code == 200, f'推送失败: {push_response.text}'
        print(f'[OK] Mock 平台推送成功（回调地址: {push_response.json()["receive_addr"]}）')

    count = await _wait_for_record_count(2)
    assert count >= 2, f'过车记录落库超时: {count}'
    print(f'[OK] 过车记录落库 {count} 条（经 9099 后端消费循环）')

    # ---- 5. 重复推送验证幂等 ----
    async with httpx.AsyncClient(timeout=10) as http:
        await http.post(f'{MOCK_URL}/mock/push', json={'vehicles': [E2E_VEHICLES[0]]})
    await asyncio.sleep(2)  # 等待消费
    async with SessionLocal() as db:
        from sqlalchemy import func, select

        from module_gat1400.entity.do.pass_record_do import TruckPassRecord

        count = (db.execute(select(func.count()).select_from(TruckPassRecord))).scalar()
        assert count == 2, f'重复推送后数量异常（应仍为2）: {count}'
        print('[OK] 重复推送幂等验证通过（仍为 2 条，motor_vehicle_id 去重生效）')

    # ---- 6. 过车记录查询接口 ----
    async with SessionLocal() as db:
        result = PassRecordService.get_list(db, PassRecordPageQueryModel(plate_no='浙K'), True, True)
        assert result.total >= 2, f'查询结果异常: total={result.total}'
        first = result.rows[0]
        print(f'[OK] 过车记录查询通过（total={result.total}，首条车牌 {first["plateNo"]}）')

    # ---- 7. 清理：注销 + 取消订阅 + 清除注入配置 ----
    async with SessionLocal() as db:
        Gat1400SessionService.unregister(db, redis)
        Gat1400SubscribeService.cancel_subscribe(db, redis)
    for key in e2e_config_keys:
        await redis.delete(f'sys_config:{key}')
    await redis.aclose()
    print('[OK] 清理完成（已注销并取消订阅，注入配置已清除）')
    print('\n[DONE] GA/T1400 完整链路验证通过！')


async def main() -> None:
    # 确认后端在运行
    async with httpx.AsyncClient(timeout=5) as http:
        try:
            await http.get(f'{BACKEND_URL}/captchaImage', timeout=3)
        except Exception:
            print(f'[ERROR] 后端未运行（{BACKEND_URL}），请先 local-dev-start.ps1 启动')
            sys.exit(1)
    # 启动 Mock 平台（子进程）
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mock_process = subprocess.Popen(
        [
            sys.executable,
            '-m',
            'uvicorn',
            'tests.gat1400.mock_viid_server:app',
            '--host',
            '127.0.0.1',
            '--port',
            str(MOCK_PORT),
            '--log-level',
            'warning',
        ],
        cwd=backend_root,
    )
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            for _ in range(50):
                try:
                    await http.get(f'{MOCK_URL}/VIID/System/Time')
                    break
                except Exception:
                    await asyncio.sleep(0.2)
        await run_async()
    finally:
        mock_process.terminate()
        mock_process.wait(timeout=10)


if __name__ == '__main__':
    asyncio.run(main())
