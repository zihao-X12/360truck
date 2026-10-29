# 松阳大队大货车管理平台

面向大货车基础信息管理平台。系统提供辖区主体、车辆档案、Excel 台账导入导出、业务看板、安全设备缺装预警，以及 GA/T 1400 视图库对接与过车记录，并按大队管理员、中队管理员、领导三类角色控制菜单、操作和数据范围。

## 业务能力

- 首页业务看板：车辆来源、主体类型、重点监管、预警等级、中队分布和设备覆盖率。
- 主体管理：运输企业和个人车主按“所有人名称 + 主体类型”跨中队归集，查看权限范围内的名下车辆。
- 车辆档案：车辆基础信息、安全设备、归属主体、车辆照片和归属变更历史。
- 台账导入导出：兼容根目录真实 Excel 台账，限制单次 500 行，逐行返回真实错误信息。
- 重点监管预警：刹车辅助系统和 360 全景影像缺装计算、查询、下钻、重算和导出。
- GA/T 1400 视图库对接：向大华适配专网平台注册/保活/注销、过车记录订阅与自动续订、
  通知回调接收与解析落库去重，对接配置可在页面维护（密码加密存储、回显脱敏）。
  详见 [`docs/gat1400-integration-design.md`](docs/gat1400-integration-design.md)。
- 过车记录：按车牌、设备、时间范围查询卡口过车记录并导出，标识是否本平台车辆；
  数据权限按车辆分管中队隔离。
- 数据权限：中队管理员仅访问本中队数据，领导仅查询和导出，大队管理员拥有全量权限。

## 归属与数据范围规则

大货车多为挂靠性质，因此**车辆分管中队**与**主体登记归属中队**是两个独立概念，二者可以不同：

| 字段 | 含义 | 说明 |
| --- | --- | --- |
| `truck_vehicle.dept_id` | **分管中队** | 这辆车由哪个中队负责管理，由车辆自身确定，**不随所关联主体变化** |
| `truck_owner.dept_id` | **登记归属中队** | 主体的登记归属，仅用于登记统计与主体列表筛选，**不决定车辆分管** |
| `truck_vehicle.owner_id` | 归集维度 | 多辆车可归集到同一主体，允许跨中队 |

由此产生的行为：

1. **主体是归集维度，不是管辖依据**。一辆挂靠车可以「主体登记在西屏、车辆由古市分管」。
2. **主体档案跨中队可见**：主体登记在本中队，或本中队分管了该主体名下车辆，即可见此主体。
3. **「名下车辆」为该主体全部在管车辆（跨中队）**，并标注每辆车的分管中队。
4. **车辆本身仍严格按分管中队隔离**，中队管理员不能修改、删除、导出其他中队的车辆。
5. **看板按中队统计统一按「车辆分管中队」归集**，同一行的车辆数与主体数口径一致。
6. **个人车辆可不建主体**：只填「机动车所有人」即可建档，`owner_id` 允许为空，需要归集时再补建主体。

规则背景与取舍见 [`docs/reference/truck-platform-development-plan.md`](docs/reference/truck-platform-development-plan.md) 的 M6 章节。

## 技术与目录

| 目录 | 说明 |
| --- | --- |
| `ruoyi-fastapi-backend/` | FastAPI、SQLAlchemy asyncio 后端 |
| `ruoyi-fastapi-frontend/` | Vue 3、Vite、Element Plus 管理端 |
| `ruoyi-fastapi-test/` | pytest、Playwright 端到端测试 |
| `scripts/` | Windows 本地开发和测试脚本 |
| `docs/` | 部署及验收文档 |

开发数据库优先使用 MySQL 8，PostgreSQL 作为兼容目标；Redis 用于验证码、权限配置和导入错误文件缓存。

## 环境要求

- Windows PowerShell（本地脚本使用 PowerShell 编写）。
- Python 3.10 或更高版本。
- Node.js 18 或更高版本及 npm。
- MySQL 8 或 PostgreSQL 14，以及 Redis 6.2 或更高版本。
- 使用 Docker 部署时，需要 Docker Engine 和 Docker Compose v2。

