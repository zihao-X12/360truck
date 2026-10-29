# 更新日志

## 大货车管理平台

### 达梦数据库（DM8）适配 · 调研结论与处置

在本地达梦 DM8 实例（`dm8_20241022_x86_rh6_64_single`，CASE_SENSITIVE=1、UNICODE_FLAG=0）
与 SQLAlchemy 2.0.x 上完成真机验证。

**结论：当前版本继续使用 MySQL，暂不切换到达梦。**

原因：达梦异步方言不可用，必须把数据访问层整体改为同步（涉及 dao 28 + service 36 +
controller 32 共约 96 个文件、约 1292 处 `await`）。改造本身已验证可行（应用可正常构建、
220 条路由正常注册），但需要同步重写整套测试的 mock 与断言，回归成本与风险均较高，
且当前 MySQL 路径功能完整、测试 480 项通过。

**本次验证获得的关键事实（供后续决策使用）**

1. **达梦异步方言不可用（阻塞项）**：dmSQLAlchemy 的 `dmAsync` 在 SQLAlchemy
   2.0.36 / 2.0.40 / 2.0.46 上均报
   `AttributeError: 'AsyncAdapt_dmasync_connection' object attribute '_connection' is read-only`
   （根因：`AsyncAdapt_dmasync_connection.__slots__` 未包含 `_connection`）；
   SQLAlchemy 2.1.x 上更早失败（`cannot import name 'await_fallback'`）。
2. **同步路径可用**：`dm+dmPython` 同步 Engine 经真机验证通过 —— 建表、BigInteger/Integer
   自增主键、`limit/offset` 分页、`LIKE`、`NOT IN`、`count(distinct)`、中文回读均正常。
3. **`find_in_set` 在达梦可用**：项目部门数据权限所用的
   `WHERE find_in_set(dept_id, ancestors) > 0` 实测正常，无需改写。
   （达梦不支持的 MySQL 函数里，`GROUP_CONCAT` 确认不可用，但项目未使用。）
4. **达梦不支持「多行 INSERT + RETURNING」**：`session.add_all([...])` 会抛
   `FlushError: Multi-row INSERT ... did not produce the correct number of INSERTed rows
   for RETURNING`；dmPython 原生 `executemany` 与逐行 `add + flush` 均正常。
5. **达梦方言无法渲染 `LONGBLOB`**：`notice_do` 原先的
   `mysql.LONGBLOB if db_type == 'mysql' else LargeBinary` 写法在 `db_type='dm'` 时会落到
   `LONGBLOB` 导致建表编译失败。

**保留的资产**

- `ruoyi-fastapi-backend/scripts/dm_dialect_check.py`：离线达梦方言编译体检（模型 DDL + 典型查询）
- `ruoyi-fastapi-backend/scripts/dm_sync_check.py`：达梦真机连通与关键行为验证
- `ruoyi-fastapi-backend/scripts/dm_ddl_apply_check.py`：将全部模型 DDL 真实建到达梦并回滚清理
- `ruoyi-fastapi-backend/.env.dm`：达梦验证配置模板（不含真实凭据）

后续若决定切换达梦，上述结论可直接复用，无需重新试错。

### 交付打包与端到端部署验证

**目标环境补充确认**：MySQL **也是 Docker 部署**（非宿主机直装），Redis 未部署。
这带来两处必要调整，已写入部署指南。

**调整 1：确认 MySQL 容器是否发布端口（新增指南 2.1 节）**

后端容器用 `network_mode: host`，以 `127.0.0.1:<端口>` 连接 MySQL。能否连通取决于
MySQL 容器有没有把端口发布到宿主机，已用对照组实测：

| MySQL 容器启动方式 | host 网络的后端 |
| --- | --- |
| `docker run -p 3306:3306 ...`（发布端口） | **可连接** |
| 仅 `--network <自定义网络>`、未 `-p` | **不可连接**（同网络容器可用容器名，host 网络不行） |

指南给出三步自查（`docker port <容器名> 3306`、`docker inspect` 看网络与端口映射），
并按「已发布 / 未发布」两种情况给处置：未发布时推荐**备份后重建容器并补 `-p`**
（附完整的参数记录命令，避免丢卷），备选是改用 bridge 网络编排。

**调整 2：`mysql` 客户端可能不存在（改写指南第 3 节）**

麒麟宿主机通常不装 MySQL 客户端，故建库、导脚本、校验三处都补了
`docker exec -i <容器名> mysql ...` 写法，可不装客户端完成初始化。
其中 `-i` 不可省（脚本需经 stdin 传入）—— 已用替身容器实测该重定向机制：
949 行脚本→容器内 949 行，逐脚本循环投递字节数一致。

另补充：为系统建专用库账号时主机部分应用 `'%'` 而非 `'127.0.0.1'`，
因为后端经 docker-proxy 转发，来源地址不一定是回环。

**以下为首次打包时的记录**

新增交付打包能力，并用**打包后的产物**完成了一次真实端到端验证。

**新增文件**

| 文件 | 说明 |
| --- | --- |
| `部署指南.md` | 交付包主入口：方案 A（仅后端容器 + 宿主机 nginx/Redis）/ 方案 B（全容器）、数据库初始化、校验、排障、备份 |
| `docker-compose.backend-only.yml` | 方案 A 编排：只起后端容器，`network_mode: host` 直连宿主机 MySQL/Redis |
| `deploy/nginx/truck-bank.conf` | 宿主机 nginx 配置（托管 `dist/`，反代 `/docker-api/` → `127.0.0.1:9099`） |
| `deploy/redis/{redis.conf,truck-bank-redis.service,install-redis.sh}` | 随包 Redis（systemd 托管，可自动识别是否带二进制） |
| `scripts/package-release.ps1` | 打包脚本：robocopy 排除开发期产物，内建 6 项交付前校验 |

