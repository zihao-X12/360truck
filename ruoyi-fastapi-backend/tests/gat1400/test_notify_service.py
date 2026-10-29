import json
import unittest
from unittest.mock import AsyncMock, patch

from module_gat1400.service.gat1400_notify_service import (
    NOTIFY_STREAM_KEY,
    PARSE_NO_VEHICLE_DATA,
    PARSE_SUBSCRIBE_MISMATCH,
    PARSE_SUCCESS,
    Gat1400NotifyService,
    extract_motor_vehicles,
    map_vehicle_fields,
    parse_notification_list,
)

# 大华文档"订阅通知"示例结构：SubscribeNotificationListObject.SubscribeNotificationObject[]
VEHICLE_ARCHIVE_ID = 123
DAHUA_NOTIFICATION = {
    'SubscribeNotificationListObject': {
        'SubscribeNotificationObject': [
            {
                'NotificationID': '650100010000042017040112010100001',
                'SubscribeID': '650100010000032017040112010100001',
                'Title': '通知主题',
                'TriggerTime': '20171102101205',
                'InfoIDs': '650100000013200000010120170330120000000010100001',
                'MotorVehicleObjectList': {
                    'MotorVehicleObject': [
                        {
                            'MotorVehicleID': '330101010012100000010220171018080608022060269899',
                            'InfoKind': 1,
                            'DeviceID': '65010000001190000001',
                            'TollgateID': '2141245',
                            'LaneNo': 1,
                            'HasPlate': '1',
                            'PlateClass': '99',
                            'PlateColor': '99',
                            'PlateNo': '苏NF5676',
                            'Speed': 8,
                            'Direction': '0',
                            'VehicleClass': '1',
                            'VehicleColor': '1',
                            'PassTime': '20160912220107',
                            'NameOfPassedRoad': '中山路',
                            'StorageUrl1': '9527/upload/122/20130901/00/0524-NAS221-50151415-AS.jpg',
                            'PlateReliability': '90',
                            'SubImageList': {'SubImageInfoObject': [{'ImageID': 'IMG-001'}]},
                        }
                    ]
                },
            }
        ]
    }
}


class ParseNotificationListTests(unittest.IsolatedAsyncioTestCase):
    async def test_parse_dahua_wrapper(self) -> None:
        notifications = parse_notification_list(DAHUA_NOTIFICATION)

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['NotificationID'], '650100010000042017040112010100001')

    async def test_parse_standard_wrapper(self) -> None:
        body = json.loads(
            json.dumps(DAHUA_NOTIFICATION).replace('SubscribeNotificationListObject', 'SubscribeNotificationList')
        )
        notifications = parse_notification_list(body)

        self.assertEqual(len(notifications), 1)

    async def test_parse_wrapper_as_direct_list(self) -> None:
        body = {'SubscribeNotificationListObject': [{'NotificationID': 'N1'}]}

        self.assertEqual(parse_notification_list(body), [{'NotificationID': 'N1'}])

    async def test_parse_rejects_invalid(self) -> None:
        self.assertEqual(parse_notification_list(None), [])
        self.assertEqual(
            parse_notification_list({'SubscribeNotificationListObject': {'SubscribeNotificationObject': 'junk'}}), []
        )


class ExtractMotorVehicleTests(unittest.IsolatedAsyncioTestCase):
    async def test_extract_dahua_vehicle_list(self) -> None:
        vehicles = extract_motor_vehicles(
            DAHUA_NOTIFICATION['SubscribeNotificationListObject']['SubscribeNotificationObject'][0]
        )

        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0]['PlateNo'], '苏NF5676')

    async def test_extract_direct_list(self) -> None:
        notification = {'MotorVehicleObjectList': [{'MotorVehicleID': 'A'}, {'MotorVehicleID': 'B'}]}

        self.assertEqual(len(extract_motor_vehicles(notification)), 2)

    async def test_extract_missing(self) -> None:
        self.assertEqual(extract_motor_vehicles({'MotorVehicleObjectList': None}), [])
        self.assertEqual(extract_motor_vehicles({}), [])


class MapVehicleFieldsTests(unittest.IsolatedAsyncioTestCase):
    async def test_map_full_vehicle(self) -> None:
        item = {
            'MotorVehicleID': '330101010012100000010220171018080608022060269899',
            'InfoKind': 1,
            'DeviceID': 'D1',
            'TollgateID': 'T1',
            'PlateNo': '苏NF5676',
            'PlateColor': '99',
            'VehicleClass': '1',
            'PassTime': '20160912220107',
            'LaneNo': 1,
            'Speed': 8,
            'Direction': '0',
            'HasPlate': '1',
            'IsSuspicious': '0',
            'StorageUrl1': 'http://x/1.jpg',
            'PlateReliability': '90',
            'NameOfPassedRoad': '中山路',
        }
        fields = map_vehicle_fields(item)

        self.assertEqual(fields['motor_vehicle_id'], '330101010012100000010220171018080608022060269899')
        self.assertEqual(fields['plate_no'], '苏NF5676')
        self.assertEqual(fields['pass_time'].strftime('%Y%m%d%H%M%S'), '20160912220107')
        self.assertEqual(fields['lane_no'], 1)
        self.assertEqual(fields['speed'], 8)
        self.assertEqual(fields['has_plate'], '1')
        self.assertEqual(fields['raw_json'], item)

    async def test_map_vehicle_tolerates_bad_values(self) -> None:
        fields = map_vehicle_fields({'MotorVehicleID': 'X', 'PassTime': 'junk', 'LaneNo': 'abc', 'Speed': None})

        self.assertEqual(fields['pass_time'], None)
        self.assertEqual(fields['lane_no'], None)
        self.assertEqual(fields['speed'], None)


