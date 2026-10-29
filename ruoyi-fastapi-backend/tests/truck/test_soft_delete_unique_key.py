"""验证软删除会释放唯一键占用的身份字段。

背景：`truck_owner.credit_code` / `id_card_no`、`truck_vehicle.(plate_no, plate_color)` /
`vin` 都是唯一索引且**不含 del_flag**。若软删时保留这些字段，重建同一主体或车辆会被
唯一约束拦下并报 Duplicate entry（M13 修复）。

这些用例直接构造 SQLAlchemy 语句并断言 UPDATE 的 SET 子句，
因此不依赖真实数据库即可锁定行为。
"""

import unittest
from datetime import datetime
from typing import Any

from sqlalchemy.dialects import mysql

from module_truck.dao.owner_dao import TruckOwnerDao
from module_truck.dao.vehicle_dao import TruckVehicleDao


class _CapturingSession:
    """捕获传入 execute 的语句，便于断言 SET 子句。"""

    def __init__(self) -> None:
        self.statements: list = []

    async def execute(self, statement: Any) -> None:
        self.statements.append(statement)


def _set_values(statement: Any) -> dict:
    """从 UPDATE 语句提取 SET 的列 -> 绑定值。"""
    compiled = statement.compile(dialect=mysql.dialect())
    return dict(compiled.params)


class SoftDeleteReleasesUniqueKeyTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_soft_delete_clears_identity_fields(self) -> None:
        """软删主体必须清空 credit_code 与 id_card_no，否则身份标识无法复用。"""
        db = _CapturingSession()
        await TruckOwnerDao.delete(db, 1, 'admin', datetime.now())

        self.assertEqual(len(db.statements), 1)
        values = _set_values(db.statements[0])
        cleared = {key for key, value in values.items() if value is None}
        self.assertIn('credit_code', cleared)
        self.assertIn('id_card_no', cleared)
        self.assertEqual(values.get('del_flag'), '2')

    async def test_vehicle_soft_delete_clears_plate_and_vin(self) -> None:
        """软删车辆必须清空 plate_no 与 vin，(plate_no, plate_color)/vin 才能复用。"""
        db = _CapturingSession()
        await TruckVehicleDao.soft_delete(db, 1, 'admin', datetime.now())

        self.assertEqual(len(db.statements), 1)
        values = _set_values(db.statements[0])
        cleared = {key for key, value in values.items() if value is None}
        self.assertIn('plate_no', cleared)
        self.assertIn('vin', cleared)
        self.assertEqual(values.get('del_flag'), '2')


if __name__ == '__main__':
    unittest.main()