**关键发现：Redis 必须 ≥ 6.2**

后端用 Redis Streams 的 `XAUTOCLAIM` 做日志聚合与 GA/T1400 通知消费。
实测在 Redis **6.0.16** 上该命令不存在，两个消费循环每秒报错：

```
unknown command `XAUTOCLAIM`, with args beginning with: `log:stream`, ...
```

此时登录、车辆、主体、看板等功能**正常**，但操作日志聚合与过车记录消费**不可用**，
且日志被持续刷屏。麒麟 V10 / openEuler 20.03 默认源里的 redis 通常是 **5.0.x / 6.0.x**，
直接 `dnf install redis` 会踩到该问题。故交付包提供 `deploy/redis/install-redis.sh`：
优先安装随包二进制；若无二进制则检查系统版本并给出结论；会自动停用系统旧 redis 服务
以避免端口冲突，并处理 SELinux 端口/目录上下文。

**端到端验证（用打包产物实际跑通）**

在 WSL 内模拟麒麟拓扑（MySQL 8.0.46 + Redis + 后端容器 `network_mode: host`）：

| 验证项 | 结果 |
| --- | --- |
| 后端镜像构建（`Dockerfile.kylin`） | 成功，2.29 GB |
| 镜像架构 / glibc | `linux/amd64` / **2.28**（与麒麟一致） |
| 镜像内 `create_app()` | 220 路由 |
| 13 个初始化脚本灌入空库 | **13/13 成功**；38 表、组织 7、菜单 6、账号 3、GAT1400 配置 13、阈值 2/2 |
| 用打包的 compose + 镜像 `up -d --no-build` | 容器启动，`health=healthy` |
| 登录 | 成功（token 452 字符，`dept_name=松阳大队` 中文正确） |
| 只读接口 | `vehicle/owner/warning/list`、`dashboard/summary`、`dashboard/dept-stat` 全 200，返回 6 个中队 |
| **写路径** | 新增主体 → 落库成功 → 列表可查回（中文正常） |
| 前端 `dist` | 用 `npm run build:docker` 重建，API 前缀 `/docker-api`（与 nginx 一致） |

**交付前发现并修正的问题**

1. 仓库内 `ruoyi-fastapi-frontend/dist` 原是 `/prod-api` 构建，与麒麟 nginx 的 `/docker-api`
   不匹配，直接放入包会「页面能开但接口 404」。已重建为 `/docker-api`。
2. `requirements.txt` 末行 `.` 承担安装项目自身（提供 `ruoyi` CLI）的作用，不可删除；
   此前已修正为 LF 并保留该项。

**未纳入包的内容**：MySQL/Redis/nginx 的 Docker 镜像（Docker Hub 在本环境被 DNS 重定向到
127.0.0.1，无法获取）、达梦相关文件（按交付决定排除）、`.venv`/`node_modules`/`logs`、
`ruoyi-fastapi-test`（E2E 工程，需浏览器环境）。

### 数据库名统一为 truck_bank

按交付要求，数据库名由 `ruoyi-fastapi` 改为 **`truck_bank`**（下划线，无连字符）。

**改动范围**（仅改「库名值」，目录名 `ruoyi-fastapi-backend` / `-frontend` / `-test` 一律未动）：

| 类型 | 文件 |
| --- | --- |
| 代码默认值 | `config/env.py`：`db_database = 'truck_bank'` |
| 环境文件 | `.env.dev`、`.env.dockermy`、`.env.dockerpg`、`.env.prod` |
| 编排文件 | `docker-compose.my.yml`（`MYSQL_DATABASE`）、`docker-compose.pg.yml`（`POSTGRES_DB`）、`docker-compose.kylin.yml`、`ruoyi-fastapi-test/docker-compose.test.{my,pg}.yml` |
| 交付模板 | `.env.deploy.example`（新增 `DB_DATABASE` / `DB_USERNAME`） |
| 文档与脚本 | `docs/deploy-kylin-v10.md`、`README.md`、`scripts/local-permission-test.ps1`、`docs/cli_usage.md`、`alembic/env.py` 注释 |

**验证**（真实执行，非推断）：

- 全新创建 `truck_bank`（utf8mb4 / utf8mb4_general_ci），按序执行 13 个初始化脚本 —— **13/13 成功**。
- 结果：表总数 38、组织 7（大队 + 6 中队）、业务菜单 6、业务表 6、验收账号 3、
  GAT1400 配置 13、预警阈值 2/2、`truck_vehicle.plate_no` 可空。
- 应用配置解析：`db_database = truck_bank`，连接串为
  `mysql+asyncmy://root:***@127.0.0.1:3306/truck_bank`。
- 应用实连新库查询：`SELECT DATABASE()` → `truck_bank`，业务表计数正确。
- 重启后端后三类角色登录与车辆/主体接口均正常（新库无业务数据，返回 0 属预期）。

**注意**：连接串为字符串拼接
（`{db_host}:{db_port}/{db_database}`），库名含下划线无需转义，可直接使用。

### 银河麒麟 V10 部署适配

**目标环境确认**：银河麒麟 V10（x86_64，**glibc 2.28**），Docker 已部署，
**MySQL 8.0.45 已部署在宿主机**（非容器），**Redis 尚未部署**。

**关键风险与处置：更换后端基础镜像**

原 `Dockerfile.my` 使用 `python:3.10`（Debian 12，**glibc 2.36**）。在 glibc 2.36 环境构建时，
pip 会优先选择 `manylinux_2_28` / `manylinux_2_34` 的 wheel ——
`asyncmy`、`Pillow`、`greenlet` 等目前**只发布 `manylinux_2_28` 及以上**的 Linux wheel。
这类产物在麒麟 V10（glibc 2.28）上运行会报 `GLIBC_2.34 not found`，
表现为**镜像能构建成功、但在目标机器上无法启动**，属于容易漏到部署现场才发现的问题。

