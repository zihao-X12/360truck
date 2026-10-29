# 离线镜像包清单（内网交付）

面向无法访问 Docker Hub 的公安内网环境。核心思路：**在有网机器上完成全部构建**，
把成品镜像与基础镜像一并导出，内网只需 `docker load` 后启动，**内网不执行任何构建**。

> 为什么必须这样做：`Dockerfile.my` / `Dockerfile.pg` 内含 `pip install`（依赖
> `pypi.tuna.tsinghua.edu.cn`），前端 `Dockerfile` 内含 `npm install`（依赖
> `registry.npmmirror.com`）。仅导入基础镜像后在内网 `docker compose build` 仍会因
> 拉取 PyPI / npm 包失败。**内网必须使用 `--no-build`。**

## 0. 快捷方式：用脚本一键完成导出

本清单的手工步骤已脚本化，**推荐直接使用**（脚本会做前置检查、架构告警、digest 记录、
打包压缩与校验和，并自动收集交付资产）：

```bash
# 有网机器，项目根目录
docker compose -f docker-compose.my.yml build      # 先构建
bash scripts/export-offline-bundle.sh              # 导出 MySQL 离线包

# 可选参数
bash scripts/export-offline-bundle.sh --with-pg            # 同时导出 PG 包
bash scripts/export-offline-bundle.sh --with-build-base    # 附带构建期基础镜像
```

产物位于 `dist/offline-bundle/`：镜像包（`.tar.gz` + `.sha256`）、`image-digests.txt`、
`deploy/mysql-init/`、compose 文件、`.env.deploy.example` 与本运行手册。

若需了解每步做了什么或脚本不适用，见下方手工步骤。

---

## 1. 镜像清单

共 6 个镜像：基础镜像 4 个 + 构建产物 2 个（后端按数据库二选一，或两者都带）。

| # | 镜像 | 来源 | 用途 | 必须 |
| --- | --- | --- | --- | --- |
| 1 | `python:3.10` | 构建 `Dockerfile.my` / `Dockerfile.pg` 的基础镜像 | 后端运行时 | 是（若内网不重建，可省略） |
| 2 | `node:18-slim` | 前端 `Dockerfile` 构建阶段 | 前端构建 | 是（若内网不重建，可省略） |
| 3 | `nginx:latest` | 前端 `Dockerfile` 运行阶段 | 前端运行时 | 是（若内网不重建，可省略） |
| 4 | `mysql:8.0` | `docker-compose.my.yml` | 数据库 | MySQL 版必带 |
| 5 | `postgres:14` | `docker-compose.pg.yml` | 数据库（兼容目标，不在交付范围） | 仅 PG 版 |
| 6 | `redis:latest` | 两个 compose | 缓存/会话 | 是 |
| 7 | `ruoyi-backend-my:latest` | 构建产物（后端 MySQL 版） | 后端服务 | MySQL 版必带 |
| 8 | `ruoyi-backend-pg:latest` | 构建产物（后端 PG 版） | 后端服务 | 仅 PG 版 |
| 9 | `ruoyi-frontend:latest` | 构建产物（前端） | 前端服务 | 是 |

**最小集合（MySQL 交付）**：`mysql:8.0`、`redis:latest`、`ruoyi-backend-my:latest`、`ruoyi-frontend:latest`
共 4 个。若内网不需要重新构建，`python` / `node` / `nginx` 三个基础镜像可省略
（成品镜像已包含其全部层）。

### ⚠️ 浮动标签风险

以下标签是**浮动**的，同一标签在不同时间拉取可能是不同内容，离线交付时必须先固定：

| 标签 | 风险 | 建议 |
| --- | --- | --- |
| `redis:latest` | 内容可变 | 改为具体版本，如 `redis:7.4.2` |
| `nginx:latest` | 内容可变 | 改为具体版本，如 `nginx:1.27.4` |
| `mysql:8.0` | 小版本浮动 | 固定为 `mysql:8.0.42` |
| `postgres:14` | 小版本浮动 | 固定为 `postgres:14.15` |
| `python:3.10` | 小版本浮动 | 固定为 `python:3.10.15` |
| `node:18-slim` | 小版本浮动 | 固定为 `node:18.20.4-slim` |

**固定方法（推荐用 digest，最严格）**：在有网机器上拉取后记录 digest，把 compose 与
Dockerfile 里的标签替换为 `镜像@sha256:...`：

