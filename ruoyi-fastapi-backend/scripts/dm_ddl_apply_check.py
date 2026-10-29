"""把本项目全部模型的建表 DDL 直接打到真实达梦实例上。

仅验证 DDL 可执行性（编译通过 != 数据库能建），执行完毕后回滚删表，不留副作用。

用法：
    python scripts/dm_ddl_apply_check.py --env dm
环境变量：
    DM_DIALECT_DIR  包含 dmSQLAlchemy/dmPython 的目录
    DM_HOST / DM_PORT / DM_USER / DM_PASSWORD
"""

import os
import sys
from pathlib import Path

DM_DIALECT_DIR = os.environ.get('DM_DIALECT_DIR', '')
if DM_DIALECT_DIR:
    sys.path.insert(0, DM_DIALECT_DIR)
    for _d in (DM_DIALECT_DIR, os.path.join(DM_DIALECT_DIR, 'dmssl')):
        os.environ['PATH'] = _d + os.pathsep + os.environ['PATH']
        try:
            os.add_dll_directory(_d)
        except (AttributeError, OSError):
            pass

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import inspect, text  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402

# 触发全部模型注册
import module_admin.entity.do.dept_do  # noqa: E402
import module_admin.entity.do.notice_do  # noqa: E402
import module_admin.entity.do.role_do  # noqa: E402
import module_admin.entity.do.user_do  # noqa: F401, E402
import module_gat1400.entity.do.gat1400_connect_do  # noqa: E402
import module_gat1400.entity.do.pass_record_do  # noqa: F401, E402
import module_truck.entity.do.truck_do  # noqa: F401, E402
from config.database import Base, sync_engine  # noqa: E402


def main() -> int:
    print(f'同步 URL 方言: {sync_engine.dialect.name}')
    existing = set(inspect(sync_engine).get_table_names())
    print(f'库中已有表 {len(existing)} 张')

    created: list[str] = []
    failed: list[tuple[str, str]] = []
    with sync_engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            ddl = str(CreateTable(table).compile(dialect=sync_engine.dialect))
            try:
                conn.execute(text(ddl))
                created.append(table.name)
            except Exception as exc:
                failed.append((table.name, str(exc).splitlines()[0][:150]))

    print(f'\n创建成功 {len(created)} 张，失败 {len(failed)} 张')
    for name, err in failed:
        print(f'  ✗ {name}: {err}')

    # 清理：只删本次新建的表
    with sync_engine.begin() as conn:
        for name in reversed(created):
            try:
                conn.execute(text(f'DROP TABLE "{name}"'))
            except Exception:
                try:
                    conn.execute(text(f'DROP TABLE {name}'))
                except Exception as exc:
                    print(f'  清理失败 {name}: {str(exc)[:80]}')
    print(f'已清理 {len(created)} 张临时表')

    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
