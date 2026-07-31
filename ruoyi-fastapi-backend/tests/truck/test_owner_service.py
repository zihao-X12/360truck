import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from exceptions.exception import ServiceException
from module_truck.dao.owner_dao import TruckOwnerDao
from module_truck.entity.vo.owner_vo import DeleteTruckOwnerModel, TruckOwnerModel
from module_truck.service.owner_service import TruckOwnerService


class TruckOwnerServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_identity_is_rejected(self) -> None:
        owner = TruckOwnerModel(ownerId=2, ownerType='enterprise', ownerName='测试企业', deptId=9101, creditCode='91330000TEST')
        existing = SimpleNamespace(owner_id=1)

        with (
            patch.object(TruckOwnerDao, 'get_by_identity', new=AsyncMock(return_value=existing)),
            self.assertRaises(ServiceException),
        ):
            await TruckOwnerService._check_unique(AsyncMock(), owner)

    async def test_owner_with_vehicles_cannot_be_deleted(self) -> None:
        db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
        owner = TruckOwnerModel(ownerId=1, ownerType='enterprise', ownerName='测试企业', deptId=9101)

        with (
            patch.object(TruckOwnerService, 'detail', new=AsyncMock(return_value=owner)),
            patch.object(TruckOwnerDao, 'count_vehicles', new=AsyncMock(return_value=1)),
            self.assertRaises(ServiceException) as raised,
        ):
            await TruckOwnerService.delete(
                db, DeleteTruckOwnerModel(ownerIds='1'), 'admin', datetime.now()
            )

        self.assertIn('仍有关联车辆', raised.exception.message)
        db.rollback.assert_awaited_once()
        db.commit.assert_not_awaited()

    async def test_unreferenced_owner_is_soft_deleted(self) -> None:
        db = SimpleNamespace(commit=AsyncMock(), rollback=AsyncMock())
        owner = TruckOwnerModel(ownerId=1, ownerType='individual', ownerName='测试车主', deptId=9101)

        with (
            patch.object(TruckOwnerService, 'detail', new=AsyncMock(return_value=owner)),
            patch.object(TruckOwnerDao, 'count_vehicles', new=AsyncMock(return_value=0)),
            patch.object(TruckOwnerDao, 'delete', new=AsyncMock()) as delete,
        ):
            result = await TruckOwnerService.delete(
                db, DeleteTruckOwnerModel(ownerIds='1'), 'admin', datetime.now()
            )

        self.assertTrue(result.is_success)
        delete.assert_awaited_once()
        db.commit.assert_awaited_once()


if __name__ == '__main__':
    unittest.main()
