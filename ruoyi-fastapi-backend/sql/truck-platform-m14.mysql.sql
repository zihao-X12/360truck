-- M14 预警阈值调整：只对「一项设备都没装」的车辆预警（MySQL 8）
--
-- 变更前：level_one_threshold=2、level_two_threshold=1 → 缺 1 项即触发二级预警
-- 变更后：level_one_threshold=2、level_two_threshold=2 → 缺 2 项（一项都没装）才预警
-- 两级阈值相同表示当前业务只保留一级预警；表结构与二级等级字典保留，便于后续恢复分级。
--
-- 重算语义与 TruckWarningService.recalculate 保持一致：
--   missing_device_count = 应安装设备数(2) - 已装设备数
--   已装设备数 = truck_vehicle_device 中 status='0' 且 device_type 属于应安装清单的去重计数
--   warning_level        = 缺装 >= 2 → level_one，否则 none（二级当前不可达）
--   supervision_flag     = 缺装 > 0 → '1'，否则 '0'（与预警等级相互独立）
-- 参与范围：del_flag='0' 且 vehicle_status 不属于 transferred/scrapped。
-- 脚本可重复执行。

START TRANSACTION;

-- 1. 调整阈值
UPDATE truck_warning_rule
SET level_one_threshold = 2,
    level_two_threshold = 2
WHERE rule_id = 1;

-- 2. 重算现有活动车辆
UPDATE truck_vehicle v
LEFT JOIN (
    SELECT vehicle_id, COUNT(DISTINCT device_type) AS installed_count
    FROM truck_vehicle_device
    WHERE status = '0'
      AND device_type IN ('brake_assist', 'panoramic_360')
    GROUP BY vehicle_id
) d ON d.vehicle_id = v.vehicle_id
SET v.missing_device_count = 2 - COALESCE(d.installed_count, 0),
    v.warning_level = CASE
        WHEN 2 - COALESCE(d.installed_count, 0) >= 2 THEN 'level_one'
        ELSE 'none'
    END,
    v.supervision_flag = CASE
        WHEN 2 - COALESCE(d.installed_count, 0) > 0 THEN '1'
        ELSE '0'
    END
WHERE v.del_flag = '0'
  AND v.vehicle_status NOT IN ('transferred', 'scrapped');

COMMIT;
