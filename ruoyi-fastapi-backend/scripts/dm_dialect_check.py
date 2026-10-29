"""达梦方言兼容性体检（无需数据库连接）。

用 dmSQLAlchemy 的达梦方言编译器，编译本项目真实的 SQLAlchemy 模型与典型查询，
在不连云数据库的前提下得到「哪些 DDL/查询能编译成达梦 SQL」的结论。

用法（在 ruoyi-fastapi-backend 目录下）：
    python scripts/dm_dialect_check.py
需先把包含 dmSQLAlchemy / dmPython 的目录通过 DM_DIALECT_DIR 指出来。
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
DM_DIALECT_DIR = os.environ.get('DM_DIALECT_DIR', '')
if DM_DIALECT_DIR:
    sys.path.insert(0, DM_DIALECT_DIR)

from dmSQLAlchemy.dmpython import DMDialect_dmPython  # noqa: E402
from sqlalchemy import case, func, select  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

# 触发模型注册
import module_admin.entity.do.dept_do  # noqa: E402
import module_admin.entity.do.notice_do  # noqa: E402
import module_admin.entity.do.role_do  # noqa: E402
import module_admin.entity.do.user_do  # noqa: F401, E402
import module_gat1400.entity.do.gat1400_connect_do  # noqa: E402
import module_gat1400.entity.do.pass_record_do  # noqa: F401, E402
import module_truck.entity.do.truck_do  # noqa: F401, E402
from config.database import Base  # noqa: E402
from module_admin.entity.do.dept_do import SysDept  # noqa: E402
from module_truck.entity.do.truck_do import (  # noqa: E402
    TruckOwner,
    TruckVehicle,
    TruckVehicleDevice,
)


def check_ddl(dialect) -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    for table in Base.metadata.sorted_tables:
        try:
            str(CreateTable(table).compile(dialect=dialect))
        except Exception as exc:
            failures.append((table.name, f'{type(exc).__name__}: {exc}'))
    return failures


def check_query(dialect, stmt) -> tuple[bool, str]:
    try:
        sql = str(stmt.compile(dialect=dialect))
        return True, ' '.join(sql.split())[:120]
    except Exception as exc:
        return False, f'{type(exc).__name__}: {exc}'


def main() -> int:
    dialect = DMDialect_dmPython()
    print(f'方言: {type(dialect).__name__}  driver={dialect.driver}')

    print('\n========== 1) 建表 DDL 编译 ==========')
    failures = check_ddl(dialect)
    print(f'  成功 {len(Base.metadata.sorted_tables) - len(failures)} 张，失败 {len(failures)} 张')
    for name, err in failures:
        print(f'    ✗ {name}: {err}')

    print('\n========== 2) 典型查询编译 ==========')
    vehicle_scope = TruckVehicle.dept_id == 9101
    checks = {
        '车辆分页+权限': select(TruckVehicle).where(TruckVehicle.del_flag == '0', vehicle_scope).limit(10).offset(0),
        '车牌模糊查询': select(TruckVehicle).where(TruckVehicle.plate_no.like('%浙K%')),
        '主体名下车辆数': select(TruckOwner.owner_id, func.count(TruckVehicle.vehicle_id))
        .join(TruckVehicle, TruckVehicle.owner_id == TruckOwner.owner_id)
        .group_by(TruckOwner.owner_id),
        '看板条件聚合': select(
            func.count(TruckVehicle.vehicle_id),
            func.sum(case((TruckVehicle.source_type == 'local', 1), else_=0)),
        ).where(TruckVehicle.del_flag == '0'),
        '设备去重计数': select(
            TruckVehicleDevice.device_type,
            func.count(func.distinct(TruckVehicleDevice.vehicle_id)),
        ).group_by(TruckVehicleDevice.device_type),
        'NOT IN 状态过滤': select(TruckVehicle).where(
            TruckVehicle.vehicle_status.notin_(['transferred', 'scrapped'])
        ),
        '部门权限 find_in_set': select(SysDept.dept_id).where(func.find_in_set(9100, SysDept.ancestors) > 0),
        '部门权限 find_in_set(列参)': select(SysDept.dept_id).where(
            func.find_in_set(SysDept.dept_id, SysDept.ancestors) > 0
        ),
    }
    bad = 0
    for label, stmt in checks.items():
        good, detail = check_query(dialect, stmt)
        mark = '✓' if good else '✗'
        print(f'  {mark} {label}')
        if not good:
            bad += 1
            print(f'      {detail}')
    return 1 if failures or bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