改用 PyPA 官方 `quay.io/pypa/manylinux_2_28_x86_64`（基于 AlmaLinux 8.10，**glibc 2.28**，
内置 CPython 3.10），与目标系统 glibc 对齐，新增 `Dockerfile.kylin`。

**已在 glibc 2.28 环境实测（非推断）**：

| 验证项 | 结果 |
| --- | --- |
| `pip install -r requirements.txt`（35 项直接依赖 → 148 个包） | 全部成功，**无源码编译** |
| `sqlglotrs`（Rust 核心） | 0.12.0 导入正常，sqlglot 32 dialects |
| `asyncmy` 0.2.11、`Pillow` 12.1.1、`pandas` 2.3.3、`bcrypt`、`psutil`、`cryptography`、`greenlet` | 均 wheel，导入正常 |
| `create_app()` | 成功，**220 条路由**，与开发环境一致 |
| `ruoyi` CLI（`pyproject.toml` 入口） | 命令已生成，`--help` 正常 |
| `network_mode: host` 容器访问宿主机回环服务 | 可连接；**并用 bridge 网络做对照组确认非误判** |

**新增文件**

- `ruoyi-fastapi-backend/Dockerfile.kylin`：glibc 2.28 基线后端镜像。
  依赖安装分两步（先装依赖清单，再 `pip install --no-deps .` 安装项目自身以生成 CLI），
  便于利用层缓存。
- `docker-compose.kylin.yml`：复用宿主机 MySQL（不启动数据库容器）、启动 Redis 容器
  （端口仅绑 `127.0.0.1`）、前后端均用 `network_mode: host`。
- `ruoyi-fastapi-frontend/bin/nginx.dockerkylin.conf` 与 `-8080.conf`：
  host 网络下反代 `127.0.0.1:9099`（不能用容器服务名，host 模式下无法解析）。
- `docs/deploy-kylin-v10.md`：麒麟部署完整指南，含与通用方案的三点差异、
  前置检查、数据库初始化、部署后校验、排障对照表与兼容性结论。

**顺带修复：`requirements.txt` 行尾与路径依赖**

该文件原为 **CRLF 行尾**，且末行是 `.`（安装项目自身以提供 `ruoyi` CLI 入口）。
CRLF 本身不影响 Docker 构建（`WORKDIR /app` + `COPY . .` 恰好满足），
但会导致在其他路径下 `pip install -r` 解析异常、报
`Directory '.' is not installable`。已统一为 LF 并保留 `.` 条目
（该条目必需：`pyproject.toml` 的 `ruoyi = "cli.main:main"` 与 Dockerfile 的
`CMD ["ruoyi", "app", "run"]` 都依赖它，且 `utils/import_util.py` 会检查 `pyproject.toml` 存在）。

**未验证**：麒麟真机上的镜像构建与容器启动。本机无麒麟环境，且 Docker Hub 不可达
（`registry-1.docker.io` 被阻断，quay.io 可达），故使用 `quay.io` 的 glibc 2.28 镜像做等价验证。

### 离线交付支持：镜像包清单与构建上下文优化

**新增**

- `docs/offline-image-bundle.md`：离线镜像包完整清单与运行手册，含镜像枚举、浮动标签风险、
  digest 固定方法、导出/导入步骤、内网启动（`--no-build`）、升级回滚与交付前检查清单。
- `scripts/export-offline-bundle.sh`：一键导出脚本。含镜像存在性前置检查、架构告警
  （非 `linux/amd64` 会提示内网 `exec format error` 风险）、`image-digests.txt` 记录、
  `docker save` + `gzip -9` + `sha256` 校验和，并自动收集 `deploy/*-init/`、compose 文件、
  密钥模板与手册到 `dist/offline-bundle/`。

**关键约束（写入手册）**：内网**不能自行构建镜像** ——
`Dockerfile.my`/`Dockerfile.pg` 内含 `pip install`（`pypi.tuna.tsinghua.edu.cn`），
前端 `Dockerfile` 内含 `npm install`（`registry.npmmirror.com`）。
仅导入基础镜像后在内网 `docker compose build` 仍会失败，**必须在外网构建后 `docker save` 导出，
内网 `docker load` 后以 `up -d --no-build` 启动**。

**修复**

- 补齐 `ruoyi-fastapi-backend/.dockerignore` 与 `ruoyi-fastapi-frontend/.dockerignore`（原先缺失）。
  构建上下文由**后端 495 MB → 11.5 MB、前端 789 MB → 3.1 MB**。
  除效率外还有正确性意义：Windows 下创建的 `.venv`（453 MB）与 `node_modules`（622 MB）
  含平台专有二进制，拷入 Linux 镜像后不可用（前端会因缺少 `@esbuild/win32-x64` 等原生模块报错）。

**验证**

- 导出脚本：`bash -n` 语法通过；实跑在「镜像缺失」处正确 fail-fast（退出码 1）；
  未知参数退出码 2。
- 打包往返流程用 `FROM scratch` 最小镜像实测通过：
  `build → docker save → gzip -9 → sha256sum -c (OK) → docker rmi → gunzip | docker load →`
  架构与内容一致。验证后镜像与临时文件已清理。
- 未验证：真实业务镜像的构建与导出 —— 本机 Docker 守护进程出口被阻断，
  `registry-1.docker.io` 不可达（而 `curl` 访问外网正常），无法拉取任何基础镜像。

### 部署配置修复：Docker 初始化缺业务数据 + 无持久化

