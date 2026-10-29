-- M4 业务看板与重点监管预警增量脚本（PostgreSQL）
BEGIN;

INSERT INTO truck_warning_rule (
  rule_id, rule_name, required_device_types, level_one_threshold, level_two_threshold,
  status, create_by, create_time, remark
) VALUES (
  1, '安全设备缺装预警', '["brake_assist","panoramic_360"]', 2, 2,
  '0', 'admin', NOW(), '刹车辅助系统和360全景影像为应安装设备'
)
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO sys_menu (
  menu_id, menu_name, parent_id, order_num, path, component, query, route_name,
  is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark
) VALUES
  (9004, '重点监管预警', 9000, 4, 'warning', 'truck/warning/index', '', 'TruckWarning', 1, 0, 'C', '0', '0', 'truck:warning:query', 'warning', 'admin', NOW(), '缺装安全设备车辆预警'),
  (9040, '看板查询', 9000, 30, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:dashboard:list', '#', 'admin', NOW(), '业务看板查询权限'),
  (9041, '预警查询', 9004, 31, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:query', '#', 'admin', NOW(), '重点监管预警查询权限'),
  (9042, '预警重算', 9004, 32, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:recalculate', '#', 'admin', NOW(), '重点监管预警重算权限'),
  (9043, '预警导出', 9004, 33, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:export', '#', 'admin', NOW(), '重点监管预警导出权限')
ON CONFLICT (menu_id) DO NOTHING;

INSERT INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9004), (9010, 9040), (9010, 9041), (9010, 9042), (9010, 9043),
  (9011, 9004), (9011, 9040), (9011, 9041), (9011, 9043)
ON CONFLICT (role_id, menu_id) DO NOTHING;

SELECT setval(pg_get_serial_sequence('truck_warning_rule', 'rule_id'), GREATEST((SELECT MAX(rule_id) FROM truck_warning_rule), 1), true);

COMMIT;