首次手动运行前，请分别在后端和前端目录安装依赖：

```powershell
cd ruoyi-fastapi-backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..\ruoyi-fastapi-frontend
npm install
```

## 本地运行

当前仓库的本地开发环境已放在项目内 `.runtime/` 和后端 `.venv/`。在 PowerShell 中执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-dev-start.ps1
```

服务地址：

- Web：`http://127.0.0.1:5173/`
- API：`http://127.0.0.1:9099/`
- MySQL：`127.0.0.1:3306`
- Redis：`127.0.0.1:6379`

停止服务：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-dev-stop.ps1
```

本地脚本依赖项目内的 `.runtime/`、后端 `.venv/` 和前端 `node_modules/`。如果这些依赖尚未准备好，也可以分别启动服务：

```powershell
# 后端，执行目录为 ruoyi-fastapi-backend
cd ruoyi-fastapi-backend
.\.venv\Scripts\python.exe app.py --env=dev

# 前端，另开一个 PowerShell 窗口，执行目录为 ruoyi-fastapi-frontend
cd ruoyi-fastapi-frontend
npm.cmd run dev
```

## Docker 部署

### 银河麒麟 V10（当前交付目标）

目标环境为银河麒麟 V10（x86_64，glibc 2.28），MySQL 8.0.45 已部署在**宿主机**，Redis 随编排部署。
与通用方案有三点差异，**必须使用麒麟专用文件**：

| 项 | 通用方案 | 麒麟方案 |
| --- | --- | --- |
| 编排文件 | `docker-compose.my.yml` | **`docker-compose.kylin.yml`** |
| 后端镜像 | `Dockerfile.my`（`python:3.10`，glibc 2.36） | **`Dockerfile.kylin`**（`manylinux_2_28`，glibc 2.28） |
| nginx 配置 | `nginx.dockermy.conf` | **`nginx.dockerkylin.conf`**（反代 `127.0.0.1:9099`） |
| MySQL | compose 起容器 | 复用宿主机已装实例 |
| Redis | compose 起容器 | compose 起容器（端口仅绑回环） |

> **为什么必须换基础镜像**：在 `python:3.10`（Debian 12，glibc 2.36）里构建时，
> pip 会选中 `manylinux_2_28`/`2_34` 的 wheel，产物在麒麟（glibc 2.28）上会报
> `GLIBC_2.34 not found` —— 镜像能构建成功但在目标机起不来。
> 已实测：`manylinux_2_28_x86_64` 中全部依赖均有兼容 wheel，无需编译，
> `create_app()` 正常构建 220 条路由。

完整步骤（含宿主机 MySQL 复用、数据库初始化、排障对照与兼容性结论）见
[`docs/deploy-kylin-v10.md`](docs/deploy-kylin-v10.md)。

```bash
# 外网构建并导出
docker compose -f docker-compose.kylin.yml build
docker save -o truck-kylin-images.tar ruoyi-backend-my:kylin ruoyi-frontend:latest redis:7.4.2