**问题 1（严重，会导致部署后不可用）**：`docker-compose.my.yml` / `docker-compose.pg.yml`
只把基础模板挂载到 `/docker-entrypoint-initdb.d`，而应用启动时仅执行
`Base.metadata.create_all`（建表结构），**不插入任何业务数据**。业务数据全部来自 SQL 脚本，
因此照原配置部署的后果是：可以登录，但看不到「大货车管理」菜单，
`xiping_admin` / `truck_leader` 账号不存在，看板中队统计为空（缺少 9100 松阳大队）。

**问题 2**：compose 未声明任何数据卷，MySQL 数据、Redis 数据与上传文件（车辆照片）
均未持久化，重建容器即丢失。

**问题 3**：`.env.dockermy` 内含默认口令 `DB_PASSWORD='root'`、`MYSQL_ROOT_PASSWORD: root`；
且该文件会随 `Dockerfile.my` 的 `COPY . .` 打进镜像，仅改仓库文件无法生效。

**处置**：

1. 新增 `scripts/prepare-docker-init.ps1`：把「基础模板 → 业务初始化 → m4~m14 增量」共 13 个
   脚本按正确顺序复制到 `deploy/mysql-init/` 与 `deploy/pg-init/`，以 `01/02/03` 序号前缀
   固定执行顺序（MySQL/PG 官方镜像按文件名字母序执行）。`m6` 会清理上游演示账号与组织，
   故必须排在基础模板之后。
2. 两个 compose 文件的数据库服务改用该目录挂载（只读），并新增持久化卷
   `mysql-data` / `pg-data`、`redis-data`、`upload-data`（挂载到 `/app/vf_admin`，
   因为 `UploadSettings` 使用相对路径且**不可由环境变量覆盖**，容器内固定在该目录）。
3. 口令改为从 `--env-file .env.deploy` 注入（compose 变量必填校验），不再使用镜像内默认值。
4. 端口收敛：仅前端 `12580` 映射到宿主机，MySQL/PG、Redis 与后端改为仅容器内网访问，
   原配置会把 13306 / 16379 / 19099 暴露到宿主机。
5. `.gitignore` 忽略生成的 `deploy/*-init/` 与 `.env.deploy`（源脚本仍在
   `ruoyi-fastapi-backend/sql/`，避免重复入库）。

**验证**：

- 两个 compose 文件均通过 `docker compose config` 官方解析校验，挂载与端口符合预期。
- 用生成的 `deploy/mysql-init/` 按序灌入空库：**13/13 脚本执行成功**，业务数据齐全 ——
  组织架构 7（大队 + 6 中队）、业务字典类型 7、业务菜单 6、业务表 6、验收账号 3、
  业务角色 2 与 24 条菜单授权、预警规则 1（阈值 2/2）、GAT1400 配置 13，
  且 `truck_vehicle.plate_no` 为可空（M13 生效）。
- **未完成**：本机 Docker 守护进程出口被阻断（`registry-1.docker.io` 不可达，
  而 `curl` 访问外网正常），故未能实际构建镜像并起容器。上述为等价的脚本级验证，
  镜像构建与容器编排需在可访问镜像仓库的环境执行。

### 预警阈值调整（M14）：只对「一项设备都没装」的车辆预警

**变更前**：`level_one_threshold=2`、`level_two_threshold=1`
→ 由于判定为 `缺装数 >= 阈值`，**缺 1 项即触发二级预警**。

**变更后**：`level_one_threshold=2`、`level_two_threshold=2`
→ 缺装 2 项（一项都没装）= 一级预警；**缺 1 项不预警**。

应安装设备共 2 项（刹车辅助系统、360 全景影像），故两级阈值相同即表示当前业务
只保留一级预警；阈值机制与二级等级字典均保留，后续恢复分级只需调低 `level_two_threshold`。

**改动内容**：

1. 默认阈值改为 2/2：`truck_do.py` 列默认值、`warning_service.parse_rule` 兜底值。
2. MySQL / PostgreSQL 初始化模板与 `m4` 脚本的阈值插入值同步改为 2/2。
3. 新增 `sql/truck-platform-m14.mysql.sql` 与 `.pg.sql`：调整运行库阈值并重算存量车辆，
   可重复执行（MySQL 真机连续执行两次验证幂等）。
4. 测试更新为锁定新口径，同时**保留对两级判定机制的覆盖**
   （`test_two_level_grading_still_supported_by_thresholds` 用 3/1 验证仍可区分两级）。

**存量数据影响**（实测）：

| | 变更前 | 变更后 |
| --- | --- | --- |
| 一级预警 | 4 辆 | 5 辆 |
| 二级预警 | 1 辆 | 0 辆 |
| 无预警 | 1 辆 | 1 辆 |

其中一辆此前从未参与重算的车辆（缺装 0）在本次重算中被正确纳入统计。

**注意语义差异**：`supervision_flag`（重点监管）与 `warning_level`（预警等级）判定**相互独立** ——
只要存在缺装（`missing_device_count > 0`）即标重点监管。因此缺 1 项的车辆**不预警但仍标重点监管**，
预警列表按 `supervision_flag='1'` 过滤，会出现 `warningLevel=none` 的行。
如需两者严格一致，需调整 `TruckWarningDao.update_warning`。

### 软删释放唯一键（M13）

**问题**：`truck_owner.credit_code` / `id_card_no`、`truck_vehicle.(plate_no, plate_color)` /
`vin` 都是**唯一索引且不含 `del_flag`**。软删时只置 `del_flag='2'`、保留身份字段，
导致重建同一主体或车辆时被唯一约束拦下并报 `Duplicate entry`，用户表现为
「删掉的东西建不回来」。

**处置**：

1. 软删主体时同时清空 `credit_code` 与 `id_card_no`（`TruckOwnerDao.delete`）。
2. 软删车辆时同时清空 `plate_no` 与 `vin`（`TruckVehicleDao.soft_delete`）。
3. `truck_vehicle.plate_no` 由 `NOT NULL` 改为可空（已删除的车辆没有有效车牌），
   模型 `TruckVehicle.plate_no` 同步改为 `nullable=True`。
