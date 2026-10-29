"""
GA/T1400 通知接收与过车记录落库。

处理链路：
回调接口（同步快速响应）→ Redis 队列（原始报文）→ 后台消费循环 → 解析 → 落库

报文结构对照大华文档"通知相关接口"：
    SubscribeNotificationListObject.SubscribeNotificationObject[]，
    每个通知内含 MotorVehicleObjectList.MotorVehicleObject[]（过车记录）。

兼容标准 GA/T 1400.3 附录 C.20 的命名（SubscribeNotificationList）。
落库与去重：按 MotorVehicleID 全局唯一 upsert（truck_pass_record.motor_vehicle_id 唯一键），
重复推送（对方补传/重传）幂等处理。
"""

import asyncio
import json
import os
from typing import Any
from uuid import uuid4

from redis import asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import AsyncSessionLocal
from module_gat1400.dao.gat1400_notify_log_dao import Gat1400NotifyLogDao
from module_gat1400.dao.gat1400_subscribe_dao import Gat1400SubscribeDao
from module_gat1400.dao.pass_record_dao import TruckPassRecordDao
from module_gat1400.entity.do.gat1400_notify_log_do import Gat1400NotifyLog
from module_gat1400.service.gat1400_subscribe_service import parse_time
from utils.log_util import logger

NOTIFY_STREAM_KEY = 'gat1400:notify:stream'
NOTIFY_STREAM_GROUP = 'gat1400-notify-workers'
NOTIFY_DEAD_LETTER_KEY = 'gat1400:notify:dead'
NOTIFY_STREAM_BLOCK_MS = 5000
NOTIFY_CLAIM_IDLE_MS = 60000
NOTIFY_CLAIM_BATCH_SIZE = 50

# 解析状态
PARSE_SUCCESS = 'success'
PARSE_SUBSCRIBE_MISMATCH = 'subscribe_mismatch'
PARSE_NO_VEHICLE_DATA = 'no_vehicle_data'


def parse_notification_list(body: dict | None) -> list[dict]:
    """
    从通知报文提取通知对象列表，兼容大华与国标两种包装命名：
    - 大华：SubscribeNotificationListObject.SubscribeNotificationObject[]
    - 国标：SubscribeNotificationList.SubscribeNotificationObject[]
    包装值本身为数组时也兼容。
    """
    if not isinstance(body, dict):
        return []
    for wrapper_key in ('SubscribeNotificationListObject', 'SubscribeNotificationList'):
        wrapper = body.get(wrapper_key)
        if isinstance(wrapper, list):
            return [item for item in wrapper if isinstance(item, dict)]
        if isinstance(wrapper, dict):
            items = wrapper.get('SubscribeNotificationObject')
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
            if isinstance(items, dict):
                return [items]
    return []


def extract_motor_vehicles(notification: dict) -> list[dict]:
    """
    从单个通知提取过车记录列表，兼容多种结构：
    - MotorVehicleObjectList.MotorVehicleObject[]（大华）
    - MotorVehicleObjectList 本身为数组
    """
    raw = notification.get('MotorVehicleObjectList')

    def _as_list(value: Any) -> list[dict]:
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for key in ('MotorVehicleObject', 'MotorVehicle'):
                if key in value:
                    return _as_list(value[key])
        return []

    return _as_list(raw)


def _to_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def map_vehicle_fields(item: dict) -> dict:
    """MotorVehicle 对象 → truck_pass_record 字段映射。"""
    return {
        'motor_vehicle_id': str(item.get('MotorVehicleID', '')) or None,
        'info_kind': _to_int(item.get('InfoKind')),
        'device_id': item.get('DeviceID'),
        'tollgate_id': item.get('TollgateID'),
        'plate_no': item.get('PlateNo'),
        'plate_class': item.get('PlateClass'),
        'plate_color': item.get('PlateColor'),
        'vehicle_class': item.get('VehicleClass'),
        'vehicle_color': item.get('VehicleColor'),
        'pass_time': parse_time(str(item['PassTime'])) if item.get('PassTime') else None,
        'name_of_passed_road': item.get('NameOfPassedRoad'),
        'lane_no': _to_int(item.get('LaneNo')),
        'speed': _to_int(item.get('Speed')),
        'direction': item.get('Direction'),
        'has_plate': str(item['HasPlate']) if item.get('HasPlate') is not None else None,
        'is_suspicious': str(item['IsSuspicious']) if item.get('IsSuspicious') is not None else None,
        'storage_url1': item.get('StorageUrl1'),
        'storage_url2': item.get('StorageUrl2'),
        'storage_url3': item.get('StorageUrl3'),
        'storage_url4': item.get('StorageUrl4'),
        'storage_url5': item.get('StorageUrl5'),
        'plate_reliability': item.get('PlateReliability'),
        'raw_json': item,
    }


