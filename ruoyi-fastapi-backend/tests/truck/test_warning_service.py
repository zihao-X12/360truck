import io
import unittest

from openpyxl import load_workbook

from module_truck.service.warning_service import TruckWarningService


class TruckWarningServiceTests(unittest.TestCase):
    def test_default_rule_requires_two_devices(self) -> None:
        required, level_one, level_two = TruckWarningService.parse_rule(None)

        self.assertEqual(required, ['brake_assist', 'panoramic_360'])
        self.assertEqual((level_one, level_two), (2, 1))

    def test_warning_level_follows_missing_device_count(self) -> None:
        self.assertEqual(TruckWarningService.calculate_level(2, 2, 1), 'level_one')
        self.assertEqual(TruckWarningService.calculate_level(1, 2, 1), 'level_two')
        self.assertEqual(TruckWarningService.calculate_level(0, 2, 1), 'none')

    def test_warning_export_contains_missing_device_names(self) -> None:
        content = TruckWarningService.export_warnings(
            [
                {
                    'plateNo': '浙K12345',
                    'warningLevel': 'level_one',
                    'missingDeviceTypes': ['brake_assist', 'panoramic_360'],
                }
            ]
        )
        worksheet = load_workbook(io.BytesIO(content), data_only=True).active

        self.assertEqual(worksheet.cell(2, 1).value, '浙K12345')
        self.assertEqual(worksheet.cell(2, 7).value, '一级预警')
        self.assertIn('刹车辅助系统', worksheet.cell(2, 8).value)


if __name__ == '__main__':
    unittest.main()
