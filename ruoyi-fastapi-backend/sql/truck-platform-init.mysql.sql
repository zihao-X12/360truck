-- 县域大货车基础信息管理平台初始化脚本（MySQL 8）
-- 可在已初始化 RuoYi-FastAPI 数据库上重复执行。

CREATE TABLE IF NOT EXISTS truck_owner (
  owner_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主体ID',
  owner_type VARCHAR(20) NOT NULL COMMENT '主体类型（enterprise/individual）',
  owner_name VARCHAR(100) NOT NULL COMMENT '企业名称或个人姓名',
  credit_code VARCHAR(32) DEFAULT NULL COMMENT '统一社会信用代码',
  id_card_no VARCHAR(32) DEFAULT NULL COMMENT '身份证号',
  dept_id BIGINT NOT NULL COMMENT '所属中队部门ID',
  contact_name VARCHAR(50) DEFAULT NULL COMMENT '联系人',
  contact_phone VARCHAR(30) DEFAULT NULL COMMENT '联系电话',
  address VARCHAR(255) DEFAULT NULL COMMENT '地址',
  status CHAR(1) NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  remark VARCHAR(500) DEFAULT NULL COMMENT '备注',
  create_by VARCHAR(64) DEFAULT '' COMMENT '创建者',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_by VARCHAR(64) DEFAULT '' COMMENT '更新者',
  update_time DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  del_flag CHAR(1) NOT NULL DEFAULT '0' COMMENT '删除标志（0存在 2删除）',
  PRIMARY KEY (owner_id),
  UNIQUE KEY uk_truck_owner_credit_code (credit_code),
  UNIQUE KEY uk_truck_owner_id_card_no (id_card_no),
  KEY idx_truck_owner_dept_id (dept_id),
  KEY idx_truck_owner_name (owner_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大货车归属主体表';

CREATE TABLE IF NOT EXISTS truck_vehicle (
  vehicle_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '车辆ID',
  project_name VARCHAR(100) DEFAULT NULL COMMENT '工地名称',
  plate_no VARCHAR(20) DEFAULT NULL COMMENT '车牌号（软删后置空以释放唯一键）',
  plate_color VARCHAR(20) NOT NULL COMMENT '车牌颜色',
  vehicle_type VARCHAR(30) DEFAULT NULL COMMENT '车辆类型',
  vehicle_brand VARCHAR(100) DEFAULT NULL COMMENT '车辆品牌',
  vin VARCHAR(32) DEFAULT NULL COMMENT '车架号',
  rated_load DECIMAL(10,2) DEFAULT NULL COMMENT '核定载重',
  source_type VARCHAR(20) DEFAULT NULL COMMENT '来源标识（local/nonlocal）',
  motor_owner_name VARCHAR(100) DEFAULT NULL COMMENT '机动车所有人',
  driver_name VARCHAR(50) DEFAULT NULL COMMENT '驾驶员',
  driver_phone VARCHAR(30) DEFAULT NULL COMMENT '驾驶员联系电话',
  affiliated_company VARCHAR(100) DEFAULT NULL COMMENT '挂靠公司',
  insurance_status VARCHAR(100) DEFAULT NULL COMMENT '保险情况',
  insurance_info VARCHAR(255) DEFAULT NULL COMMENT '保险公司及金额',
  owner_id BIGINT DEFAULT NULL COMMENT '当前归属主体ID',
  owner_type VARCHAR(20) DEFAULT NULL COMMENT '冗余主体类型',
  dept_id BIGINT NOT NULL COMMENT '所属中队部门ID',
  photo_file_id VARCHAR(36) DEFAULT NULL COMMENT '车辆照片文件ID',
  vehicle_status VARCHAR(20) NOT NULL DEFAULT 'normal' COMMENT '车辆状态',
  supervision_flag CHAR(1) NOT NULL DEFAULT '0' COMMENT '是否重点监管（0否 1是）',
  warning_level VARCHAR(20) DEFAULT NULL COMMENT '当前预警等级',
  missing_device_count INT NOT NULL DEFAULT 0 COMMENT '缺装设备数量',
  remark VARCHAR(500) DEFAULT NULL COMMENT '备注',
  create_by VARCHAR(64) DEFAULT '' COMMENT '创建者',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_by VARCHAR(64) DEFAULT '' COMMENT '更新者',
  update_time DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  del_flag CHAR(1) NOT NULL DEFAULT '0' COMMENT '删除标志（0存在 2删除）',
  PRIMARY KEY (vehicle_id),
  UNIQUE KEY uk_truck_vehicle_plate (plate_no, plate_color),
  UNIQUE KEY uk_truck_vehicle_vin (vin),
  KEY idx_truck_vehicle_dept_id (dept_id),
  KEY idx_truck_vehicle_owner_id (owner_id),
  KEY idx_truck_vehicle_status (vehicle_status),
  KEY idx_truck_vehicle_warning (warning_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大货车车辆档案表';

CREATE TABLE IF NOT EXISTS truck_vehicle_device (
  device_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  vehicle_id BIGINT NOT NULL COMMENT '车辆ID',
  device_type VARCHAR(30) NOT NULL COMMENT '设备类型',
  product_name VARCHAR(100) DEFAULT NULL COMMENT '产品名称',
  brand VARCHAR(100) DEFAULT NULL COMMENT '品牌',
  install_date DATE DEFAULT NULL COMMENT '安装日期',
  status CHAR(1) NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  remark VARCHAR(500) DEFAULT NULL COMMENT '备注',
  create_by VARCHAR(64) DEFAULT '' COMMENT '创建者',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_by VARCHAR(64) DEFAULT '' COMMENT '更新者',
  update_time DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (device_id),
  UNIQUE KEY uk_truck_vehicle_device (vehicle_id, device_type),
  KEY idx_truck_vehicle_device_vehicle_id (vehicle_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大货车安全设备表';

CREATE TABLE IF NOT EXISTS truck_vehicle_owner_history (
  history_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '归属变更历史ID',
  vehicle_id BIGINT NOT NULL COMMENT '车辆ID',
  old_owner_id BIGINT DEFAULT NULL COMMENT '原主体ID',
  new_owner_id BIGINT DEFAULT NULL COMMENT '新主体ID',
  old_dept_id BIGINT DEFAULT NULL COMMENT '原中队部门ID',
  new_dept_id BIGINT DEFAULT NULL COMMENT '新中队部门ID',
  change_reason VARCHAR(255) DEFAULT NULL COMMENT '变更原因',
  change_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '变更时间',
  change_by VARCHAR(64) NOT NULL DEFAULT '' COMMENT '操作人',
  PRIMARY KEY (history_id),
  KEY idx_truck_owner_history_vehicle_id (vehicle_id),
  KEY idx_truck_owner_history_change_time (change_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大货车车辆归属历史表';

CREATE TABLE IF NOT EXISTS truck_warning_rule (
  rule_id BIGINT NOT NULL AUTO_INCREMENT COMMENT '预警规则ID',
  rule_name VARCHAR(100) NOT NULL COMMENT '规则名称',
  required_device_types TEXT DEFAULT NULL COMMENT '应安装设备类型JSON数组',
  level_one_threshold INT NOT NULL DEFAULT 2 COMMENT '一级预警阈值',
  level_two_threshold INT NOT NULL DEFAULT 2 COMMENT '二级预警阈值（当前与一级相同，表示只保留一级预警）',
  status CHAR(1) NOT NULL DEFAULT '0' COMMENT '状态（0正常 1停用）',
  create_by VARCHAR(64) DEFAULT '' COMMENT '创建者',
  create_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_by VARCHAR(64) DEFAULT '' COMMENT '更新者',
  update_time DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  remark VARCHAR(500) DEFAULT NULL COMMENT '备注',
  PRIMARY KEY (rule_id),
  UNIQUE KEY uk_truck_warning_rule_name (rule_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='大货车预警规则表';

-- 松阳大队及辖区中队。固定ID用于初始化数据权限和测试数据关联。
INSERT IGNORE INTO sys_dept (dept_id, parent_id, ancestors, dept_name, order_num, status, del_flag, create_by, create_time) VALUES
  (9100, 0, '0', '松阳大队', 1, '0', '0', 'admin', NOW()),
  (9101, 9100, '0,9100', '西屏中队', 1, '0', '0', 'admin', NOW()),
  (9102, 9100, '0,9100', '古市中队', 2, '0', '0', 'admin', NOW()),
  (9103, 9100, '0,9100', '江南中队', 3, '0', '0', 'admin', NOW()),
  (9104, 9100, '0,9100', '象溪中队', 4, '0', '0', 'admin', NOW()),
  (9105, 9100, '0,9100', '大东坝中队', 5, '0', '0', 'admin', NOW()),
  (9106, 9100, '0,9100', '玉岩中队', 6, '0', '0', 'admin', NOW());

INSERT IGNORE INTO sys_dict_type (dict_id, dict_name, dict_type, status, create_by, create_time, remark) VALUES
  (9001, '车辆类型', 'truck_vehicle_type', '0', 'admin', NOW(), '大货车管理车辆类型'),
  (9002, '车牌颜色', 'truck_plate_color', '0', 'admin', NOW(), '大货车管理车牌颜色'),
  (9003, '车辆状态', 'truck_vehicle_status', '0', 'admin', NOW(), '大货车管理车辆状态'),
  (9004, '来源标识', 'truck_source_type', '0', 'admin', NOW(), '大货车管理来源标识'),
  (9005, '归属主体类型', 'truck_owner_type', '0', 'admin', NOW(), '大货车管理归属主体类型'),
  (9006, '安全设备类型', 'truck_device_type', '0', 'admin', NOW(), '大货车管理安全设备类型'),
  (9007, '预警等级', 'truck_warning_level', '0', 'admin', NOW(), '大货车管理预警等级');

INSERT IGNORE INTO sys_dict_data (dict_code, dict_sort, dict_label, dict_value, dict_type, css_class, list_class, is_default, status, create_by, create_time, remark) VALUES
  (9001, 1, '自卸货车', 'dump_truck', 'truck_vehicle_type', '', 'warning', 'Y', '0', 'admin', NOW(), '车辆类型'),
  (9002, 2, '混凝土搅拌车', 'mixer_truck', 'truck_vehicle_type', '', 'primary', 'N', '0', 'admin', NOW(), '车辆类型'),
  (9003, 3, '牵引车', 'tractor', 'truck_vehicle_type', '', 'success', 'N', '0', 'admin', NOW(), '车辆类型'),
  (9004, 4, '载货汽车', 'cargo_truck', 'truck_vehicle_type', '', 'info', 'N', '0', 'admin', NOW(), '车辆类型'),
  (9005, 99, '其他', 'other', 'truck_vehicle_type', '', 'info', 'N', '0', 'admin', NOW(), '车辆类型'),
  (9011, 1, '黄牌', 'yellow', 'truck_plate_color', '', 'warning', 'Y', '0', 'admin', NOW(), '车牌颜色'),
  (9012, 2, '蓝牌', 'blue', 'truck_plate_color', '', 'primary', 'N', '0', 'admin', NOW(), '车牌颜色'),
  (9013, 3, '绿牌', 'green', 'truck_plate_color', '', 'success', 'N', '0', 'admin', NOW(), '车牌颜色'),
  (9014, 4, '其他', 'other', 'truck_plate_color', '', 'info', 'N', '0', 'admin', NOW(), '车牌颜色'),
  (9021, 1, '正常', 'normal', 'truck_vehicle_status', '', 'success', 'Y', '0', 'admin', NOW(), '车辆状态'),
  (9022, 2, '停运', 'stopped', 'truck_vehicle_status', '', 'warning', 'N', '0', 'admin', NOW(), '车辆状态'),
  (9023, 3, '转出', 'transferred', 'truck_vehicle_status', '', 'info', 'N', '0', 'admin', NOW(), '车辆状态'),
  (9024, 4, '报废', 'scrapped', 'truck_vehicle_status', '', 'danger', 'N', '0', 'admin', NOW(), '车辆状态'),
  (9031, 1, '本地车辆', 'local', 'truck_source_type', '', 'success', 'Y', '0', 'admin', NOW(), '来源标识'),
  (9032, 2, '外地车辆', 'nonlocal', 'truck_source_type', '', 'warning', 'N', '0', 'admin', NOW(), '来源标识'),
  (9041, 1, '运输企业', 'enterprise', 'truck_owner_type', '', 'primary', 'Y', '0', 'admin', NOW(), '归属主体类型'),
  (9042, 2, '个人车主', 'individual', 'truck_owner_type', '', 'info', 'N', '0', 'admin', NOW(), '归属主体类型'),
  (9051, 1, '刹车辅助系统', 'brake_assist', 'truck_device_type', '', 'danger', 'Y', '0', 'admin', NOW(), '安全设备类型'),
  (9052, 2, '360全景影像', 'panoramic_360', 'truck_device_type', '', 'primary', 'N', '0', 'admin', NOW(), '安全设备类型'),
  (9061, 1, '一级预警', 'level_one', 'truck_warning_level', '', 'danger', 'N', '0', 'admin', NOW(), '预警等级'),
  (9062, 2, '二级预警', 'level_two', 'truck_warning_level', '', 'warning', 'N', '0', 'admin', NOW(), '预警等级'),
  (9063, 3, '无预警', 'none', 'truck_warning_level', '', 'success', 'Y', '0', 'admin', NOW(), '预警等级');

INSERT IGNORE INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, query, route_name, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark) VALUES
  (9000, '大货车管理', 0, 1, 'truck', NULL, '', 'Truck', 1, 0, 'M', '0', '0', '', 'dashboard', 'admin', NOW(), '大货车管理目录'),
  (9002, '主体管理', 9000, 2, 'owner', 'truck/owner/index', '', 'TruckOwner', 1, 0, 'C', '0', '0', 'truck:owner:query', 'peoples', 'admin', NOW(), '大货车归属主体管理'),
  (9003, '车辆档案', 9000, 3, 'vehicle', 'truck/vehicle/index', '', 'TruckVehicle', 1, 0, 'C', '0', '0', 'truck:vehicle:query', 'tree-table', 'admin', NOW(), '大货车车辆档案管理');

INSERT IGNORE INTO sys_menu (menu_id, menu_name, parent_id, order_num, path, component, query, route_name, is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark) VALUES
  (9020, '主体查询', 9000, 10, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:query', '#', 'admin', NOW(), '归属主体查询权限'),
  (9021, '主体新增', 9000, 11, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:add', '#', 'admin', NOW(), '归属主体新增权限'),
  (9022, '主体修改', 9000, 12, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:edit', '#', 'admin', NOW(), '归属主体修改权限'),
  (9023, '主体删除', 9000, 13, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:owner:remove', '#', 'admin', NOW(), '归属主体删除权限'),
  (9030, '车辆查询', 9000, 20, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:query', '#', 'admin', NOW(), '车辆查询权限'),
  (9031, '车辆新增', 9000, 21, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:add', '#', 'admin', NOW(), '车辆新增权限'),
  (9032, '车辆修改', 9000, 22, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:edit', '#', 'admin', NOW(), '车辆修改权限'),
  (9033, '车辆删除', 9000, 23, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:remove', '#', 'admin', NOW(), '车辆删除权限'),
  (9034, '车辆导入', 9000, 24, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:import', '#', 'admin', NOW(), '车辆导入权限'),
  (9035, '车辆导出', 9000, 25, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:vehicle:export', '#', 'admin', NOW(), '车辆导出权限');

INSERT IGNORE INTO sys_role (role_id, role_name, role_key, role_sort, data_scope, menu_check_strictly, dept_check_strictly, status, del_flag, create_by, create_time, remark) VALUES
  (9010, '中队管理员', 'truck_squad_admin', 10, '3', 1, 1, '0', '0', 'admin', NOW(), '仅管理本人所属中队的大货车数据'),
  (9011, '领导权限', 'truck_leader', 11, '1', 1, 1, '0', '0', 'admin', NOW(), '大货车数据只读权限');

INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9000), (9010, 9002), (9010, 9003), (9010, 9020), (9010, 9021), (9010, 9022), (9010, 9023), (9010, 9030), (9010, 9031), (9010, 9032), (9010, 9033), (9010, 9034), (9010, 9035),
  (9011, 9000), (9011, 9002), (9011, 9003), (9011, 9020), (9011, 9030), (9011, 9035);

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
INSERT IGNORE INTO truck_warning_rule (
  rule_id, rule_name, required_device_types, level_one_threshold, level_two_threshold,
  status, create_by, create_time, remark
) VALUES (
  1, '安全设备缺装预警', '["brake_assist","panoramic_360"]', 2, 2,
  '0', 'admin', NOW(), '刹车辅助系统和360全景影像为应安装设备'
);

INSERT IGNORE INTO sys_menu (
  menu_id, menu_name, parent_id, order_num, path, component, query, route_name,
  is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark
) VALUES
  (9004, '重点监管预警', 9000, 4, 'warning', 'truck/warning/index', '', 'TruckWarning', 1, 0, 'C', '0', '0', 'truck:warning:query', 'warning', 'admin', NOW(), '缺装安全设备车辆预警'),
  (9040, '看板查询', 9000, 30, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:dashboard:list', '#', 'admin', NOW(), '业务看板查询权限'),
  (9041, '预警查询', 9004, 31, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:query', '#', 'admin', NOW(), '重点监管预警查询权限'),
  (9042, '预警重算', 9004, 32, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:recalculate', '#', 'admin', NOW(), '重点监管预警重算权限'),
  (9043, '预警导出', 9004, 33, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:warning:export', '#', 'admin', NOW(), '重点监管预警导出权限');

INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9004), (9010, 9040), (9010, 9041), (9010, 9042), (9010, 9043),
  (9011, 9004), (9011, 9040), (9011, 9041), (9011, 9043);

-- 验收账号初始密码均为 admin123，非开发环境部署后必须立即修改。
INSERT IGNORE INTO sys_user (
  user_id, dept_id, user_name, nick_name, user_type, email, phonenumber, sex, avatar,
  password, status, del_flag, create_by, create_time, remark
) VALUES
  (9101, 9101, 'xiping_admin', '西屏中队管理员', '00', '', '', '0', '', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', NOW(), '大货车平台验收账号'),
  (9102, 9100, 'truck_leader', '大队领导', '00', '', '', '0', '', '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', NOW(), '大货车平台验收账号');

INSERT IGNORE INTO sys_user_role (user_id, role_id) VALUES (9101, 9010), (9102, 9011);

-- 清理上游演示用户、部门、岗位和普通角色，组织架构仅保留松阳大队及六个中队。
UPDATE sys_user
SET dept_id = 9100, nick_name = '大队管理员', email = '', phonenumber = '', sex = '0', remark = '松阳大队系统管理员'
WHERE user_id = 1;
DELETE FROM sys_user_role WHERE user_id = 2;
DELETE FROM sys_user_post WHERE user_id IN (1, 2);
DELETE FROM sys_user WHERE user_id = 2;
DELETE FROM sys_role_dept WHERE role_id = 2 OR dept_id BETWEEN 100 AND 109;
DELETE FROM sys_role_menu WHERE role_id = 2;
DELETE FROM sys_role WHERE role_id = 2;
DELETE FROM sys_user_post;
DELETE FROM sys_post;
DELETE FROM sys_dept WHERE dept_id BETWEEN 100 AND 109;
