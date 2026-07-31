-- M6 用户与组织数据清理（MySQL 8）
START TRANSACTION;

-- 大队管理员使用系统管理员账号，中队管理员和领导使用预设业务角色。
UPDATE sys_user
SET dept_id = 9100,
    nick_name = '大队管理员',
    email = '',
    phonenumber = '',
    sex = '0',
    remark = '松阳大队系统管理员'
WHERE user_id = 1;

UPDATE sys_user
SET dept_id = 9101,
    nick_name = '西屏中队管理员',
    email = '',
    phonenumber = '',
    sex = '0',
    remark = '大货车平台验收账号'
WHERE user_id = 9101;

INSERT IGNORE INTO sys_user_role (user_id, role_id) VALUES (9101, 9010), (9102, 9011);

-- 清理上游演示账号及其角色、岗位关系。
DELETE FROM sys_user_role WHERE user_id = 2;
DELETE FROM sys_user_post WHERE user_id IN (1, 2);
DELETE FROM sys_user WHERE user_id = 2;

-- 本项目不使用上游岗位和普通角色。
DELETE FROM sys_role_dept WHERE role_id = 2 OR dept_id BETWEEN 100 AND 109;
DELETE FROM sys_role_menu WHERE role_id = 2;
DELETE FROM sys_role WHERE role_id = 2;
DELETE FROM sys_user_post;
DELETE FROM sys_post;

-- 组织架构只保留松阳大队及六个中队。
DELETE FROM sys_dept WHERE dept_id BETWEEN 100 AND 109;

COMMIT;
