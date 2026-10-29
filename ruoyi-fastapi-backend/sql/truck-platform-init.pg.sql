-- 县域大货车基础信息管理平台初始化脚本（PostgreSQL）
-- 可在已初始化 RuoYi-FastAPI PostgreSQL 数据库上重复执行。

CREATE TABLE IF NOT EXISTS truck_owner (
  owner_id BIGSERIAL PRIMARY KEY,
  owner_type VARCHAR(20) NOT NULL,
  owner_name VARCHAR(100) NOT NULL,
  credit_code VARCHAR(32) UNIQUE,
  id_card_no VARCHAR(32) UNIQUE,
  dept_id BIGINT NOT NULL,
  contact_name VARCHAR(50), contact_phone VARCHAR(30), address VARCHAR(255),
  status CHAR(1) NOT NULL DEFAULT '0', remark VARCHAR(500),
  create_by VARCHAR(64) DEFAULT '', create_time TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
  update_by VARCHAR(64) DEFAULT '', update_time TIMESTAMP(0), del_flag CHAR(1) NOT NULL DEFAULT '0'
);
CREATE INDEX IF NOT EXISTS idx_truck_owner_dept_id ON truck_owner(dept_id);
CREATE INDEX IF NOT EXISTS idx_truck_owner_name ON truck_owner(owner_name);

CREATE TABLE IF NOT EXISTS truck_vehicle (
  vehicle_id BIGSERIAL PRIMARY KEY,
  project_name VARCHAR(100), plate_no VARCHAR(20), plate_color VARCHAR(20) NOT NULL,
  vehicle_type VARCHAR(30), vehicle_brand VARCHAR(100), vin VARCHAR(32) UNIQUE, rated_load NUMERIC(10,2),
  source_type VARCHAR(20), motor_owner_name VARCHAR(100), driver_name VARCHAR(50), driver_phone VARCHAR(30),
  affiliated_company VARCHAR(100), insurance_status VARCHAR(100), insurance_info VARCHAR(255),
  owner_id BIGINT, owner_type VARCHAR(20), dept_id BIGINT NOT NULL, photo_file_id VARCHAR(36),
  vehicle_status VARCHAR(20) NOT NULL DEFAULT 'normal', supervision_flag CHAR(1) NOT NULL DEFAULT '0',
  warning_level VARCHAR(20), missing_device_count INTEGER NOT NULL DEFAULT 0, remark VARCHAR(500),
  create_by VARCHAR(64) DEFAULT '', create_time TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
  update_by VARCHAR(64) DEFAULT '', update_time TIMESTAMP(0), del_flag CHAR(1) NOT NULL DEFAULT '0',
  CONSTRAINT uk_truck_vehicle_plate UNIQUE (plate_no, plate_color)
);
CREATE INDEX IF NOT EXISTS idx_truck_vehicle_dept_id ON truck_vehicle(dept_id);
CREATE INDEX IF NOT EXISTS idx_truck_vehicle_owner_id ON truck_vehicle(owner_id);
CREATE INDEX IF NOT EXISTS idx_truck_vehicle_status ON truck_vehicle(vehicle_status);
CREATE INDEX IF NOT EXISTS idx_truck_vehicle_warning ON truck_vehicle(warning_level);

CREATE TABLE IF NOT EXISTS truck_vehicle_device (
  device_id BIGSERIAL PRIMARY KEY, vehicle_id BIGINT NOT NULL, device_type VARCHAR(30) NOT NULL,
  product_name VARCHAR(100), brand VARCHAR(100), install_date DATE, status CHAR(1) NOT NULL DEFAULT '0', remark VARCHAR(500),
  create_by VARCHAR(64) DEFAULT '', create_time TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
  update_by VARCHAR(64) DEFAULT '', update_time TIMESTAMP(0),
  CONSTRAINT uk_truck_vehicle_device UNIQUE (vehicle_id, device_type)
);
CREATE INDEX IF NOT EXISTS idx_truck_vehicle_device_vehicle_id ON truck_vehicle_device(vehicle_id);

