"""达梦真机连通性与关键行为验证。

验证内容（全部针对真实达梦实例）：
  1. dmPython 同步连接（SQLAlchemy 同步 Engine）
  2. 建表 / 逐行自增主键（BigInteger 与 Integer）
  3. 分页 limit/offset、LIKE、NOT IN、count(distinct)
  4. find_in_set（项目部门数据权限依赖）
  5. 多行 INSERT + RETURNING（达梦不支持，项目已改为逐行 flush）

注意：dmAsync 异步路径在 SQLAlchemy 2.0.x 下不可用，故本脚本只验证同步路径。

用法：
    python scripts/dm_sync_check.py
环境变量（均有默认值，生产环境请显式传入）：
    DM_HOST / DM_PORT / DM_USER / DM_PASSWORD / DM_DIALECT_DIR
"""

import os
import sys

DM_DIALECT_DIR = os.environ.get('DM_DIALECT_DIR', '')
if DM_DIALECT_DIR:
    sys.path.insert(0, DM_DIALECT_DIR)
    for _d in (DM_DIALECT_DIR, os.path.join(DM_DIALECT_DIR, 'dmssl')):
        os.environ['PATH'] = _d + os.pathsep + os.environ['PATH']
        try:
            os.add_dll_directory(_d)
        except (AttributeError, OSError):
            pass

HOST = os.environ.get('DM_HOST', '127.0.0.1')
PORT = os.environ.get('DM_PORT', '5236')
USER = os.environ.get('DM_USER', 'SYSDBA')
PASSWORD = os.environ.get('DM_PASSWORD', '')

import sqlalchemy  # noqa: E402
from sqlalchemy import (  # noqa: E402
    BigInteger,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session  # noqa: E402

URL = f'dm+dmPython://{USER}:{PASSWORD}@{HOST}:{PORT}'
FAILURES: list[str] = []


class Base(DeclarativeBase):
    pass


class ProbeBigInt(Base):
    """模拟项目业务表：BigInteger 自增主键。"""

    __tablename__ = 'dm_probe_bigint'
    probe_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    payload = Column(Text)
    created = Column(DateTime, server_default=func.now())


class ProbeInt(Base):
    """模拟上游 sys_* 表：Integer 自增主键。"""

    __tablename__ = 'dm_probe_int'
    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(50))


def main() -> int:
    print(f'SQLAlchemy {sqlalchemy.__version__}')
    print(f'目标 {HOST}:{PORT} 用户 {USER}')
    engine = create_engine(URL)
    print(f'方言 {type(engine.dialect).__name__}')

    with engine.connect() as conn:
        conn.execute(text('SELECT 1 FROM DUAL'))
    print('[0] 连接成功')

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print('[1] 建表成功')

    with Session(engine) as session:
        for name, payload in [('一号', None), ('二号', '中文内容')]:
            session.add(ProbeBigInt(name=name, payload=payload))
            session.flush()
        session.commit()
        rows = session.execute(select(ProbeBigInt).order_by(ProbeBigInt.probe_id)).scalars().all()
        got = [row.probe_id for row in rows]
        print(f'[2] BigInteger 自增主键 -> {got}，中文回读 -> {[row.payload for row in rows]}')
        if got != [1, 2]:
            FAILURES.append(f'BigInteger 自增异常：{got}')

    with Session(engine) as session:
        session.add(ProbeInt(label='alpha'))
        session.flush()
        session.commit()
        value = session.execute(select(ProbeInt.id)).scalar_one()
        print(f'[3] Integer 自增主键 -> {value}')
        if value is None:
            FAILURES.append('Integer 自增主键返回 None')

    try:
        with Session(engine) as session:
            session.add_all([ProbeInt(label='m1'), ProbeInt(label='m2')])
            session.commit()
        print('[4] add_all 多行插入 -> 可用')
    except Exception as exc:
        print(f'[4] add_all 多行插入 -> 不可用（预期）：{type(exc).__name__}')
        print('    项目已改为逐行 add + flush，无需处理')

    with Session(engine) as session:
        total = session.execute(select(func.count(ProbeBigInt.probe_id))).scalar_one()
        page = session.execute(
            select(ProbeBigInt.name).order_by(ProbeBigInt.probe_id).limit(1).offset(1)
        ).scalars().all()
        liked = session.execute(select(ProbeBigInt.name).where(ProbeBigInt.name.like('%号%'))).scalars().all()
        notin = session.execute(select(ProbeBigInt.name).where(ProbeBigInt.name.notin_(['x']))).scalars().all()
        distinct = session.execute(select(func.count(func.distinct(ProbeBigInt.name)))).scalar_one()
        print(f'[5] count={total} limit/offset={page} like={liked} notin={len(notin)} distinct={distinct}')

    try:
        with Session(engine) as session:
            session.execute(text("CREATE TABLE dm_probe_dept (dept_id INT PRIMARY KEY, ancestors VARCHAR(200))"))
            session.execute(text("INSERT INTO dm_probe_dept VALUES (9100,'0')"))
            session.execute(text("INSERT INTO dm_probe_dept VALUES (9101,'0,9100')"))
            session.execute(text("INSERT INTO dm_probe_dept VALUES (9102,'0,9100,9101')"))
            session.commit()
        with Session(engine) as session:
            found = session.execute(
                text("SELECT dept_id FROM dm_probe_dept WHERE find_in_set('9100', ancestors) > 0 ORDER BY dept_id")
            ).scalars().all()
        print(f'[6] find_in_set（部门数据权限）-> {found}')
        if list(found) != [9101, 9102]:
            FAILURES.append(f'find_in_set 结果异常：{found}')
    except Exception as exc:
        print(f'[6] find_in_set -> 不可用：{type(exc).__name__}: {str(exc)[:120]}')
        FAILURES.append('find_in_set 不可用')

    with Session(engine) as session:
        session.execute(text('DROP TABLE dm_probe_dept'))
        session.commit()
    Base.metadata.drop_all(engine)
    engine.dispose()

    print('\n================ 结论 ================')
    if FAILURES:
        for item in FAILURES:
            print(f'  ✗ {item}')
        return 1
    print('全部通过')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