4. 新增增量脚本 `sql/truck-platform-m13.mysql.sql` 与 `sql/truck-platform-m13.pg.sql`：
   调整列定义并清理历史遗留（已软删记录的身份字段）。脚本可重复执行。

**设计取舍**：清空而非把 `del_flag` 并入唯一键，原因是
`(credit_code, del_flag)` 这类组合键无法阻止「多条 del_flag='0' 的相同信用代码」，
唯一性保障反而变弱；清空后 MySQL 允许多个 NULL，身份标识可安全复用，
而主体名称、车辆其余档案与操作日志仍保留完整审计痕迹。

**验证**：真机实测「创建 → 软删 → 用同一信用代码/车牌+车架号重建」均成功；
新增单元测试 `tests/truck/test_soft_delete_unique_key.py` 直接断言 UPDATE 的 SET 子句，
无需数据库即可锁定行为（此前该缺陷无测试覆盖）。

### 归属与数据范围规则定稿

1. 明确 `truck_owner.dept_id` 为「主体登记归属中队」，`truck_vehicle.dept_id` 为「车辆分管中队」，
   二者相互独立，挂靠车辆允许主体与车辆分管中队不同。
2. 主体「名下车辆」数量与明细改为该主体跨中队的全部在管车辆，不再按当前用户车辆权限收窄；
   按 `ownerId` 查询车辆时先校验主体可见性，避免借该参数越权。
3. 车辆列表补充 `deptName` 并改列名为「分管中队」，跨中队查看时可识别车辆归属。
4. 看板中队统计的企业数/个人数改为按车辆分管中队归集，与同行车辆数口径一致。
5. 主体列表、主体表单、车辆表单的字段标签与说明提示同步更新。
6. 新增单元测试 `test_owner_vehicle_count_covers_all_squads` 与 `tests/truck/test_vehicle_list_scope.py`。

### 既有缺陷修复

1. 部门选项接口 `/truck/vehicle/dept-options` 原先不返回中队所属的大队节点，
   导致前端 `handleTree` 组树为空、树形选择器无可选中队且选中后只显示部门 ID。
   现连同大队节点一起返回，前端递归剔除大队节点，车辆分管中队默认值改为空以强制显式选择。
2. 修复 E2E 中依赖旧标签「所属中队」的断言，改为按新标签「分管中队」并校验真实选择流程。
3. 补齐缺失的 PostgreSQL 增量脚本 `truck-platform-m4.pg.sql`、`m6.pg.sql`、`m7.pg.sql`、`m8.pg.sql`，
   此前 MySQL 有而 PostgreSQL 没有，导致 PostgreSQL 升级路径从 m4 起断裂。
4. 修复 `truck-platform-init.pg.sql` 对 PostgreSQL 模板中不存在的 `sys_dept.remark` 列的写入，
   该错误会让整个 PostgreSQL 初始化链路在第二步即失败。
5. 修复 `truck-platform-m12.pg.sql` 使用 `ON CONFLICT (config_key)` 报错的问题
   （PostgreSQL 模板的 `sys_config.config_key` 非唯一索引），改为 `WHERE NOT EXISTS`。
6. `truck-platform-m4.pg.sql` 显式插入 `rule_id=1` 后复位自增序列，避免后续新增预警规则主键冲突。

### PostgreSQL 真机验证

在 PostgreSQL 14.24 上执行「基础模板 + `init` + `m4`~`m12`」共 11 个脚本：全部成功，
二次执行同样成功（幂等）；已校验 6 张业务表、松阳大队及 6 个中队、7 类业务字典、1 条预警规则、
3 个验收账号、2 个业务角色、13 项 GAT1400 配置、过车记录表与对接状态表均正确。

### 交付质量修复

1. 修复 Ruff 检查未通过的两处问题（`owner_dao` C416、`test_owner_service` I001）。
2. 修复 E2E 通用页面用例硬编码 Cookie 域为 `localhost` 导致 `127.0.0.1` 下全部被重定向到登录页的问题，
   改为按 `Config.frontend_url` 推导；站点标题断言改为读取配置。
3. `LoginHelper` 增加登录令牌缓存，避免整套用例触发 `/login` 限流（12 次/60 秒）导致误报 429。
4. 修复 Windows 中文环境 GBK 编码问题：CLI 子进程输出与嵌套 CLI 调用固定 UTF-8 解码，
   后端日志文件 sink 固定 UTF-8，消除 `UnicodeDecodeError` 与日志乱码。
5. 新增 `ruoyi-fastapi-backend/requirements-dev.txt` 声明 `pytest` 与 `pytest-asyncio` 测试依赖。

## RuoYi-Vue3-FastAPI v1.9.0

### 项目依赖

前后端依赖均有升级，请升级依赖或重新创建环境。

### 新增功能

