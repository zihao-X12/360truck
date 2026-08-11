import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from exceptions.exception import ServiceException
from module_truck.dao.owner_dao import TruckOwnerDao
from module_truck.entity.vo.vehicle_vo import TruckVehicleDeviceModel, TruckVehicleModel
from module_truck.service.vehicle_service import TruckVehicleService


class TruckVehicleRuleTests(unittest.IsolatedAsyncioTestCase):
    async def test_vehicle_can_link_owner_from_another_department(self) -> None:
        vehicle = TruckVehicleModel(
            plateNo='浙A12345', plateColor='yellow', deptId=9102, ownerId=1
        )
        owner = SimpleNamespace(owner_id=1, owner_type='individual', dept_id=9101)

        with patch.object(TruckOwnerDao, 'get_by_id', new=AsyncMock(return_value=owner)):
            await TruckVehicleService._resolve_owner(AsyncMock(), vehicle)

        self.assertEqual(vehicle.owner_type, 'individual')

    def test_plate_and_vin_are_normalized(self) -> None:
        vehicle = TruckVehicleModel(
            plateNo=' 浙a 12345 ', plateColor='yellow', deptId=9101, vin='1hgcm82633a004352'
        )

        self.assertEqual(vehicle.plate_no, '浙A12345')
        self.assertEqual(vehicle.vin, '1HGCM82633A004352')

    def test_vin_must_have_seventeen_characters(self) -> None:
        with self.assertRaises(ValidationError):
            TruckVehicleModel(plateNo='浙A12345', plateColor='yellow', deptId=9101, vin='SHORT')

    async def test_duplicate_device_type_is_rejected(self) -> None:
        vehicle = TruckVehicleModel(
            plateNo='浙A12345',
            plateColor='yellow',
            deptId=9101,
            devices=[TruckVehicleDeviceModel(deviceType='brake_assist'), TruckVehicleDeviceModel(deviceType='brake_assist')],
        )

        with self.assertRaises(ServiceException):
            await TruckVehicleService._validate_devices(vehicle)