```bash
docker image inspect --format '{{index .RepoDigests 0}}' mysql:8.0
# 输出示例：mysql@sha256:abcd.....
```

> 注意：Dockerfile 的 `FROM` 与 compose 的 `image:` 都要一起改，否则版本不一致。

---

## 2. 有网机器：构建与导出

### 2.1 准备与构建

```bash
cd /opt/truck-platform          # 项目根目录

# 首次构建前确认 .dockerignore 生效（可大幅缩小构建上下文）
#   后端 495MB -> 11.5MB，前端 789MB -> 3.1MB
# 若上下文仍很大，说明 .dockerignore 缺失或被改动

# 构建（MySQL 版）
docker compose -f docker-compose.my.yml build

# 如同时需要 PG 版
docker compose -f docker-compose.pg.yml build
```

### 2.2 记录镜像 digest（作为交付清单的一部分）

```bash
docker images --digests --format '{{.Repository}}:{{.Tag}}  {{.Digest}}  {{.Size}}' \
  | grep -E 'python|node|nginx|mysql|postgres|redis|ruoyi' | sort
```

把输出保存为 `image-digests.txt` 一并交付，便于内网核对是否与构建时完全一致。

### 2.3 导出镜像包

```bash
# 最小集合（MySQL 交付）：成品 + 运行期基础镜像
docker save -o truck-mysql-images.tar \
  ruoyi-backend-my:latest \
  ruoyi-frontend:latest \
  mysql:8.0 \
  redis:latest

# 若内网也需要重新构建，追加构建期基础镜像
docker save -o truck-build-base-images.tar \
  python:3.10 \
  node:18-slim \
  nginx:latest

# 如需 PG 版
docker save -o truck-pg-images.tar \
  ruoyi-backend-pg:latest \
  postgres:14
```

压紧并生成校验和：

```bash
gzip -9 truck-mysql-images.tar
sha256sum truck-mysql-images.tar.gz > truck-mysql-images.tar.gz.sha256
ls -lh truck-mysql-images.tar.gz*
```

### 2.4 打包交付物

除镜像包外，还需要：

| 交付物 | 说明 |
| --- | --- |
| `docker-compose.my.yml` | 已修复的编排文件（业务脚本挂载 + 持久化卷 + 端口收敛） |
| `deploy/mysql-init/` | **13 个初始化脚本**，由 `scripts/prepare-docker-init.ps1` 生成 |
| `.env.deploy.example` | 密钥模板，内网复制为 `.env` 后填写 |
| `image-digests.txt` | 镜像 digest 清单，用于核对 |
| 达梦相关文件 | **不纳入**，按已确认决定排除 `.env.dm` 与 `scripts/dm_*.py` |

> `deploy/mysql-init/` 必须一并交付：镜像不含业务数据，数据库初始化完全依赖这 13 个脚本。

---

## 3. 内网机器：导入与启动

### 3.1 校验并导入

```bash
sha256sum -c truck-mysql-images.tar.gz.sha256     # 校验完整性
gunzip -c truck-mysql-images.tar.gz | docker load
docker images | grep -E 'ruoyi|mysql|redis'       # 核对已导入
```

### 3.2 启动（务必 `--no-build`）

```bash
cd /opt/truck-platform

# 1. 准备密钥
cp .env.deploy.example .env
vi .env                                            # 改口令与 JWT 密钥

# 2. 启动（--no-build 是离线环境的关键，避免触发 pip/npm 联网）
docker compose -f docker-compose.my.yml up -d --no-build

# 3. 查看状态
docker compose -f docker-compose.my.yml ps
```

**常见错误对照**：

| 报错 | 原因 | 处理 |
| --- | --- | --- |
| `pip install ... Could not find a version` / 连接超时 | 使用了 `up -d`（默认会构建） | 改用 `--no-build` |
| `npm ERR! network` | 同上 | 改用 `--no-build` |
| `required variable MYSQL_ROOT_PASSWORD is missing` | 未创建 `.env` | `cp .env.deploy.example .env` 并填写 |
| `pull access denied` / `manifest unknown` | 镜像未导入或名称不一致 | 核对 `image-digests.txt` 与 `docker images` |

### 3.3 必须校验业务数据

