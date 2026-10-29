-- M8 跨中队主体归集（PostgreSQL）
-- 将同一「主体类型 + 规范化名称」的重复主体合并到最小 owner_id，
-- 同步改写车辆与归属历史引用，并把被合并主体软删。
BEGIN;

-- keep_owner_id 必然等于该名称下最小的 owner_id，因此可直接用等值条件筛选重复项。
WITH merged AS (
  SELECT
    owner_type,
    LOWER(TRIM(owner_name)) AS owner_name_key,
    MIN(owner_id)           AS keep_owner_id
  FROM truck_owner
  WHERE del_flag = '0'
  GROUP BY owner_type, LOWER(TRIM(owner_name))
  HAVING COUNT(*) > 1
)
UPDATE truck_vehicle v
SET owner_id = m.keep_owner_id,
    owner_type = m.owner_type,
    update_by = 'migration_m8',
    update_time = NOW()
FROM truck_owner o, merged m
WHERE o.owner_id = v.owner_id
  AND o.owner_type = m.owner_type
  AND LOWER(TRIM(o.owner_name)) = m.owner_name_key
  AND o.owner_id <> m.keep_owner_id;

WITH merged AS (
  SELECT
    owner_type,
    LOWER(TRIM(owner_name)) AS owner_name_key,
    MIN(owner_id)           AS keep_owner_id
  FROM truck_owner
  WHERE del_flag = '0'
  GROUP BY owner_type, LOWER(TRIM(owner_name))
  HAVING COUNT(*) > 1
)
UPDATE truck_vehicle_owner_history h
SET old_owner_id = m.keep_owner_id
FROM merged m
WHERE h.old_owner_id IS NOT NULL
  AND h.old_owner_id <> m.keep_owner_id
  AND EXISTS (
    SELECT 1 FROM truck_owner o
    WHERE o.owner_id = h.old_owner_id
      AND o.owner_type = m.owner_type
      AND LOWER(TRIM(o.owner_name)) = m.owner_name_key
  );

WITH merged AS (
  SELECT
    owner_type,
    LOWER(TRIM(owner_name)) AS owner_name_key,
    MIN(owner_id)           AS keep_owner_id
  FROM truck_owner
  WHERE del_flag = '0'
  GROUP BY owner_type, LOWER(TRIM(owner_name))
  HAVING COUNT(*) > 1
)
UPDATE truck_vehicle_owner_history h
SET new_owner_id = m.keep_owner_id
FROM merged m
WHERE h.new_owner_id IS NOT NULL
  AND h.new_owner_id <> m.keep_owner_id
  AND EXISTS (
    SELECT 1 FROM truck_owner o
    WHERE o.owner_id = h.new_owner_id
      AND o.owner_type = m.owner_type
      AND LOWER(TRIM(o.owner_name)) = m.owner_name_key
  );

WITH merged AS (
  SELECT
    owner_type,
    LOWER(TRIM(owner_name)) AS owner_name_key,
    MIN(owner_id)           AS keep_owner_id
  FROM truck_owner
  WHERE del_flag = '0'
  GROUP BY owner_type, LOWER(TRIM(owner_name))
  HAVING COUNT(*) > 1
)
UPDATE truck_owner o
SET del_flag = '2',
    update_by = 'migration_m8',
    update_time = NOW()
FROM merged m
WHERE o.owner_type = m.owner_type
  AND LOWER(TRIM(o.owner_name)) = m.owner_name_key
  AND o.owner_id <> m.keep_owner_id
  AND o.del_flag = '0';

COMMIT;
