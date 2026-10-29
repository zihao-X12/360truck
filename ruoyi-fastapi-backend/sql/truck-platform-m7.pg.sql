-- M7 中队管理员操作权限修复（PostgreSQL）
BEGIN;

INSERT INTO sys_role (
  role_id, role_name, role_key, role_sort, data_scope, menu_check_strictly,
  dept_check_strictly, status, del_flag, create_by, create_time, remark
) VALUES (
  9010, '中队管理员', 'truck_squad_admin', 10, '3', 1,
  1, '0', '0', 'admin', NOW(), '仅管理本人所属中队的大货车数据'
)
ON CONFLICT (role_id) DO UPDATE SET
  role_name = EXCLUDED.role_name,
  role_key = EXCLUDED.role_key,
  data_scope = '3',
  status = '0',
  del_flag = '0',
  remark = EXCLUDED.remark;

UPDATE sys_user
SET dept_id = 9101, status = '0', del_flag = '0'
WHERE user_name = 'xiping_admin';

DELETE FROM sys_user_role ur
USING sys_user u
WHERE u.user_id = ur.user_id
  AND u.user_name = 'xiping_admin'
  AND ur.role_id <> 9010;

INSERT INTO sys_user_role (user_id, role_id)
SELECT user_id, 9010 FROM sys_user WHERE user_name = 'xiping_admin'
ON CONFLICT DO NOTHING;

INSERT INTO sys_role_menu (role_id, menu_id) VALUES
  (9010, 9000),
  (9010, 9002), (9010, 9020), (9010, 9021), (9010, 9022), (9010, 9023),
  (9010, 9003), (9010, 9030), (9010, 9031), (9010, 9032), (9010, 9033), (9010, 9034), (9010, 9035),
  (9010, 9004), (9010, 9040), (9010, 9041), (9010, 9042), (9010, 9043)
ON CONFLICT (role_id, menu_id) DO NOTHING;

COMMIT;