```bash
# 用 .env 中的真实口令替换 <密码>
docker exec ruoyi-mysql mysql -uroot -p<密码> ruoyi-fastapi -e "
SELECT '组织' n, COUNT(*) v FROM sys_dept WHERE dept_id BETWEEN 9100 AND 9106
UNION ALL SELECT '菜单', COUNT(*) FROM sys_menu WHERE menu_id IN (9000,9002,9003,9004,9044,9047)
UNION ALL SELECT '账号', COUNT(*) FROM sys_user WHERE user_name IN ('admin','xiping_admin','truck_leader')
UNION ALL SELECT '预警规则', COUNT(*) FROM truck_warning_rule
UNION ALL SELECT 'GAT1400', COUNT(*) FROM sys_config WHERE config_key LIKE 'gat1400.%';"
```

期望：组织 `7`、菜单 `6`、账号 `3`、预警规则 `1`、GAT1400 `13`。

**若全为 0**：说明数据库初始化没执行。原因是数据卷非空（脚本只在卷为空时运行）。
执行 `docker compose -f docker-compose.my.yml down -v` 后重新 `up -d --no-build`。

### 3.4 防火墙

```bash
sudo ufw allow OpenSSH
sudo ufw allow 12580/tcp
sudo ufw enable
```

仅需开放 `12580`。compose 已把 MySQL/Redis/后端改为仅容器内网访问，不对外暴露端口。

---

## 4. 环境要求

| 项 | 要求 |
| --- | --- |
| Docker Engine | ≥ 20.10（需 `docker compose` v2 插件） |
| Docker Compose | v2（本清单在 **v2.40.3** 上实测校验通过；`up --no-build` 为 v2 通用选项） |
| 磁盘 | 镜像包压缩后约 1～2 GB；导入后含数据卷建议预留 ≥ 20 GB |
| 内存 | 建议 ≥ 4 GB（MySQL + Redis + 后端 + Nginx 四个容器） |
| CPU | x86_64（镜像架构必须与构建机一致，见下） |

> 体积随基础镜像版本与依赖变化，上表为经验值。实际以脚本输出的 `du -sh` 为准。

### ⚠️ 架构一致性

`docker save` 导出的镜像**只包含构建机的架构**。若在有网机器上用 ARM（如 Apple M 系列、
部分鲲鹏服务器）构建，导入 x86_64 内网服务器后会报
`exec format error` 或 `no matching manifest`。

```bash
docker image inspect --format '{{.Os}}/{{.Architecture}}' ruoyi-backend-my:latest
# 必须输出 linux/amd64（内网服务器为 x86_64 时）
```

跨架构构建需使用 `docker buildx build --platform linux/amd64`，构建后同样用 `docker save` 导出。

---

## 5. 升级与回滚

### 升级（业务脚本有增量时）

```bash
# 1. 交付新镜像包并导入
gunzip -c truck-mysql-images-v1.1.tar.gz | docker load

# 2. 执行新增的增量脚本（例如 m15）
docker exec -i ruoyi-mysql mysql -uroot -p<密码> ruoyi-fastapi < sql/truck-platform-m15.mysql.sql

# 3. 重建容器（数据卷保留）
docker compose -f docker-compose.my.yml up -d --no-build
```

> 新增增量脚本**不会**自动执行——initdb 目录只在数据卷为空时运行。必须手工执行。

### 回滚

```bash
docker load < truck-mysql-images-v1.0.tar        # 载回旧镜像（标签相同会覆盖）
docker compose -f docker-compose.my.yml up -d --no-build --force-recreate
```

回滚前务必备份数据库：

```bash
docker exec ruoyi-mysql mysqldump -uroot -p<密码> --single-transaction ruoyi-fastapi \
  | gzip > backup-$(date +%F).sql.gz
```

---

## 6. 交付前检查清单

- [ ] 有网机器构建成功，`docker compose ps` 四个容器 `healthy`/`running`
- [ ] 已完成 3.3 的业务数据校验（组织 7 / 菜单 6 / 账号 3）
- [ ] `image-digests.txt` 已生成
- [ ] 镜像包已导出并生成 `.sha256`
- [ ] `deploy/mysql-init/` 13 个脚本随包交付
- [ ] `docker image inspect` 架构为 `linux/amd64`
- [ ] 达梦相关文件（`.env.dm`、`scripts/dm_*.py`）未打包
- [ ] 浮动标签已固定或已记录 digest
