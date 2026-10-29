-- M12 视图库对接菜单平级 + 可视化配置项（MySQL 8）
START TRANSACTION;

-- 1. 新建一级目录「视图库对接」（与「大货车管理」9000 平级）
INSERT IGNORE INTO sys_menu (
  menu_id, menu_name, parent_id, order_num, path, component, query, route_name,
  is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark
) VALUES
  (9050, '视图库对接', 0, 1, 'gat1400', '', '', 'Gat1400', 1, 0, 'M', '0', '0', '', 'connection', 'admin', NOW(), 'GA/T1400 视图库对接（与业务菜单平级）');

-- 2. 对接状态页移到新目录下（子路径改为 connect，组件不变）
UPDATE sys_menu SET parent_id = 9050, path = 'connect', order_num = 1 WHERE menu_id = 9044;

-- 3. 角色授权：中队管理员与领导需可见新目录（否则子菜单无法挂载）
INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9050),
  (9011, 9050);

-- 4. 可视化配置默认项（页面可改，.env 为回退值）
-- 注：sys_config 只有 config_id 主键，config_key 没有唯一索引，INSERT IGNORE 不会去重，
-- 重复执行会插入重复配置项，因此必须用 NOT EXISTS 保证幂等（与 PostgreSQL 版保持一致）。
INSERT INTO sys_config (config_name, config_key, config_value, config_type, create_by, create_time, remark)
SELECT v.config_name, v.config_key, v.config_value, v.config_type, 'admin', NOW(), v.remark
FROM (
  SELECT 'GAT1400对接开关' AS config_name, 'gat1400.enabled' AS config_key, 'false' AS config_value, 'N' AS config_type, '是否启用GA/T1400对接' AS remark
  UNION ALL SELECT 'GAT1400平台地址', 'gat1400.platform.addr', '', 'N', '大华视图库平台地址，如 http://ip:port'
  UNION ALL SELECT 'GAT1400设备ID', 'gat1400.device.id', '', 'N', '我方20位设备ID（可自定义，规则见设计文档）'
  UNION ALL SELECT 'GAT1400认证账号', 'gat1400.auth.username', '', 'N', '摘要认证账号（大华平台分配）'
  UNION ALL SELECT 'GAT1400认证密码', 'gat1400.auth.password', '', 'N', '摘要认证密码（加密存储，大华平台分配）'
  UNION ALL SELECT 'GAT1400保活间隔', 'gat1400.keepalive.interval', '60', 'N', '保活间隔秒数，需小于90s标准要求'
  UNION ALL SELECT 'GAT1400订阅类别', 'gat1400.subscribe.detail', '13', 'N', '订阅类别，13=过车记录，多个用逗号分隔'
  UNION ALL SELECT 'GAT1400订阅资源ID', 'gat1400.subscribe.resource.uri', '33110000005030000001', 'N', '订阅资源ID（大华平台下发）'
  UNION ALL SELECT 'GAT1400申请人', 'gat1400.subscribe.applicant.name', '', 'N', '订阅申请人'
  UNION ALL SELECT 'GAT1400申请单位', 'gat1400.subscribe.applicant.org', '', 'N', '订阅申请单位'
  UNION ALL SELECT 'GAT1400订阅有效期', 'gat1400.subscribe.days', '30', 'N', '订阅有效期天数，到期前自动续订'
  UNION ALL SELECT 'GAT1400回调地址', 'gat1400.subscribe.receive.addr', '', 'N', '我方通知回调地址，如 http://IP/VIID/SubscribeNotifications'
  UNION ALL SELECT 'GAT1400通知IP白名单', 'gat1400.notify.allowed.ips', '', 'N', '通知来源IP白名单，逗号分隔，留空不限制'
) AS v
WHERE NOT EXISTS (SELECT 1 FROM sys_config c WHERE c.config_key = v.config_key);

COMMIT;