# 麒麟上导入并启动
gunzip -c truck-kylin-images.tar.gz | docker load
cp .env.deploy.example .env && vi .env        # 填宿主机 MySQL 口令与 JWT 密钥
for f in $(ls deploy/mysql-init/*.sql | sort); do mysql -uroot -p ruoyi-fastapi < "$f"; done
docker compose -f docker-compose.kylin.yml up -d --no-build
```

### Ubuntu 服务器部署

以下命令适用于 Ubuntu 22.04/24.04。服务器需要安装 Docker Engine 和 Docker Compose v2，并确保当前账号可以执行 `docker` 命令：

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
docker --version
docker compose version
```

如果当前账号尚未加入 Docker 用户组，可先使用 `sudo docker compose` 执行命令；也可以加入用户组后重新登录：

```bash
sudo usermod -aG docker "$USER"
```

将项目放到服务器目录后，**必须先执行两个准备步骤**（否则部署出来没有业务数据，见下方说明）：

```bash
cd /opt/truck-platform

# 步骤 1：生成数据库初始化目录
#   MySQL 官方镜像/SQL 官方镜像按文件名字母序执行 /docker-entrypoint-initdb.d 下的脚本。
#   本步骤把「基础模板 + 业务初始化 + m4~m14 增量」按正确顺序复制到
#   deploy/mysql-init/ 与 deploy/pg-init/（带 01/02/03 序号前缀）。
pwsh -File scripts/prepare-docker-init.ps1
#   Linux 上无 pwsh 时，可按 01-base -> 02-truck-init -> 03-m04..m14 的顺序手工复制

# 步骤 2：创建 compose 变量文件（含密钥，已在 .gitignore 中，不要提交）
cp .env.deploy.example .env
#   然后编辑 .env，把 CHANGE_ME_* 占位值改成强口令与随机 JWT 密钥
vi .env

# 步骤 3：构建并启动
# MySQL 版本
sudo docker compose -f docker-compose.my.yml up -d --build

# 或 PostgreSQL 版本（兼容目标，不在交付范围）
sudo docker compose -f docker-compose.pg.yml up -d --build
```

> compose 会自动读取项目根目录的 `.env`，因此不需要每次追加 `--env-file` 参数。
> 若忘记创建 `.env`，compose 会直接报错并提示该怎么做（fail-fast），不会用默认弱口令启动 ——
> 这也是为了确保 `docker compose ps` / `down` 等常用命令不会因变量缺失而无法执行。

> **为什么必须先做步骤 1**：应用启动时只执行 `Base.metadata.create_all`（建表结构），
> **不会插入任何业务数据**。松阳大队及 6 个中队、业务字典、大货车管理菜单、角色、
> 验收账号、预警规则、GA/T1400 配置全部来自 SQL 脚本。若只挂载基础模板，
> 部署后可以登录但看不到业务菜单，看板中队统计也会为空。

**已知部署约束**：

- **离线内网需预置镜像**：`docker-compose.*.yml` 依赖 `mysql:8.0`、`postgres:14`、`redis:latest`、
  `node:18-slim`、`nginx:latest`、`python:3.10`。公安内网通常无法访问 Docker Hub；
  且由于构建过程需要 `pip install` / `npm install`，**内网无法自行构建镜像**，
  必须在外网构建后导出、内网导入，并以 `--no-build` 启动。
  完整清单、导出脚本与校验步骤见 [`docs/offline-image-bundle.md`](docs/offline-image-bundle.md)；
  一键导出：`bash scripts/export-offline-bundle.sh`。
- **持久化已配置**：`mysql-data` / `pg-data`、`redis-data`、`upload-data` 三个命名卷分别保存
  数据库、Redis 与上传文件（`/app/vf_admin`，含车辆照片）。**不要使用 `down -v`**，
  否则会连同数据卷一起删除。需要重新初始化数据库时才用 `down -v`。
- **端口仅开放前端**：compose 中只映射了前端 `12580`；MySQL/PG、Redis 与后端均不映射到宿主机，
  由容器内网互通。若需本机调试，请临时放开对应 `ports` 并限制来源 IP。
- **密钥不走镜像**：`.env.dockermy` / `.env.dockerpg` 会随 `COPY . .` 打进镜像，
  因此生产密钥通过项目根目录的 `.env`（compose 自动读取）注入覆盖，
  不要只改仓库里的 `.env.*` 文件。模板见 [`.env.deploy.example`](.env.deploy.example)。

部署完成后通过 `http://服务器IP:12580/` 访问系统。建议只对外开放 `12580`，不要将数据库和 Redis 端口暴露到公网；如果确需远程维护，应限制为可信 IP。Ubuntu 防火墙示例：

```bash
sudo ufw allow OpenSSH
sudo ufw allow 12580/tcp
sudo ufw enable
sudo ufw status
```

首次启动后检查容器和日志：

```bash
sudo docker compose -f docker-compose.my.yml ps
sudo docker compose -f docker-compose.my.yml logs -f --tail=100
```

**部署后必须校验业务数据是否初始化成功**（最容易出问题的一步）：

```bash
# 用 .env 中的真实口令替换下方的 <密码>
sudo docker exec ruoyi-mysql mysql -uroot -p<密码> ruoyi-fastapi -e "
SELECT '组织架构' AS item, COUNT(*) AS val FROM sys_dept WHERE dept_id BETWEEN 9100 AND 9106
UNION ALL SELECT '业务菜单', COUNT(*) FROM sys_menu WHERE menu_id IN (9000,9002,9003,9004,9044,9047)
UNION ALL SELECT '验收账号', COUNT(*) FROM sys_user WHERE user_name IN ('admin','xiping_admin','truck_leader')
UNION ALL SELECT '预警规则', COUNT(*) FROM truck_warning_rule
UNION ALL SELECT 'GAT1400配置', COUNT(*) FROM sys_config WHERE config_key LIKE 'gat1400.%';
"
```

期望结果：组织架构 `7`、业务菜单 `6`、验收账号 `3`、预警规则 `1`、GAT1400 配置 `13`。
若均为 0，说明 `deploy/mysql-init/` 未挂载或数据卷非空（脚本只在卷为空时执行），
执行 `sudo docker compose -f docker-compose.my.yml down -v` 后重新 `up`。

PostgreSQL 版本将上面命令中的 `docker-compose.my.yml` 替换为 `docker-compose.pg.yml`。更新代码后重新构建并启动：

```bash
sudo docker compose -f docker-compose.my.yml up -d --build
```

Compose 文件当前未配置数据库、Redis 和上传目录的持久化卷，仅适合开发、验收或已由运维平台统一管理存储的环境。正式部署前必须为数据库、Redis（如需持久化）和后端上传目录配置宿主机目录或 Docker volume，并纳入备份；不要通过 `down -v` 删除生产数据。

容器内置的 `.env.dockermy` / `.env.dockerpg` 含有默认账号密码、JWT 密钥和数据库密码。正式部署前应在镜像构建或 Compose 配置中覆盖这些值，并修改所有验收账号密码。

Docker 访问地址为 `http://127.0.0.1:12580/`，后端映射端口为 `19099`。数据库和 Redis 端口分别映射为 MySQL `13306`、PostgreSQL `15432` 和 Redis `16379`。停止对应环境：

```bash
docker compose -f docker-compose.my.yml down
# 或
docker compose -f docker-compose.pg.yml down
```

Compose 文件只自动导入基础系统 SQL。容器首次启动后，还需按[数据库初始化](#数据库初始化)中的顺序执行业务初始化和增量脚本；Linux 服务器上应通过数据库容器执行脚本，例如：

```bash
sudo docker exec -i ruoyi-mysql mysql -uroot -proot ruoyi-fastapi \
  < ruoyi-fastapi-backend/sql/truck-platform-init.mysql.sql
```

实际生产执行前请核对数据库容器名称、密码和目标库，增量脚本按发布顺序执行。

## 配置说明

后端按 `APP_ENV` 加载对应配置文件：`.env.dev`、`.env.dockermy`、`.env.dockerpg` 或 `.env.prod`。重点配置包括：

| 配置项 | 说明 |
| --- | --- |
| `DB_TYPE`、`DB_HOST`、`DB_PORT` | 数据库类型和连接信息（`mysql` / `postgresql` / `dm`，当前生产为 `mysql`） |
| `REDIS_HOST`、`REDIS_PORT` | Redis 连接信息 |
| `JWT_SECRET_KEY` | JWT 签名密钥，生产环境必须替换 |
| `TRANSPORT_CRYPTO_ENABLED`、`TRANSPORT_CRYPTO_MODE` | 传输层加解密开关和模式 |
| `UPLOAD_PATH`、`PRIVATE_UPLOAD_PATH` | 文件和车辆照片存储目录 |
| `DM_COMPATIBLE_MODE`、`DM_PARSE_TYPE` | 仅 `DB_TYPE='dm'` 时生效的达梦方言选项（当前未启用，见下） |

传输层加解密的模式、密钥轮换和生产配置见 [`ruoyi-fastapi-backend/docs/transport_crypto_config.md`](ruoyi-fastapi-backend/docs/transport_crypto_config.md)。后端 CLI 命令见 [`ruoyi-fastapi-backend/docs/cli_usage.md`](ruoyi-fastapi-backend/docs/cli_usage.md)。

## 数据库初始化

### MySQL 8

新数据库按以下顺序执行：

1. `ruoyi-fastapi-backend/sql/ruoyi-fastapi.sql`
2. `ruoyi-fastapi-backend/sql/truck-platform-init.mysql.sql`
3. 按发布顺序执行增量脚本 `truck-platform-m4.mysql.sql` 至 `truck-platform-m14.mysql.sql`

**完整的增量脚本清单（按顺序）**：`m4`、`m5`、`m6`、`m7`、`m8`、`m9`、`m10`、`m11`、`m12`、`m13`、`m14`。

已有业务库按版本继续执行增量脚本，例如：

```powershell
.\.runtime\mysql\mysql-8.0.42-winx64\bin\mysql.exe `
  --host=127.0.0.1 --port=3306 --user=root --password=mysqlroot `
  --database=truck_bank --default-character-set=utf8mb4 `
  --execute="source ruoyi-fastapi-backend/sql/truck-platform-m13.mysql.sql"
```

全新数据库应优先执行完整初始化脚本，再按实际发布版本执行增量脚本。
**当前生产与验证环境为 MySQL 8**，业务脚本采用可重复执行写法。

### PostgreSQL（兼容目标，不在交付范围）

> **交付定位（已确认）**：PostgreSQL **不在交付范围**，仅作为代码与 SQL 的兼容目标保留脚本，
> 不纳入发布验收。生产与验收环境统一使用 MySQL 8。保留脚本的目的是：一旦后续需要切换，
> 无需重新翻译 SQL。

新数据库按以下顺序执行：

1. `ruoyi-fastapi-backend/sql/ruoyi-fastapi-pg.sql`
2. `ruoyi-fastapi-backend/sql/truck-platform-init.pg.sql`
3. 按发布顺序执行增量脚本 `truck-platform-m4.pg.sql` 至 `truck-platform-m14.pg.sql`

**完整的增量脚本清单（按顺序）**：`m4`、`m5`、`m6`、`m7`、`m8`、`m9`、`m10`、`m11`、`m12`、`m13`、`m14`。
全部脚本已配齐 MySQL / PostgreSQL 两份，均采用可重复执行写法。

曾在 PostgreSQL 14.24 上完成一次链路演练（基础模板 + `init` + `m4`~`m12`，二次执行幂等），
说明脚本可用；但**该演练不构成交付验收依据**，PostgreSQL 仍未列为已验证的生产数据库。

> **注意**：PostgreSQL 模板的 `sys_dept` 没有 `remark` 列、`sys_config` 的 `config_key` 不是唯一索引
> （MySQL 模板两者都有）。编写增量脚本时不要对 `sys_dept` 写 `remark`，也不要用
> `ON CONFLICT (config_key)`，需改用 `WHERE NOT EXISTS`。

### 达梦（DM8）—— 暂缓，后续打包不纳入

**达梦暂缓实施，且后续打包时不纳入交付物。**

代码中保留了达梦接线（`DB_TYPE='dm'`、`dm+dmPython` 同步 URL、`DM_COMPATIBLE_MODE` /
`DM_PARSE_TYPE` 配置项）与三个验证脚本；由于当前不使用，打包或交付时**不应包含**
`.env.dm` 与 `scripts/dm_*.py`。

达梦官方异步方言 `dmAsync` 在 SQLAlchemy 2.0.x 上不可用，切换需把数据访问层整体改为同步
（约 96 个文件、1292 处 `await`）并重写整套测试，属于独立的较大工期。完整调研结论见
[`CHANGELOG.md`](CHANGELOG.md) 的「达梦数据库（DM8）适配 · 调研结论与处置」。


## 验收账号

| 账号 | 初始密码 | 部门 | 角色 | 权限 |
| --- | --- | --- | --- | --- |
| `admin` | `admin123` | 管理部门 | 大队管理员/系统管理员 | 全量数据和系统配置 |
| `xiping_admin` | `admin123` | 西屏中队 | 中队管理员 | 仅西屏中队数据，可维护和导入导出 |
| `truck_leader` | `admin123` | 松阳大队 | 领导权限 | 全量只读，可导出，不可新增、修改、删除或重算 |

非开发环境部署后必须立即修改全部初始密码，并按实际人员调整账号、部门和角色。

## 预警规则

默认应安装设备：

1. 刹车辅助系统 `brake_assist`
2. 360 全景影像 `panoramic_360`

默认等级（阈值 `truck_warning_rule.level_one_threshold=2`、`level_two_threshold=2`）：

- 缺失 2 项（**一项都没装**）：一级预警 `level_one`
- 缺失 1 项：不预警
- 无缺失：无预警 `none`

即当前业务**只保留一级预警**：安装任意一项设备即不预警。
阈值机制本身仍支持两级（`calculate_level` 按 `缺装数 >= 阈值` 判定），
两级阈值相同时二级自然不会触发；后续若需恢复分级，只需把 `level_two_threshold` 调低。

重点监管标志 `supervision_flag` 的判定与预警等级**相互独立**：只要存在缺装
（`missing_device_count > 0`）即置为 `1`，即缺 1 项的车辆不预警但仍标重点监管。
如需两者严格一致，需调整 `TruckWarningDao.update_warning`。

增量脚本 `truck-platform-m14.*.sql` 负责把已在运行的库调整到该口径并重算存量车辆。

转出、报废和已删除车辆不参与重算。规则保存在 `truck_warning_rule`，当前版本暂不提供规则配置页面。

## 测试与构建

后端业务测试和静态检查：

```powershell
cd ruoyi-fastapi-backend
.\.venv\Scripts\python.exe -m ruff check module_truck tests\truck
.\.venv\Scripts\python.exe -m unittest discover -s tests\truck -p 'test_*.py' -v
```

前端生产构建：

```powershell
cd ruoyi-fastapi-frontend
npm.cmd run build:prod
```

首次运行大货车 Playwright E2E：

```powershell
cd ruoyi-fastapi-test
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\local-e2e-test.ps1
```

E2E 脚本会暂时关闭 Redis 中的登录验证码配置，测试结束后恢复原值。

三角色数据与操作权限回归：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\local-permission-test.ps1
```

权限脚本会创建两辆临时车辆，验证完成后自动清理，并恢复原验证码配置。

## 部署要点

1. 生产环境必须通过环境变量或独立配置文件覆盖数据库、Redis、JWT 和文件存储配置。
2. 前端生产包由 `npm.cmd run build:prod` 生成在 `ruoyi-fastapi-frontend/dist/`。
3. Nginx 将 `/dev-api` 代理到后端 `9099`；上传和导出接口应配置足够的请求体及超时时间。
4. 初始化脚本使用 UTF-8，MySQL 客户端应指定 `--default-character-set=utf8mb4`。
5. 车辆照片复用文件管理模块，部署时需持久化上传目录并配置备份。
6. PostgreSQL 为兼容目标，正式切换前仍需在目标版本执行完整回归。

## 常见问题

### 页面能打开但接口 404

浏览器通过前端代理访问 `/dev-api`。直接访问本地后端 `9099` 时接口路径不带 `/dev-api`，例如 `/truck/vehicle/list`。

### 新菜单未出现

确认已执行最新业务 SQL，随后退出并重新登录。若仍未出现，重启后端和 Redis 以刷新菜单及权限缓存。

### 登录提示验证码错误

正常登录需填写页面验证码。自动化测试使用 `scripts/local-e2e-test.ps1` 临时关闭验证码，不应在生产环境永久关闭。

### Excel 导入失败

仅支持 `.xlsx`，单次最多 500 行。下载错误明细查看工作表、原始行号、字段值和真实错误原因；错误文件在 Redis 中保留 30 分钟。

### 中队管理员看到了其他中队数据

检查用户是否绑定到正确中队、是否只分配 `truck_squad_admin` 角色，以及该角色 `data_scope` 是否为 `3`（本部门数据）。

## 验收

交付验收步骤见 [`docs/truck-platform-acceptance.md`](docs/truck-platform-acceptance.md)。
