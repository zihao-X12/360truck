-- M13 软删释放唯一键（PostgreSQL）
-- 问题：truck_owner 的 credit_code / id_card_no、truck_vehicle 的 (plate_no, plate_color) / vin
--       都是唯一索引且不含 del_flag，软删后身份字段仍被占用，重建同一主体或车辆时
--       报 duplicate key。
-- 处置：软删时置空身份字段（由应用层执行），并把 plate_no 改为可空。
--       本脚本负责结构变更与历史数据清理，可重复执行。

BEGIN;

-- 1. plate_no 允许为空（软删后置空以释放唯一键）
ALTER TABLE truck_vehicle ALTER COLUMN plate_no DROP NOT NULL;

-- 2. 清理历史遗留：已软删的主体，其身份字段不再保留
UPDATE truck_owner
SET credit_code = NULL,
    id_card_no = NULL
WHERE del_flag = '2'
  AND (credit_code IS NOT NULL OR id_card_no IS NOT NULL);

-- 3. 清理历史遗留：已软删的车辆，其车牌与车架号不再保留
UPDATE truck_vehicle
SET plate_no = NULL,
    vin = NULL
WHERE del_flag = '2'
  AND (plate_no IS NOT NULL OR vin IS NOT NULL);

COMMIT;