1.新增AI管理模块 ([#69](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/69))。
2.新增移动端模块 ([#73](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/73))。
3.新增多worker运行支持 ([#76](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/76))。
4.应用新增演示模式 ([#78](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/78))。

### BUG修复

1.修复代码生成controller模板删除接口query_db参数异常的问题 ([#63](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/63))。
2.修复登录接口response_model声明错误 ([#71](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/71))。
3.修复无法直接通过后端地址访问API文档的问题 ([#74](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/74))。
4.修复create_app重复执行的问题 ([#84](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/84))。

### 代码重构

1.移除对python3.9的支持 ([#67](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/67))。

### 代码优化

1.优化alembic处理表模型逻辑，避免无关表影响 ([#68](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/68))。
2.优化代码生成后端模板 ([#72](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/72))。
3.自动注册路由出错时抛出异常以便于调试 ([#79](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/79))。
4.优化部分页面字段tooltip说明 (#80)。
5.优化项目启动速度 ([#82](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/82))。
6.优化暗黑模式切换效果 ([#83](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/83))。
7.优化热重载模式或单worker下scheduler的任务状态同步机制 ([#85](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/85))。
8.优化防重提交间隔时间可自定义 ([#87](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/87))。
9.优化验证码计算结果为非负数 ([#88](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/88))。
10.优化ci测试稳定性 ([#90](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/90))。

## RuoYi-Vue3-FastAPI v1.8.1

### 新增功能

1.新增E2E测试 ([#57](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/57))。

### BUG修复

1.修复DictTag组件渲染异常的问题 ([#59](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/59))。

### 代码优化

1.优化数据权限依赖 ([#55](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/55))。
2.动态导入定时任务函数，移除eval ([#56](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/56))。
3.优化pg版本的docker compose配置文件 ([#61](https://github.com/insistence/RuoYi-Vue3-FastAPI/pull/61))。

## RuoYi-Vue3-FastAPI v1.8.0

### 项目依赖

#### 后端

1.后端依赖升级到最新版本，请升级依赖或重新创建环境。

### 新增功能

1.新增请求上下文管理类。
2.新增`PreAuthDependency`、`CurrentUserDependency`、`DataScopeDependency`、`DBSessionDependency`、`UserInterfaceAuthDependency`和`RoleInterfaceAuthDependency`依赖函数。
3.新增上下文清理中间件。
4.新增公共vo模块。
5.新增配置文档静态资源方法。
6.新增自动注册路由功能。
7.新增docker compose部署方式。
8.菜单导航设置支持纯顶部。

### BUG修复

1.修复单账号登录模式下强退功能失效的问题 [#52](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/52)。
2.确保ApschedulerJobs字段类型与apscheduler默认创建的表字段类型一致 [#53](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/53)。
3.修复磁盘存在异常时服务监控无法正常运行的问题。
4.移除代码生成表业务表外键，修复无法删除的问题。
5.修复固定头部时出现的导航栏偏移问题。
6.修复表单构建移除所有控件后切换路由回来空白问题。
7.修复代码生成v3模板时间控件between选择后清空报错问题。

### 代码重构

1.增强ruff规则，完善类型提示。
2.优化项目结构，新增common模块，原annotation、aspect、constant、enums模块移动至common模块下。
3.重构app与server设计。

### 代码优化

1.controller层全部使用新依赖项。
2.当前用户信息使用上下文变量。
3.分页模型改为使用公共vo模块的PageModel。
4.优化API文档的响应模型显示。
5.操作响应模型改为使用公共vo模块的CrudResponseModel。
6.优化API文档的接口描述信息。
7.登录/注册页面底部版权信息修改为读取配置。
8.优化生成代码下载的zip文件名。
9.优化表单构建关闭页签销毁复制插件。
10.行内表单默认设置固定宽度。
11.优化操作日志详细请求参数显示。
12.优化index页面标题读取配置。
13.优化字典组件数字类型值处理逻辑。
14.优化字典组件值宽松匹配。
15.默认固定头部。

## RuoYi-Vue3-FastAPI v1.7.1

### 项目依赖

1.后端依赖移除passlib，直接使用bcrypt。

### BUG修复

1.修复代码生成controller模板编辑接口异常生成字段的问题。
2.移除passlib直接使用bcrypt修复密码校验异常的问题 [#48](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/48) [#49](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/49)。

### 代码优化

1.代码生成do模板补充表描述。

## RuoYi-Vue3-FastAPI v1.7.0

### 项目依赖

1.前后端依赖升级，请升级依赖或重新创建环境。

### 新增功能

1.新增alembic支持。
2.文件&图片上传组件支持自定义地址&参数。
3.新增默认打包配置项。
4.显隐列组件支持全选/全不选。
5.添加页签openPage支持传递参数。
6.外链加载时遮罩信息提示。
7.上传组件新增拖动排序属性。
8.图片上传组件新增disabled属性。
9.代码生成列支持拖动排序。
10.新增用户默认初始化密码。
11.新增页签图标显示开关功能。
12.新增底部版权信息及开关。
13.用户归属部门新增清除。
14.用户导入新增验证提示。
15.菜单搜索支持键盘选择&悬浮主题背景。
16.新增apscheduler_jobs表对应sqlalchemy模型类。
17.初始密码支持自定义修改策略。
18.账号密码支持自定义更新周期。
19.注册账号设置默认密码最后更新时间。
20.显示列信息支持对象格式。

### BUG修复

1.修复logout接口未按照app_same_time_login配置项动态判断的问题 [#IBZZ1S](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/IBZZ1S)。
2.修复上传组件被多次引用拖动仅对第一个有效的问题。

### 代码优化

1.优化接口耗时计算。
2.优化启动信息显示。
3.优化前端处理路由函数代码。
4.登录页和注册页表头使用VITE_APP_BASE_API配置值。
5.优化角色禁用不允许分配。
6.优化富文本控制台警告异常。
7.优化checkbox废弃API。
8.优化导航栏显示昵称&设置。

### 代码重构

1.重构IP归属区域查询为异步调用。
2.调整do与sql使其相互适配以支持alembic。
3.富文本复制粘贴图片上传至url。

## RuoYi-Vue3-FastAPI v1.6.2

### 新增功能

1.文件上传组件新增disabled属性。
2.文件上传组件新增类型。

### BUG修复

1.修复日志管理时间查询报错 [#27](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/27)。
2.修复定时任务状态暂停时执行单次任务会触发cron表达式的问题 [#31](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/31)。
3.修复修改字典类型时获取dict_code异常的问题。
4.修复修改字典类型时字典数据更新时间异常的问题。
5.修复代码生成模板时间查询问题 [#28](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/28)。
6.修复用户导出缺失部门名称的问题。

### 代码优化

1.优化代码生成新增和编辑字段显示和渲染。
2.pagination更换成flex布局。
3.优化代码生成vue模板 [#23](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/23)。

## RuoYi-Vue3-FastAPI v1.6.1

### 项目依赖

#### 后端

1.新增sqlglot依赖

```bash
pip install sqlglot[rs]==26.6.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### BUG修复

1.引入sqlglot修复sql语句解析异常的问题。
2.修复代码生成字段唯一性校验dao层模板判断异常的问题。
3.引入泛型修复as_query和as_form装饰模型文档丢失的问题。
4.修复代码生成主子表vo模板可能缺失NotBlank的问题。

## RuoYi-Vue3-FastAPI v1.6.0

### 项目依赖

1.后端依赖升级到最新版本，请升级依赖或重新创建环境。

### 新增功能

1.新增代码生成功能，支持配置数据库表信息一键生成和下载前后端代码，需要重新执行sql文件，请先备份数据。
2.新增表单构建功能。
3.用户头像新增支持http(s)链接。
4.新增trace中间件强化日志链路追踪和响应头 [@y1ren](https://gitee.com/y1ren)。
5.用户管理支持分栏拖动。
6.菜单面包屑导航支持多层级显示。
7.白名单支持对通配符路径匹配。
8.支持开启暗黑模式。

### BUG修复

1.修复默认关闭Tags-Views时，内链页面打不开。
2.修复删除当前登录用户拦截失效的问题。
3.修复定时任务目标字符串规则校验不全的问题。
4.修复执行单次任务时会覆盖已启用任务的问题 [#IBEKD2](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/IBEKD2)。
5.修复个人中心特殊字符密码修改失败问题。

### 代码优化

1.优化导出方法。
2.参数键值更换为多行文本。
3.优化日志中操作方法显示。
4.优化日志装饰器获取核心参数的方式。
5.用户管理过滤掉已禁用部门。
6.优化TopNav内链菜单点击没有高亮。
7.ResponseUtil补充完整参数。

## RuoYi-Vue3-FastAPI v1.5.1

### 新增功能

1.定时任务新增支持调用异步函数。

### 代码优化

1.优化字典数组条件判断。
2.校检文件名是否包含特殊字符。
3.移除已弃用的log_decorator装饰器。

## RuoYi-Vue3-FastAPI v1.5.0

### 新增功能

1.新增对PostgreSQL数据库的支持。

### BUG修复

1.修复DictTag组件控制台抛异常的问题 [#IAYSVZ](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/IAYSVZ)。
2.修复登录日志导出文件名称错误的问题。

### 代码回滚

1.因fastapi查询参数模型底层存在bug，回滚查询参数模型声明方式为as_query。

### 代码优化

1.优化CamelCaseUtil和SnakeCaseUtil以兼容更多转换场景。
2.优化列表查询排序。
3.优化参数设置页面。
4.优化上传图片带域名时不增加前缀。

## RuoYi-Vue3-FastAPI v1.4.0

### 项目依赖

#### 后端

1.更新fastapi版本为0.115.0

```bash
pip install fastapi[all]==0.115.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 代码重构

1.基于fastapi 0.115.0版本新特性，直接使用pydantic模型接收查询参数和表单数据，移除原有as_query和as_form使用方式。

### BUG修复

1.修复角色管理service书写错误。

### 代码优化

1.优化前端登录请求方法。

## RuoYi-Vue3-FastAPI v1.3.3

### 项目依赖

#### 后端

1.更新pydantic-validation-decorator版本为0.1.4，修复了一些底层bug。

### BUG修复

1.修复在线用户模块条件查询无效的问题。

### 代码优化

1.优化在线用户模块前后端字段描述一致。
2.日志装饰器异常处理增加logger打印日志。

## RuoYi-Vue3-FastAPI v1.3.2

### 新增功能

1.新增gzip压缩中间件。

### BUG修复

1.修复分页函数计算has_next错误的问题 [#10](https://github.com/insistence/RuoYi-Vue3-FastAPI/issues/10)。
2.修复定时任务监听函数中事件没有job_id报错的问题。

### 代码优化

1.优化添加中间件函数注释。

## RuoYi-Vue3-FastAPI v1.3.1

### BUG修复

1.修复1.3.0版本采用新的异常处理机制后日志装饰器无法记录异常日志的问题。

### 代码优化

1.补充定时任务违规字符串。

## RuoYi-Vue3-FastAPI v1.3.0

### 项目依赖

1.前后端依赖均升级到最新版本，请升级依赖或重新创建环境。
2.使用`PyJWT`替换`python-jose`以解决一些安全性问题。

### 新增功能

1.新增字段校验装饰器，支持手动触发校验，已封装为`pydantic-validation-decorator`库。
2.各模块`service`层新增字段唯一性校验。
3.全局新增`ServiceException`自定义服务异常和`ServiceWarning`自定义服务警告，无需在接口中写大量的异常捕获。
4.菜单管理新增路由名称，请执行以下sql为数据库新增字段：

```sql
ALTER TABLE sys_menu ADD COLUMN route_name varchar(50) DEFAULT '';
```

5.新增`constant`常量配置及`enums`枚举类型配置。
6.新增`StringUtil`、`CronUtil`工具类。

### BUG修复

1.修复用户管理、角色管理、部门管理越权漏洞。
2.修复各模块`dao`层`status`、`del_flag`类型与数据库不一致的问题。
3.修复移动端左侧菜单无法显示的问题。
4.修复其他已知BUG。

### 代码重构

1.重构日志装饰器为`Log`，未来版本将删除`log_decorator`装饰器，请尽快迁移。
2.重构`RedisInitKeyConfig`为枚举类型，现在可通过以下方式获取对应的`key`和`remark`
`RedisInitKeyConfig.ACCESS_TOKEN.key`、`RedisInitKeyConfig.ACCESS_TOKEN.remark`。
3.重构数据权限逻辑，底层进行优化，使用方法与之前相同。

### 代码优化

1.引入`ruff`对后端代码进行格式化及检测修复，优化导入。
2.各模块基于`ServiceException`自定义服务异常和`ServiceWarning`自定义服务警告优化了异常处理逻辑。
3.各模块`vo`层使用`Field`声明字段。
4.优化API文档字段描述显示。

## RuoYi-Vue3-FastAPI v1.2.2

### BUG修复

1.修复删除定时任务时未移除调度中任务的问题。
2.修复菜单生成路由时组件条件判断错误的问题。

## RuoYi-Vue3-FastAPI v1.2.1

### BUG修复

1.修复各模块新增数据时创建时间记录异常的问题。
2.修复菜单挂载到根目录时路由加载异常等一系列相关问题。

### 代码及性能优化

1.修改代理localhost为127.0.0.1以适配部分设备解析localhost异常的问题。

## RuoYi-Vue3-FastAPI v1.2.0

### 重要说明

本次更新为 **_破坏性更新_** ，重构数据库orm为异步，代码改动很大，请谨慎升级。
1.原有的Session类型声明统一变更为AsyncSession。
2.service层和dao层的函数修改为异步函数，请使用await调用。
3.orm查询不再支持query，请使用select、update、delete等语句，具体使用方法请参考[https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html](https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html)。

### 项目依赖

#### 后端

1.增加asyncmy依赖用于支持orm异步操作mysql，请重新安装依赖

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple。
```

### 新增功能

1.新增SnakeCaseUtil工具类，将原CamelCaseUtil工具类的camel_to_snake函数迁移至SnakeCaseUtil工具类。

### BUG修复

1.修复用户管理模块重置用户密码时会异常重置用户岗位和角色的问题。
2.修复清空定时任务日志异常的问题。

## RuoYi-Vue3-FastAPI v1.1.3

### 新增功能

1.用户密码新增非法字符验证。

### BUG修复

1.修复通知公告列表查询前后端字段不一致的问题。
2.修复个人中心修改基本资料后端异常的问题。

## RuoYi-Vue3-FastAPI v1.1.2

### 新增功能

1.配置文件新增数据库连接池相关配置。

### BUG修复

1.修复个人中心修改密码后端异常的问题。

### 代码及性能优化

1.使用@lru_cache缓存ip归属区域查询结果，避免重复调用ip归属区域查询接口以优化性能。

## RuoYi-Vue3-FastAPI v1.1.1

### BUG修复

1.修复编辑定时任务时更新的信息未同步至scheduler的问题 [#I9EK56](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/I9EK56)。
2.修复编辑角色数据权限时后端异常的问题 [#I9ENQN](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/I9ENQN)。
3.修复菜单配置路由参数不生效的问题。
4.修复获取路由信息时菜单排序不生效的问题。
5.修复添加菜单时是否外链和是否缓存回显异常的问题。

## RuoYi-Vue3-FastAPI v1.1.0

### 新增功能

1.后端配置文件新增sqlalchemy日志开关配置。
2.后端配置文件新增IP归属区域查询开关配置。
3.后端配置文件新增账号同时登录开关配置。

### BUG修复

1.修复token本身过期时退出登录接口异常的问题 [#I9CBWT](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/I9CBWT)。
2.修复系统版本号或浏览器版本号无法获取时登录异常的问题 [#I9CYNM](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/I9CYNM)。

## RuoYi-Vue3-FastAPI v1.0.3

### 新增功能

1.账号密码登录新增IP黑名单校验。

### BUG修复

1.修复外链菜单无法打开的问题 [#I95KBK](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/I95KBK)。
2.修复添加和编辑菜单页面中是否缓存和是否外链字段回显异常的问题 [#I95KBK](https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/issues/I95KBK)。

## RuoYi-Vue3-FastAPI v1.0.2

### 新增功能

1.用户接口权限校验增加列表接收参数，实现同一接口支持多个权限标识校验。
2.新增按角色校验接口权限依赖

### BUG修复

1.修复用户管理和部门管理模块数据权限异常的问题。

### 代码及性能优化

1.调整参数设置、部门管理、字典管理、定时任务、日志管理、角色管理、菜单管理模块部分接口权限标识。

## RuoYi-Vue3-FastAPI v1.0.1

### 项目依赖

#### 后端

1.更新fastapi版本为0.109.1，修复一些安全性问题，命令：

```bash
pip install fastapi[all]==0.109.1 -i https://mirrors.aliyun.com/pypi/simple/
```

### 新增功能

1.日志管理模块新增字段排序查询。

## RuoYi-Vue3-FastAPI v1.0.0

RuoYi-Vue3-FastAPI第一个版本发布啦！
此版本功能如下：
1.用户管理：用户是系统操作者，该功能主要完成系统用户配置。
2.角色管理：角色菜单权限分配。
3.菜单管理：配置系统菜单，操作权限，按钮权限标识等。
4.部门管理：配置系统组织机构（公司、部门、小组）。
5.岗位管理：配置系统用户所属担任职务。
6.字典管理：对系统中经常使用的一些较为固定的数据进行维护。
7.参数管理：对系统动态配置常用参数。
8.通知公告：系统通知公告信息发布维护。
9.操作日志：系统正常操作日志记录和查询；系统异常信息日志记录和查询。
10.登录日志：系统登录日志记录查询包含登录异常。
11.在线用户：当前系统中活跃用户状态监控。
12.定时任务：在线（添加、修改、删除）任务调度包含执行结果日志。
13.服务监控：监视当前系统CPU、内存、磁盘、堆栈等相关信息。
14.缓存监控：对系统的缓存信息查询，命令统计等。
15.系统接口：根据业务代码自动生成相关的api接口文档。