class Gat1400NotifyService:
    _consume_task: asyncio.Task | None = None

    @classmethod
    async def enqueue_notify(cls, redis: aioredis.Redis, raw_body: str) -> None:
        """写入可靠 Stream；消息仅在数据库提交成功后确认。"""
        await redis.xadd(NOTIFY_STREAM_KEY, {'raw_body': raw_body})

    @classmethod
    async def _ensure_group(cls, redis: aioredis.Redis) -> None:
        try:
            await redis.xgroup_create(NOTIFY_STREAM_KEY, NOTIFY_STREAM_GROUP, id='0-0', mkstream=True)
        except Exception as exc:
            if 'BUSYGROUP' not in str(exc):
                raise

    @classmethod
    async def _dead_letter(cls, redis: aioredis.Redis, raw_body: str, reason: str) -> None:
        await redis.xadd(NOTIFY_DEAD_LETTER_KEY, {'raw_body': raw_body, 'reason': reason})

    @classmethod
    async def persist_notification(cls, db: AsyncSession, notification: dict) -> Gat1400NotifyLog | None:
        """
        解析单个通知并落库：通知日志 + 过车记录批量 upsert + 车牌匹配车辆档案。
        """
        notification_id = notification.get('NotificationID')
        subscribe_id = notification.get('SubscribeID')
        trigger_time = parse_time(str(notification['TriggerTime'])) if notification.get('TriggerTime') else None
        vehicles = extract_motor_vehicles(notification)

        # 订阅校验：找不到有效订阅时标记状态（联调期不丢弃数据，仅告警）
        parse_status = PARSE_SUCCESS
        if not await Gat1400SubscribeDao.get_by_id(db, subscribe_id or ''):
            parse_status = PARSE_SUBSCRIBE_MISMATCH
            logger.warning(f'⚠️ GA/T1400 通知的订阅ID不在有效订阅表内: {subscribe_id}')
        if not vehicles:
            parse_status = PARSE_NO_VEHICLE_DATA

        record_count = 0
        if vehicles:
            record_count = await cls._upsert_pass_records(db, vehicles)

        notify_log = await Gat1400NotifyLogDao.add(
            db,
            notification_id=notification_id,
            subscribe_id=subscribe_id,
            trigger_time=trigger_time,
            parse_status=parse_status,
            record_count=record_count,
            raw_body=json.dumps(notification, ensure_ascii=False),
        )
        await db.commit()
        return notify_log

    @classmethod
    async def _upsert_pass_records(cls, db: AsyncSession, vehicles: list[dict]) -> int:
        """过车记录批量 upsert（motor_vehicle_id 去重）+ 车牌匹配车辆档案回填 vehicle_id。"""
        fields_list = []
        seen_ids: set[str] = set()
        for item in vehicles:
            fields = map_vehicle_fields(item)
            motor_vehicle_id = fields.get('motor_vehicle_id')
            if not motor_vehicle_id or motor_vehicle_id in seen_ids:
                continue
            seen_ids.add(motor_vehicle_id)
            fields_list.append(fields)

        existing_ids = await TruckPassRecordDao.get_existing_ids(
            db, [fields['motor_vehicle_id'] for fields in fields_list]
        )
        for fields in fields_list:
            if fields['motor_vehicle_id'] in existing_ids:
                await TruckPassRecordDao.update_by_motor_vehicle_id(
                    db,
                    fields['motor_vehicle_id'],
                    **{key: value for key, value in fields.items() if key != 'motor_vehicle_id'},
                )
            else:
                await TruckPassRecordDao.add(db, **fields)

        # 按车牌匹配本平台车辆档案（唯一匹配才回填，多车同牌不回填避免误关联）
        plates = [fields['plate_no'] for fields in fields_list if fields.get('plate_no')]
        plate_vehicle_map = await TruckPassRecordDao.get_vehicle_ids_by_plates(db, plates)
        for fields in fields_list:
            plate_no = fields.get('plate_no')
            vehicle_ids = plate_vehicle_map.get(plate_no, []) if plate_no else []
            if len(vehicle_ids) == 1:
                await TruckPassRecordDao.update_by_motor_vehicle_id(
                    db, fields['motor_vehicle_id'], vehicle_id=vehicle_ids[0]
                )
        return len(fields_list)

    @classmethod
    async def _process_messages(cls, redis: aioredis.Redis, messages: list[tuple[str, dict]]) -> None:
        """处理 Stream 消息；只有确定不可恢复的坏报文才进死信并确认。"""
        for message_id, data in messages:
            raw_body = data.get('raw_body', '')
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError:
                await cls._dead_letter(redis, raw_body, 'invalid_json')
                await redis.xack(NOTIFY_STREAM_KEY, NOTIFY_STREAM_GROUP, message_id)
                logger.error('❌ GA/T1400 通知报文非 JSON，已进死信 Stream')
                continue
            notifications = parse_notification_list(body)
            if not notifications:
                await cls._dead_letter(redis, raw_body, 'invalid_notification_structure')
                await redis.xack(NOTIFY_STREAM_KEY, NOTIFY_STREAM_GROUP, message_id)
                logger.error('❌ GA/T1400 通知结构无效，已进死信 Stream')
                continue
            try:
                async with AsyncSessionLocal() as db:
                    for notification in notifications:
                        await cls.persist_notification(db, notification)
                await redis.xack(NOTIFY_STREAM_KEY, NOTIFY_STREAM_GROUP, message_id)
            except Exception as exc:
                # 不确认：消费者中断或数据库暂时失败时由 XAUTOCLAIM 重新投递。
                logger.error(f'❌ GA/T1400 通知落库失败，保留待重试: {exc}')

    @classmethod
    async def _claim_pending(cls, redis: aioredis.Redis, consumer_name: str) -> None:
        start_id = '0-0'
        while True:
            result = await redis.xautoclaim(
                name=NOTIFY_STREAM_KEY,
                groupname=NOTIFY_STREAM_GROUP,
                consumername=consumer_name,
                min_idle_time=NOTIFY_CLAIM_IDLE_MS,
                start_id=start_id,
                count=NOTIFY_CLAIM_BATCH_SIZE,
            )
            if not result:
                return
            next_start_id, messages = result[0], result[1]
            if messages:
                await cls._process_messages(redis, messages)
            if not messages or next_start_id == start_id:
                return
            start_id = next_start_id

    @classmethod
    async def consume_loop(cls, redis: aioredis.Redis) -> None:
        """Stream 消费组：确认式消费，并自动认领宕机遗留的 pending 消息。"""
        await cls._ensure_group(redis)
        consumer_name = f'gat1400-{os.getpid()}-{uuid4().hex[:8]}'
        logger.info(f'🔁 GA/T1400 通知消费循环已启动（Stream {NOTIFY_STREAM_KEY}）')
        last_claim_time = 0.0
        while True:
            try:
                now = asyncio.get_running_loop().time()
                if now - last_claim_time >= NOTIFY_CLAIM_IDLE_MS / 1000:
                    await cls._claim_pending(redis, consumer_name)
                    last_claim_time = now
                result = await redis.xreadgroup(
                    groupname=NOTIFY_STREAM_GROUP,
                    consumername=consumer_name,
                    streams={NOTIFY_STREAM_KEY: '>'},
                    count=NOTIFY_CLAIM_BATCH_SIZE,
                    block=NOTIFY_STREAM_BLOCK_MS,
                )
                for _, messages in result or []:
                    await cls._process_messages(redis, messages)
            except asyncio.CancelledError:  # noqa: PERF203 - long-running worker must preserve cancellation
                raise
            except Exception as e:
                logger.error(f'❌ GA/T1400 通知消费循环异常: {e}，1秒后继续')
                await asyncio.sleep(1)

    @classmethod
    async def start(cls, redis: aioredis.Redis) -> None:
        """启动通知消费后台任务。"""
        if cls._consume_task and not cls._consume_task.done():
            return
        cls._consume_task = asyncio.create_task(cls.consume_loop(redis))

    @classmethod
    async def stop(cls) -> None:
        """停止通知消费后台任务。"""
        if cls._consume_task:
            cls._consume_task.cancel()
            try:
                await cls._consume_task
            except asyncio.CancelledError:
                pass
            cls._consume_task = None
