-- M8 跨中队主体归集（MySQL 8）
START TRANSACTION;

DROP TEMPORARY TABLE IF EXISTS tmp_truck_owner_merge;
CREATE TEMPORARY TABLE tmp_truck_owner_merge AS
SELECT
  owner_type,
  LOWER(TRIM(owner_name)) AS owner_name_key,
  MIN(owner_id) AS keep_owner_id
FROM truck_owner
WHERE del_flag = '0'
GROUP BY owner_type, LOWER(TRIM(owner_name))
HAVING COUNT(*) > 1;

UPDATE truck_vehicle v
JOIN truck_owner o ON o.owner_id = v.owner_id
JOIN tmp_truck_owner_merge m
  ON m.owner_type = o.owner_type
 AND m.owner_name_key = LOWER(TRIM(o.owner_name))
SET v.owner_id = m.keep_owner_id,
    v.owner_type = m.owner_type,
    v.update_by = 'migration_m8',
    v.update_time = NOW()
WHERE o.owner_id <> m.keep_owner_id;

UPDATE truck_vehicle_owner_history h
JOIN truck_owner o ON o.owner_id = h.old_owner_id
JOIN tmp_truck_owner_merge m
  ON m.owner_type = o.owner_type
 AND m.owner_name_key = LOWER(TRIM(o.owner_name))
SET h.old_owner_id = m.keep_owner_id
WHERE o.owner_id <> m.keep_owner_id;

UPDATE truck_vehicle_owner_history h
JOIN truck_owner o ON o.owner_id = h.new_owner_id
JOIN tmp_truck_owner_merge m
  ON m.owner_type = o.owner_type
 AND m.owner_name_key = LOWER(TRIM(o.owner_name))
SET h.new_owner_id = m.keep_owner_id
WHERE o.owner_id <> m.keep_owner_id;

UPDATE truck_owner o
JOIN tmp_truck_owner_merge m
  ON m.owner_type = o.owner_type
 AND m.owner_name_key = LOWER(TRIM(o.owner_name))
SET o.del_flag = '2',
    o.update_by = 'migration_m8',
    o.update_time = NOW()
WHERE o.owner_id <> m.keep_owner_id;

DROP TEMPORARY TABLE tmp_truck_owner_merge;
COMMIT;
