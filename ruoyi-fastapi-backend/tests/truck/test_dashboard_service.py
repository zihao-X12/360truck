import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import true

from module_truck.dao.dashboard_dao import TruckDashboardDao
from module_truck.service.dashboard_service import TruckDashboardService


class TruckDashboardServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_merges_vehicle_and_owner_statistics(self) -> None:
        with (
            patch.object(
                TruckDashboardDao,
                'get_vehicle_summary',
                new=AsyncMock(
                    return_value={
                        'vehicle_total': 9,
                        'local_vehicle_count': 6,
                        'nonlocal_vehicle_count': 3,
                        'supervision_count': 2,
                        'level_one_count': 1,
                        'level_two_count': 1,
                    }
                ),
            ),
            patch.object(
                TruckDashboardDao,
                'get_owner_summary',
                new=AsyncMock(return_value={'owner_total': 5, 'enterprise_count': 3, 'individual_count': 2}),
            ),
        ):
            result = await TruckDashboardService.get_summary(AsyncMock(), true(), true())

        self.assertEqual(result.vehicle_total, 9)
        self.assertEqual(result.owner_total, 5)
        self.assertEqual(result.level_one_count, 1)

    async def test_dept_stats_include_empty_departments(self) -> None:
        with (
            patch.object(TruckDashboardDao, 'get_dept_vehicle_counts', new=AsyncMock(return_value=[(9101, 4)])),
            patch.object(TruckDashboardDao, 'get_dept_owner_counts', new=AsyncMock(return_value=[(9101, 2, 1)])),
            patch.object(
                TruckDashboardDao,
                'get_departments',
                new=AsyncMock(return_value=[(9101, '西屏中队'), (9102, '古市中队')]),
            ),
        ):
            result = await TruckDashboardService.get_dept_stats(AsyncMock(), true(), true())

        self.assertEqual(result[0].vehicle_count, 4)
        self.assertEqual(result[0].enterprise_count, 2)
        self.assertEqual(result[1].vehicle_count, 0)
        self.assertEqual(result[1].individual_count, 0)


if __name__ == '__main__':
    unittest.main()
