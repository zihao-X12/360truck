import unittest
from unittest.mock import ANY, AsyncMock, patch

from common.vo import PageModel
from exceptions.exception import ServiceException
from module_truck.dao.owner_dao import TruckOwnerDao
from module_truck.dao.vehicle_dao import TruckVehicleDao
from module_truck.entity.vo.vehicle_vo import TruckVehiclePageQueryModel
from module_truck.service.vehicle_service import TruckVehicleService


class _EmptyResult:
    """替身查询结果：模拟中队名称查询返回空集合。"""

    def all(self) -> list:
        return []


def _db_stub() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_EmptyResult())
    return db


class TruckVehicleListScopeTests(unittest.IsolatedAsyncioTestCase):
    """
    车辆列表在「按主体跨中队查看」与「默认中队隔离」两种路径下的权限行为。
    """

    async def test_owner_query_requires_owner_visibility(self) -> None:
        """按 ownerId 查询前必须校验主体可见性，不可借 ownerId 越权读取其他中队车辆。"""
        with (
            patch.object(TruckOwnerDao, 'get_by_id', new=AsyncMock(return_value=None)),
            patch.object(TruckVehicleDao, 'get_list', new=AsyncMock()) as vehicle_list,
            self.assertRaises(ServiceException) as raised,
        ):
            await TruckVehicleService.get_list(
                _db_stub(), TruckVehiclePageQueryModel(ownerId=10), AsyncMock(), True, AsyncMock()
            )

        self.assertIn('无权访问', raised.exception.message)
        vehicle_list.assert_not_awaited()

    async def test_owner_query_returns_all_squads(self) -> None:
        """主体可见时，按 ownerId 查询返回该主体名下全部车辆。"""
        page = PageModel(
            rows=[
                {'vehicleId': 26, 'plateNo': '浙K22233', 'deptId': 9101},
                {'vehicleId': 2, 'plateNo': '鄂AVL676', 'deptId': 9102},
            ],
            pageNum=1,
            pageSize=10,
            total=2,
            hasNext=False,
        )
        vehicle_scope = AsyncMock(name='vehicle_scope')
        owner_scope = AsyncMock(name='owner_scope')

        with (
            patch.object(TruckOwnerDao, 'get_by_id', new=AsyncMock(return_value=object())) as get_owner,
            patch.object(TruckVehicleDao, 'get_list', new=AsyncMock(return_value=page)),
        ):
            result = await TruckVehicleService.get_list(
                _db_stub(), TruckVehiclePageQueryModel(ownerId=6), vehicle_scope, True, owner_scope
            )

        # 主体可见性校验使用 (owner_scope, vehicle_scope) 组合，与主体列表口径一致
        get_owner.assert_awaited_once_with(ANY, 6, owner_scope, vehicle_scope)
        self.assertEqual([row['vehicleId'] for row in result.rows], [26, 2])

    async def test_default_query_keeps_squad_isolation(self) -> None:
        """不传 ownerId 时走原有路径，不做主体校验，人员范围完全由车辆 scope 决定。"""
        page = PageModel(rows=[{'vehicleId': 26, 'deptId': 9101}], pageNum=1, pageSize=10, total=1, hasNext=False)
        vehicle_scope = AsyncMock(name='vehicle_scope')

        with (
            patch.object(TruckOwnerDao, 'get_by_id', new=AsyncMock()) as get_owner,
            patch.object(TruckVehicleDao, 'get_list', new=AsyncMock(return_value=page)) as vehicle_list,
        ):
            result = await TruckVehicleService.get_list(
                _db_stub(), TruckVehiclePageQueryModel(), vehicle_scope, True, AsyncMock()
            )

        get_owner.assert_not_awaited()
        self.assertIs(vehicle_list.await_args.args[2], vehicle_scope)
        self.assertEqual(result.rows[0]['vehicleId'], 26)


if __name__ == '__main__':
    unittest.main()
