import io
import unittest

from openpyxl import Workbook, load_workbook

from module_truck.service.vehicle_import_service import TruckVehicleImportService


class TruckVehicleImportTests(unittest.TestCase):
    @staticmethod
    def _workbook_bytes(rows: list[list]) -> bytes:
        workbook = Workbook()
        worksheet = workbook.active
        for row in rows:
            worksheet.append(row)
        output = io.BytesIO()
        workbook.save(output)
        return output.getvalue()

    def test_legacy_headers_distinguish_two_phone_columns(self) -> None:
        content = self._workbook_bytes([
            TruckVehicleImportService.LEGACY_HEADERS,
            ['工地A', ' 浙a 12345 ', '自卸货车', None, None, '张三', '13800000000', '李四', '13900000000', '无', None, '是', '否', '西屏中队', '是'],
        ])

        headers, rows = TruckVehicleImportService.parse_workbook(content)

        self.assertEqual(headers, TruckVehicleImportService.LEGACY_HEADERS)
        self.assertEqual(rows[0]['values']['owner_phone'], '13800000000')
        self.assertEqual(rows[0]['values']['driver_phone'], '13900000000')

    def test_build_vehicle_maps_defaults_and_devices(self) -> None:
        values = {
            'plate_no': ' 浙a 12345 ',
            'vehicle_type': '自卸货车',
            'dept_name': '西屏中队',
            'source_type': '是',
            'brake_assist': '是',
            'panoramic_360': '否',
        }

        vehicle = TruckVehicleImportService.build_vehicle(
            values,
            {'西屏中队': 9101},
            {'自卸货车': 'dump_truck'},
            {'黄牌': 'yellow', 'yellow': 'yellow'},
            'admin',
        )

        self.assertEqual(vehicle.plate_no, '浙A12345')
        self.assertEqual(vehicle.plate_color, 'yellow')
        self.assertEqual(vehicle.source_type, 'local')
        self.assertEqual([device.device_type for device in vehicle.devices], ['brake_assist'])

    def test_invalid_source_type_has_real_value_in_message(self) -> None:
        with self.assertRaisesRegex(ValueError, '未知'):
            TruckVehicleImportService.build_vehicle(
                {'plate_no': '浙A12345', 'dept_name': '西屏中队', 'source_type': '未知'},
                {'西屏中队': 9101},
                {},
                {'yellow': 'yellow'},
                'admin',
            )

    def test_error_workbook_contains_row_and_message(self) -> None:
        row = {'sheet': 'Sheet1', 'row_number': 2, 'raw': ['工地A', None]}
        content = TruckVehicleImportService.build_error_workbook(['工地名称', '车牌'], [(row, '车牌不能为空')])
        worksheet = load_workbook(io.BytesIO(content), data_only=True).active

        self.assertEqual(worksheet.cell(2, 1).value, 'Sheet1')
        self.assertEqual(worksheet.cell(2, 2).value, 2)
        self.assertEqual(worksheet.cell(2, 5).value, '车牌不能为空')

    def test_empty_export_keeps_business_headers(self) -> None:
        content = TruckVehicleImportService.export_vehicles([])
        worksheet = load_workbook(io.BytesIO(content), data_only=True).active
        headers = [cell.value for cell in worksheet[1]]

        self.assertIn('辖区中队', headers)
        self.assertIn('是否安装刹辅系统', headers)


if __name__ == '__main__':
    unittest.main()
