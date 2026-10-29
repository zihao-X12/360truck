-- M11 过车记录菜单与权限点（PostgreSQL）
BEGIN;

-- 9047 过车记录菜单，9048 查询权限，9049 导出权限
INSERT INTO sys_menu (
  menu_id, menu_name, parent_id, order_num, path, component, query, route_name,
  is_frame, is_cache, menu_type, visible, status, perms, icon, create_by, create_time, remark
) VALUES
  (9047, '过车记录', 9000, 6, 'pass-record', 'truck/pass-record/index', '', 'TruckPassRecord', 1, 0, 'C', '0', '0', 'truck:passrecord:query', 'monitor', 'admin', NOW(), '大华视图库过车记录查询'),
  (9048, '过车记录查询', 9047, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:passrecord:query', '#', 'admin', NOW(), '过车记录查询权限'),
  (9049, '过车记录导出', 9047, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'truck:passrecord:export', '#', 'admin', NOW(), '过车记录导出权限')
ON CONFLICT (menu_id) DO NOTHING;

-- 三角色授权：中队管理员/领导只读查询，导出仅大队管理员（admin 全通）与中队管理员
INSERT INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9047), (9010, 9048), (9010, 9049),
  (9011, 9047), (9011, 9048)
ON CONFLICT (role_id, menu_id) DO NOTHING;

COMMIT;
