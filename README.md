# 松阳大队大货车管理平台

面向松阳大队及西屏、古市、江南、象溪、大东坝、玉岩六个中队的大货车基础信息管理平台。系统提供辖区主体、车辆档案、Excel 台账导入导出、业务看板和安全设备缺装预警，并按大队管理员、中队管理员、领导三类角色控制菜单、操作和数据范围。

## 业务能力

- 首页业务看板：车辆来源、主体类型、重点监管、预警等级、中队分布和设备覆盖率。
- 主体管理：运输企业和个人车主档案，关联所属中队。
- 车辆档案：车辆基础信息、安全设备、归属主体、车辆照片和归属变更历史。
- 台账导入导出：兼容根目录真实 Excel 台账，限制单次 500 行，逐行返回真实错误信息。
- 重点监管预警：刹车辅助系统和 360 全景影像缺装计算、查询、下钻、重算和导出。
- 数据权限：中队管理员仅访问本中队数据，领导仅查询和导出，大队管理员拥有全量权限。

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

将项目放到服务器目录后，在项目根目录执行：

```bash
cd /opt/truck-platform

# MySQL 版本
sudo docker compose -f docker-compose.my.yml up -d --build

# 或 PostgreSQL 版本
sudo docker compose -f docker-compose.pg.yml up -d --build
```

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
| `DB_TYPE`、`DB_HOST`、`DB_PORT` | 数据库类型和连接信息 |
| `REDIS_HOST`、`REDIS_PORT` | Redis 连接信息 |
| `JWT_SECRET_KEY` | JWT 签名密钥，生产环境必须替换 |
| `TRANSPORT_CRYPTO_ENABLED`、`TRANSPORT_CRYPTO_MODE` | 传输层加解密开关和模式 |
| `UPLOAD_PATH`、`PRIVATE_UPLOAD_PATH` | 文件和车辆照片存储目录 |

传输层加解密的模式、密钥轮换和生产配置见 [`ruoyi-fastapi-backend/docs/transport_crypto_config.md`](ruoyi-fastapi-backend/docs/transport_crypto_config.md)。后端 CLI 命令见 [`ruoyi-fastapi-backend/docs/cli_usage.md`](ruoyi-fastapi-backend/docs/cli_usage.md)。

## 数据库初始化

### MySQL 8

新数据库按以下顺序执行：

1. `ruoyi-fastapi-backend/sql/ruoyi-fastapi.sql`
2. `ruoyi-fastapi-backend/sql/truck-platform-init.mysql.sql`

已有 M1-M4 业务库按版本继续执行 M5、M6 增量脚本：

```powershell
.\.runtime\mysql\mysql-8.0.42-winx64\bin\mysql.exe `
  --host=127.0.0.1 --port=3306 --user=root --password=mysqlroot `
  --database=ruoyi-fastapi --default-character-set=utf8mb4 `
  --execute="source ruoyi-fastapi-backend/sql/truck-platform-m5.mysql.sql"
```

随后执行 `ruoyi-fastapi-backend/sql/truck-platform-m6.mysql.sql`，完成用户与组织数据清理。全新数据库应优先执行完整初始化脚本，再按实际发布版本执行增量脚本。

### PostgreSQL

新数据库按以下顺序执行：

1. `ruoyi-fastapi-backend/sql/ruoyi-fastapi-pg.sql`
2. `ruoyi-fastapi-backend/sql/truck-platform-init.pg.sql`

M5 增量脚本为 `ruoyi-fastapi-backend/sql/truck-platform-m5.pg.sql`。业务脚本采用可重复执行写法。

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

默认等级：

- 缺失 2 项：一级预警 `level_one`
- 缺失 1 项：二级预警 `level_two`
- 无缺失：无预警 `none`

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
