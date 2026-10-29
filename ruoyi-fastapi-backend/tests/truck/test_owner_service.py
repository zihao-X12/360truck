import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from common.vo import PageModel
from exceptions.exception import ServiceException
from module_truck.dao.owner_dao import TruckOwnerDao
from module_truck.entity.vo.owner_vo import DeleteTruckOwnerModel, TruckOwnerModel
from module_truck.service.owner_service import TruckOwnerService


class TruckOwnerServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_list_includes_vehicle_counts(self) -> None:
        page = PageModel(rows=[{'ownerId': 1}, {'ownerId': 2}], pageNum=1, pageSize=10, total=2, hasNext=False)

        with (
            patch.object(TruckOwnerDao, 'get_list', new=AsyncMock(return_value=page)),
            patch.object(
                TruckOwnerDao, 'count_vehicles_by_owner_ids', new=AsyncMock(return_value={1: 3})
            ) as count_vehicles,
        ):
            result = await TruckOwnerService.get_list(
                AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), True
            )

        self.assertEqual(result.rows, [{'ownerId': 1, 'vehicleCount': 3}, {'ownerId': 2, 'vehicleCount': 0}])
        # 「名下车辆」为跨中队全部车辆，计数不得再按车辆数据权限收窄
        count_vehicles.assert_awaited_once_with(unittest.mock.ANY, [1, 2])

    async def test_owner_vehicle_count_covers_all_squads(self) -> None:
        """
        挂靠主体名下车辆可跨中队分管，「名下车辆」必须给出全部数量。

        该用例锁定回归：计数不传 vehicle_scope，避免中队管理员只看到本中队分管的
        部分车辆而误判主体车辆总数。
        """
        page = PageModel(rows=[{'ownerId': 6}], pageNum=1, pageSize=10, total=1, hasNext=False)
        counted_scopes: list[object] = []

        async def fake_count(_db: object, owner_ids: list[int], vehicle_scope: object = None) -> dict[int, int]:
            counted_scopes.append(vehicle_scope)
            return {6: 4}

        with (
            patch.object(TruckOwnerDao, 'get_list', new=AsyncMock(return_value=page)),
            patch.object(TruckOwnerDao, 'count_vehicles_by_owner_ids', new=fake_count),
        ):
            result = await TruckOwnerService.get_list(AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock(), True)

        # 主体登记在西屏(9102)、4 辆车分布在 9102 与 9101，计数应为 4 而非本中队可见的 3
        self.assertEqual(result.rows, [{'ownerId': 6, 'vehicleCount': 4}])
        self.assertEqual(counted_scopes, [None])

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