class FakeNotifyLog:
    """模拟通知日志记录：携带真实属性供断言。"""

    def __init__(self, parse_status: str, record_count: int) -> None:
        self.parse_status = parse_status
        self.record_count = record_count


class PersistNotificationTests(unittest.IsolatedAsyncioTestCase):
    def _patch_log_dao(self, parse_status: str, record_count: int) -> AsyncMock:
        dao_log = AsyncMock()
        dao_log.return_value = FakeNotifyLog(parse_status=parse_status, record_count=record_count)
        return dao_log

    async def test_persist_success_dedup_and_plate_match(self) -> None:
        db = AsyncMock()
        notification = DAHUA_NOTIFICATION['SubscribeNotificationListObject']['SubscribeNotificationObject'][0]
        vehicle_id = '330101010012100000010220171018080608022060269899'

        with (
            patch(
                'module_gat1400.service.gat1400_notify_service.Gat1400SubscribeDao.get_by_id',
                AsyncMock(return_value=True),
            ),
            patch(
                'module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.get_existing_ids',
                AsyncMock(return_value={vehicle_id}),
            ),
            patch(
                'module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.update_by_motor_vehicle_id',
                AsyncMock(),
            ) as dao_update,
            patch('module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.add', AsyncMock()) as dao_add,
            patch(
                'module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.get_vehicle_ids_by_plates',
                AsyncMock(return_value={'苏NF5676': [VEHICLE_ARCHIVE_ID]}),
            ),
            patch(
                'module_gat1400.service.gat1400_notify_service.Gat1400NotifyLogDao.add',
                self._patch_log_dao(PARSE_SUCCESS, 1),
            ),
        ):
            notify_log = await Gat1400NotifyService.persist_notification(db, notification)

        # 已有记录走更新，不重复新增（去重）
        dao_add.assert_not_awaited()
        self.assertEqual(dao_update.await_count, 2)  # 1次更新数据 + 1次回填 vehicle_id
        self.assertTrue(any(call.kwargs.get('vehicle_id') == VEHICLE_ARCHIVE_ID for call in dao_update.await_args_list))
        self.assertEqual(notify_log.parse_status, PARSE_SUCCESS)
        self.assertEqual(notify_log.record_count, 1)

    async def test_persist_subscribe_mismatch_flags_but_keeps_data(self) -> None:
        db = AsyncMock()
        notification = DAHUA_NOTIFICATION['SubscribeNotificationListObject']['SubscribeNotificationObject'][0]
        with (
            patch(
                'module_gat1400.service.gat1400_notify_service.Gat1400SubscribeDao.get_by_id',
                AsyncMock(return_value=False),
            ),
            patch(
                'module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.get_existing_ids',
                AsyncMock(return_value=set()),
            ),
            patch('module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.add', AsyncMock()),
            patch(
                'module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.update_by_motor_vehicle_id',
                AsyncMock(),
            ),
            patch(
                'module_gat1400.service.gat1400_notify_service.TruckPassRecordDao.get_vehicle_ids_by_plates',
                AsyncMock(return_value={}),
            ),
            patch(
                'module_gat1400.service.gat1400_notify_service.Gat1400NotifyLogDao.add',
                self._patch_log_dao(PARSE_SUBSCRIBE_MISMATCH, 1),
            ),
        ):
            notify_log = await Gat1400NotifyService.persist_notification(db, notification)

        self.assertEqual(notify_log.parse_status, PARSE_SUBSCRIBE_MISMATCH)
        self.assertEqual(notify_log.record_count, 1)  # 数据不丢弃

    async def test_persist_no_vehicle_data(self) -> None:
        db = AsyncMock()
        notification = {'NotificationID': 'N1', 'SubscribeID': 'S1', 'TriggerTime': '20171102101205'}
        with (
            patch(
                'module_gat1400.service.gat1400_notify_service.Gat1400SubscribeDao.get_by_id',
                AsyncMock(return_value=True),
            ),
            patch(
                'module_gat1400.service.gat1400_notify_service.Gat1400NotifyLogDao.add',
                self._patch_log_dao(PARSE_NO_VEHICLE_DATA, 0),
            ),
        ):
            notify_log = await Gat1400NotifyService.persist_notification(db, notification)

        self.assertEqual(notify_log.parse_status, PARSE_NO_VEHICLE_DATA)
        self.assertEqual(notify_log.record_count, 0)


class EnqueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_enqueue_writes_reliable_stream(self) -> None:
        redis = AsyncMock()

        await Gat1400NotifyService.enqueue_notify(redis, '{"a":1}')

        redis.xadd.assert_awaited_once_with(NOTIFY_STREAM_KEY, {'raw_body': '{"a":1}'})


if __name__ == '__main__':
    unittest.main()
