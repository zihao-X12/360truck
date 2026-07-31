import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.dialects import mysql

from common.aspect.data_scope import GetDataScope
from module_truck.entity.do.truck_do import TruckVehicle


class TruckDataScopeTests(unittest.TestCase):
    def test_squad_role_limits_vehicle_query_to_own_department(self) -> None:
        current_user = SimpleNamespace(
            user=SimpleNamespace(
                user_id=9101,
                dept_id=9101,
                admin=False,
                role=[SimpleNamespace(role_id=9010, data_scope=GetDataScope.DATA_SCOPE_DEPT)],
            )
        )

        with (
            patch('common.aspect.data_scope.DependencyUtil.check_exclude_routes'),
            patch('common.aspect.data_scope.RequestContext.get_current_user', return_value=current_user),
        ):
            expression = GetDataScope(TruckVehicle)(SimpleNamespace())

        sql = str(expression.compile(dialect=mysql.dialect(), compile_kwargs={'literal_binds': True}))
        self.assertIn('truck_vehicle.dept_id = 9101', sql)

    def test_admin_has_unrestricted_vehicle_scope(self) -> None:
        current_user = SimpleNamespace(
            user=SimpleNamespace(
                user_id=1,
                dept_id=103,
                admin=True,
                role=[SimpleNamespace(role_id=1, data_scope=GetDataScope.DATA_SCOPE_ALL)],
            )
        )

        with (
            patch('common.aspect.data_scope.DependencyUtil.check_exclude_routes'),
            patch('common.aspect.data_scope.RequestContext.get_current_user', return_value=current_user),
        ):
            expression = GetDataScope(TruckVehicle)(SimpleNamespace())

        self.assertEqual(str(expression).lower(), 'true')


if __name__ == '__main__':
    unittest.main()
