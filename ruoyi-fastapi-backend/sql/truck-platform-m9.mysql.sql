-- M9 GA/T1400 对接状态表（MySQL 8）
START TRANSACTION;

CREATE TABLE IF NOT EXISTS `gat1400_connect` (
  `connect_id`         BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
  `register_status`    VARCHAR(20)  NOT NULL DEFAULT 'unregistered' COMMENT '注册状态 unregistered/online/offline',
  `fail_count`         INT          NOT NULL DEFAULT 0 COMMENT '连续失败次数',
  `last_register_time` DATETIME     DEFAULT NULL COMMENT '最近注册成功时间',
  `last_keepalive_time` DATETIME    DEFAULT NULL COMMENT '最近保活时间',
  `keepalive_count`    BIGINT       NOT NULL DEFAULT 0 COMMENT '保活累计次数',
  `error_message`      VARCHAR(500) DEFAULT '' COMMENT '最近一次错误信息',
  `create_time`        DATETIME     DEFAULT NULL COMMENT '创建时间',
  `update_time`        DATETIME     DEFAULT NULL COMMENT '更新时间',
  `del_flag`           CHAR(1)      NOT NULL DEFAULT '0' COMMENT '删除标志 0正常 2删除',
  PRIMARY KEY (`connect_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='GA/T1400对接状态表（单行）';

-- GA/T1400 对接菜单与权限点（9044 菜单，9045 查询，9046 操作）
INSERT IGNORE INTO sys_menu (
  menu_id, menu_name, parent_id, order_num, path, component, query, route_name,
  is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark
) VALUES
  (9044, 'GA/T1400对接', 9000, 5, 'gat1400', 'system/gat1400/index', '', 'TruckGat1400', 1, 0, 'C', '0', '0', 'gat1400:connect:query', 'connection', 'admin', NOW(), '大华视图库对接状态管理'),
  (9045, '对接状态查询', 9044, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'gat1400:connect:query', '#', 'admin', NOW(), '对接状态查询权限'),
  (9046, '对接操作', 9044, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'gat1400:connect:operate', '#', 'admin', NOW(), '手动注册/保活/注销权限');

-- 中队管理员与领导只读查询，操作权限仅大队管理员（admin 角色 *:*:* 全通）
INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9044), (9010, 9045),
  (9011, 9044), (9011, 9045);

COMMIT;
