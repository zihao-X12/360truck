-- M5 验收账号增量脚本（MySQL 8）
-- 初始密码均为 admin123，部署到非开发环境后必须立即修改。
INSERT IGNORE INTO sys_user (
  user_id, dept_id, user_name, nick_name, user_type, email, phonenumber, sex, avatar,
  password, status, del_flag, create_by, create_time, remark
) VALUES
  (9101, 9101, 'xiping_admin', '西屏中队管理员', '00', '', '', '0', '',
   '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', NOW(), '大货车平台验收账号'),
  (9102, 9100, 'truck_leader', '大队领导', '00', '', '', '0', '',
   '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2', '0', '0', 'admin', NOW(), '大货车平台验收账号');

INSERT IGNORE INTO sys_user_role (user_id, role_id) VALUES
  (9101, 9010),
  (9102, 9011);

-- 清理基础模板中本平台不使用的原始菜单及角色关联。
DELETE FROM sys_role_menu WHERE menu_id IN (
  2, 4, 99, 104, 106, 107, 109, 110, 111, 112, 113, 114, 115, 118, 119,
  1020, 1021, 1022, 1023, 1024, 1030, 1031, 1032, 1033, 1034, 1035, 1036,
  1037, 1038, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054, 1061,
  1062, 1063, 1064
);
DELETE FROM sys_menu WHERE menu_id IN (
  2, 4, 99, 104, 106, 107, 109, 110, 111, 112, 113, 114, 115, 118, 119,
  1020, 1021, 1022, 1023, 1024, 1030, 1031, 1032, 1033, 1034, 1035, 1036,
  1037, 1038, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054, 1061,
  1062, 1063, 1064
);