CREATE TABLE IF NOT EXISTS truck_vehicle_owner_history (
  history_id BIGSERIAL PRIMARY KEY, vehicle_id BIGINT NOT NULL, old_owner_id BIGINT, new_owner_id BIGINT,
  old_dept_id BIGINT, new_dept_id BIGINT, change_reason VARCHAR(255),
  change_time TIMESTAMP(0) NOT NULL DEFAULT CURRENT_TIMESTAMP, change_by VARCHAR(64) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_truck_owner_history_vehicle_id ON truck_vehicle_owner_history(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_truck_owner_history_change_time ON truck_vehicle_owner_history(change_time);

CREATE TABLE IF NOT EXISTS truck_warning_rule (
  rule_id BIGSERIAL PRIMARY KEY, rule_name VARCHAR(100) NOT NULL UNIQUE, required_device_types TEXT,
  level_one_threshold INTEGER NOT NULL DEFAULT 2, level_two_threshold INTEGER NOT NULL DEFAULT 2,
  status CHAR(1) NOT NULL DEFAULT '0', create_by VARCHAR(64) DEFAULT '', create_time TIMESTAMP(0) DEFAULT CURRENT_TIMESTAMP,
  update_by VARCHAR(64) DEFAULT '', update_time TIMESTAMP(0), remark VARCHAR(500)
);

-- 松阳大队及辖区中队。固定ID用于初始化数据权限和测试数据关联。
INSERT INTO sys_dept (dept_id, parent_id, ancestors, dept_name, order_num, status, del_flag, create_by, create_time) VALUES
  (9100, 0, '0', '松阳大队', 1, '0', '0', 'admin', CURRENT_TIMESTAMP),
  (9101, 9100, '0,9100', '西屏中队', 1, '0', '0', 'admin', CURRENT_TIMESTAMP),
  (9102, 9100, '0,9100', '古市中队', 2, '0', '0', 'admin', CURRENT_TIMESTAMP),
  (9103, 9100, '0,9100', '江南中队', 3, '0', '0', 'admin', CURRENT_TIMESTAMP),
  (9104, 9100, '0,9100', '象溪中队', 4, '0', '0', 'admin', CURRENT_TIMESTAMP),
  (9105, 9100, '0,9100', '大东坝中队', 5, '0', '0', 'admin', CURRENT_TIMESTAMP),
  (9106, 9100, '0,9100', '玉岩中队', 6, '0', '0', 'admin', CURRENT_TIMESTAMP)
ON CONFLICT (dept_id) DO UPDATE SET parent_id = EXCLUDED.parent_id, ancestors = EXCLUDED.ancestors, dept_name = EXCLUDED.dept_name, order_num = EXCLUDED.order_num, status = EXCLUDED.status, del_flag = EXCLUDED.del_flag;
-- 注：PostgreSQL 模板的 sys_dept 没有 remark 列（MySQL 模板有），故此处不能写 remark。

INSERT INTO sys_dict_type (dict_id, dict_name, dict_type, status, create_by, create_time, remark) VALUES
  (9001, '车辆类型', 'truck_vehicle_type', '0', 'admin', CURRENT_TIMESTAMP, '大货车管理车辆类型'),
  (9002, '车牌颜色', 'truck_plate_color', '0', 'admin', CURRENT_TIMESTAMP, '大货车管理车牌颜色'),
  (9003, '车辆状态', 'truck_vehicle_status', '0', 'admin', CURRENT_TIMESTAMP, '大货车管理车辆状态'),
  (9004, '来源标识', 'truck_source_type', '0', 'admin', CURRENT_TIMESTAMP, '大货车管理来源标识'),
  (9005, '归属主体类型', 'truck_owner_type', '0', 'admin', CURRENT_TIMESTAMP, '大货车管理归属主体类型'),
  (9006, '安全设备类型', 'truck_device_type', '0', 'admin', CURRENT_TIMESTAMP, '大货车管理安全设备类型'),
  (9007, '预警等级', 'truck_warning_level', '0', 'admin', CURRENT_TIMESTAMP, '大货车管理预警等级')
ON CONFLICT (dict_id) DO UPDATE SET dict_name = EXCLUDED.dict_name, dict_type = EXCLUDED.dict_type, status = EXCLUDED.status, remark = EXCLUDED.remark;

INSERT INTO sys_dict_data (dict_code, dict_sort, dict_label, dict_value, dict_type, css_class, list_class, is_default, status, create_by, create_time, remark) VALUES
  (9001,1,'自卸货车','dump_truck','truck_vehicle_type','','warning','Y','0','admin',CURRENT_TIMESTAMP,'车辆类型'),(9002,2,'混凝土搅拌车','mixer_truck','truck_vehicle_type','','primary','N','0','admin',CURRENT_TIMESTAMP,'车辆类型'),(9003,3,'牵引车','tractor','truck_vehicle_type','','success','N','0','admin',CURRENT_TIMESTAMP,'车辆类型'),(9004,4,'载货汽车','cargo_truck','truck_vehicle_type','','info','N','0','admin',CURRENT_TIMESTAMP,'车辆类型'),(9005,99,'其他','other','truck_vehicle_type','','info','N','0','admin',CURRENT_TIMESTAMP,'车辆类型'),
  (9011,1,'黄牌','yellow','truck_plate_color','','warning','Y','0','admin',CURRENT_TIMESTAMP,'车牌颜色'),(9012,2,'蓝牌','blue','truck_plate_color','','primary','N','0','admin',CURRENT_TIMESTAMP,'车牌颜色'),(9013,3,'绿牌','green','truck_plate_color','','success','N','0','admin',CURRENT_TIMESTAMP,'车牌颜色'),(9014,4,'其他','other','truck_plate_color','','info','N','0','admin',CURRENT_TIMESTAMP,'车牌颜色'),
  (9021,1,'正常','normal','truck_vehicle_status','','success','Y','0','admin',CURRENT_TIMESTAMP,'车辆状态'),(9022,2,'停运','stopped','truck_vehicle_status','','warning','N','0','admin',CURRENT_TIMESTAMP,'车辆状态'),(9023,3,'转出','transferred','truck_vehicle_status','','info','N','0','admin',CURRENT_TIMESTAMP,'车辆状态'),(9024,4,'报废','scrapped','truck_vehicle_status','','danger','N','0','admin',CURRENT_TIMESTAMP,'车辆状态'),
  (9031,1,'本地车辆','local','truck_source_type','','success','Y','0','admin',CURRENT_TIMESTAMP,'来源标识'),(9032,2,'外地车辆','nonlocal','truck_source_type','','warning','N','0','admin',CURRENT_TIMESTAMP,'来源标识'),
  (9041,1,'运输企业','enterprise','truck_owner_type','','primary','Y','0','admin',CURRENT_TIMESTAMP,'归属主体类型'),(9042,2,'个人车主','individual','truck_owner_type','','info','N','0','admin',CURRENT_TIMESTAMP,'归属主体类型'),
  (9051,1,'刹车辅助系统','brake_assist','truck_device_type','','danger','Y','0','admin',CURRENT_TIMESTAMP,'安全设备类型'),(9052,2,'360全景影像','panoramic_360','truck_device_type','','primary','N','0','admin',CURRENT_TIMESTAMP,'安全设备类型'),
  (9061,1,'一级预警','level_one','truck_warning_level','','danger','N','0','admin',CURRENT_TIMESTAMP,'预警等级'),(9062,2,'二级预警','level_two','truck_warning_level','','warning','N','0','admin',CURRENT_TIMESTAMP,'预警等级'),(9063,3,'无预警','none','truck_warning_level','','success','Y','0','admin',CURRENT_TIMESTAMP,'预警等级')
ON CONFLICT (dict_code) DO UPDATE SET dict_sort = EXCLUDED.dict_sort, dict_label = EXCLUDED.dict_label, dict_value = EXCLUDED.dict_value, dict_type = EXCLUDED.dict_type, list_class = EXCLUDED.list_class, is_default = EXCLUDED.is_default, status = EXCLUDED.status, remark = EXCLUDED.remark;

INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, query, route_name, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark) VALUES
  (9000, '大货车管理', 0, 1, 'truck', NULL, '', 'Truck', 1, 0, 'M', '0', '0', '', 'dashboard', 'admin', CURRENT_TIMESTAMP, '大货车管理目录'),
  (9002, '主体管理', 9000, 2, 'owner', 'truck/owner/index', '', 'TruckOwner', 1, 0, 'C', '0', '0', 'truck:owner:query', 'peoples', 'admin', CURRENT_TIMESTAMP, '大货车归属主体管理'),
  (9003, '车辆档案', 9000, 3, 'vehicle', 'truck/vehicle/index', '', 'TruckVehicle', 1, 0, 'C', '0', '0', 'truck:vehicle:query', 'tree-table', 'admin', CURRENT_TIMESTAMP, '大货车车辆档案管理')
ON CONFLICT (menu_id) DO UPDATE SET menu_name = EXCLUDED.menu_name, parent_id = EXCLUDED.parent_id, order_num = EXCLUDED.order_num, path = EXCLUDED.path, component = EXCLUDED.component, route_name = EXCLUDED.route_name, status = EXCLUDED.status, perms = EXCLUDED.perms, icon = EXCLUDED.icon, remark = EXCLUDED.remark;

INSERT INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, query, route_name, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark) VALUES
  (9020, '主体查询', 9000, 10, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:query', '#', 'admin', CURRENT_TIMESTAMP, '归属主体查询权限'),
  (9021, '主体新增', 9000, 11, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:add', '#', 'admin', CURRENT_TIMESTAMP, '归属主体新增权限'),
  (9022, '主体修改', 9000, 12, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:edit', '#', 'admin', CURRENT_TIMESTAMP, '归属主体修改权限'),
  (9023, '主体删除', 9000, 13, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:remove', '#', 'admin', CURRENT_TIMESTAMP, '归属主体删除权限'),
  (9030, '车辆查询', 9000, 20, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:query', '#', 'admin', CURRENT_TIMESTAMP, '车辆查询权限'),
  (9031, '车辆新增', 9000, 21, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:add', '#', 'admin', CURRENT_TIMESTAMP, '车辆新增权限'),
  (9032, '车辆修改', 9000, 22, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:edit', '#', 'admin', CURRENT_TIMESTAMP, '车辆修改权限'),
  (9033, '车辆删除', 9000, 23, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:remove', '#', 'admin', CURRENT_TIMESTAMP, '车辆删除权限'),
  (9034, '车辆导入', 9000, 24, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:import', '#', 'admin', CURRENT_TIMESTAMP, '车辆导入权限'),
  (9035, '车辆导出', 9000, 25, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:export', '#', 'admin', CURRENT_TIMESTAMP, '车辆导出权限')
ON CONFLICT (menu_id) DO UPDATE SET menu_name = EXCLUDED.menu_name, parent_id = EXCLUDED.parent_id, order_num = EXCLUDED.order_num, perms = EXCLUDED.perms, remark = EXCLUDED.remark;

INSERT INTO sys_role (role_id, role_name, role_key, role_sort, data_scope, menu_check_strictly, dept_check_strictly, status, del_flag, create_by, create_time, remark) VALUES
  (9010, '中队管理员', 'truck_squad_admin', 10, '3', 1, 1, '0', '0', 'admin', CURRENT_TIMESTAMP, '仅管理本人所属中队的大货车数据'),
  (9011, '领导权限', 'truck_leader', 11, '1', 1, 1, '0', '0', 'admin', CURRENT_TIMESTAMP, '大货车数据只读权限')
ON CONFLICT (role_id) DO UPDATE SET role_name = EXCLUDED.role_name, role_key = EXCLUDED.role_key, role_sort = EXCLUDED.role_sort, data_scope = EXCLUDED.data_scope, status = EXCLUDED.status, remark = EXCLUDED.remark;

INSERT INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9000), (9010, 9002), (9010, 9003), (9010, 9020), (9010, 9021), (9010, 9022), (9010, 9023), (9010, 9030), (9010, 9031), (9010, 9032), (9010, 9033), (9010, 9034), (9010, 9035),
  (9011, 9000), (9011, 9002), (9011, 9003), (9011, 9020), (9011, 9030), (9011, 9035)
ON CONFLICT (role_id, menu_id) DO NOTHING;

UPDATE sys_menu SET parent_id = 9002 WHERE menu_id IN (9020, 9021, 9022, 9023);
UPDATE sys_menu SET parent_id = 9003 WHERE menu_id IN (9030, 9031, 9032, 9033, 9034, 9035);

-- 首页承载业务看板，精简系统菜单并调整顶层顺序。
DELETE FROM sys_role_menu WHERE menu_id IN (
  2, 99, 104, 107, 108, 109, 110, 111, 112, 113, 114, 120, 500, 501,
  1020, 1021, 1022, 1023, 1024, 1035, 1036, 1037, 1038, 1039, 1040, 1041,
  1042, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054,
  9001
);
DELETE FROM sys_menu WHERE menu_id IN (
  2, 99, 104, 107, 108, 109, 110, 111, 112, 113, 114, 120, 500, 501,
  1020, 1021, 1022, 1023, 1024, 1035, 1036, 1037, 1038, 1039, 1040, 1041,
  1042, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054,
  9001
);
UPDATE sys_menu SET order_num = 1 WHERE menu_id = 9000;
UPDATE sys_menu SET order_num = 2 WHERE menu_id = 4;
UPDATE sys_menu SET order_num = 3 WHERE menu_id = 3;
UPDATE sys_menu SET order_num = 4 WHERE menu_id = 1;
UPDATE sys_menu SET order_num = 5 WHERE menu_id = 105;
UPDATE sys_menu SET order_num = 6 WHERE menu_id = 106;
UPDATE sys_menu SET order_num = 7 WHERE menu_id = 121;

-- 默认预警规则：应安装设备共 2 项，缺装 2 项（一项都没装）为一级预警。
-- 二级阈值与一级相同，表示当前只保留一级预警，缺 1 项不预警。
INSERT INTO truck_warning_rule (
  rule_id, rule_name, required_device_types, level_one_threshold, level_two_threshold,
  status, create_by, create_time, remark
) VALUES (
  1, '安全设备缺装预警', '["brake_assist","panoramic_360"]', 2, 2,
  '0', 'admin', CURRENT_TIMESTAMP, '刹车辅助系统和360全景影像为应安装设备'
) ON CONFLICT DO NOTHING;

INSERT INTO sys_menu (
  menu_id, menu_name, parent_id, order_num, path, component, query, route_name,
  is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark
) VALUES
  (9004, '重点监管预警', 9000, 4, 'warning', 'truck/warning/index', '', 'TruckWarning', 1, 0, 'C', '0', '0', 'truck:warning:query', 'warning', 'admin', CURRENT_TIMESTAMP, '缺装安全设备车辆预警'),
  (9040, '看板查询', 9000, 30, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:dashboard:list', '#', 'admin', CURRENT_TIMESTAMP, '业务看板查询权限'),
  (9041, '预警查询', 9004, 31, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:query', '#', 'admin', CURRENT_TIMESTAMP, '重点监管预警查询权限'),
  (9042, '预警重算', 9004, 32, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:recalculate', '#', 'admin', CURRENT_TIMESTAMP, '重点监管预警重算权限'),
  (9043, '预警导出', 9004, 33, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:export', '#', 'admin', CURRENT_TIMESTAMP, '重点监管预警导出权限')
ON CONFLICT DO NOTHING;

INSERT INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9004), (9010, 9040), (9010, 9041), (9010, 9042), (9010, 9043),
  (9011, 9004), (9011, 9040), (9011, 9041), (9011, 9043)
ON CONFLICT DO NOTHING;

-- 验收账号初始密码均为 admin123，非开发环境部署后必须立即修改。
INSERT INTO sys_user (
  user_id, dept_id, user_name, nick_name, user_type, email, phonenumber, sex, avatar,
  password, status, del_flag, create_by, create_time, remark
) VALUES
  (9101, 9101, 'xiping_admin', '西屏中队管理员', '00', '', '', '0', '', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', CURRENT_TIMESTAMP, '大货车平台验收账号'),
  (9102, 9100, 'truck_leader', '大队领导', '00', '', '', '0', '', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', CURRENT_TIMESTAMP, '大货车平台验收账号')
ON CONFLICT DO NOTHING;

INSERT INTO sys_user_role (user_id, role_id) VALUES (9101, 9010), (9102, 9011)
ON CONFLICT DO NOTHING;

SELECT setval(pg_get_serial_sequence('sys_dict_type', 'dict_id'), GREATEST((SELECT MAX(dict_id) FROM sys_dict_type), 1), true);
SELECT setval(pg_get_serial_sequence('sys_dict_data', 'dict_code'), GREATEST((SELECT MAX(dict_code) FROM sys_dict_data), 1), true);
SELECT setval(pg_get_serial_sequence('sys_menu', 'menu_id'), GREATEST((SELECT MAX(menu_id) FROM sys_menu), 1), true);
SELECT setval(pg_get_serial_sequence('sys_role', 'role_id'), GREATEST((SELECT MAX(role_id) FROM sys_role), 1), true);
SELECT setval(pg_get_serial_sequence('sys_dept', 'dept_id'), GREATEST((SELECT MAX(dept_id) FROM sys_dept), 1), true);
SELECT setval(pg_get_serial_sequence('sys_user', 'user_id'), GREATEST((SELECT MAX(user_id) FROM sys_user), 1), true);
