# 银河麒麟 V10 部署指南

目标环境：**银河麒麟 V10（x86_64，glibc 2.28）**，已装 Docker 与 **MySQL 8.0.45（宿主机部署）**，
**Redis 尚未部署**（随本编排一起部署）。

---

## 1. 与通用方案的三点差异

| 项 | 通用方案 | 麒麟方案（本文件） |
| --- | --- | --- |
| MySQL | 随 compose 起容器 | **复用宿主机已装的 8.0.45**，不起容器 |
| Redis | 随 compose 起容器 | 随本编排起容器（内网尚无 Redis） |
| 后端基础镜像 | `python:3.10`（Debian 12） | **`quay.io/pypa/manylinux_2_28_x86_64`**（AlmaLinux 8，glibc 2.28） |

### 为什么必须换基础镜像

`python:3.10` 基于 Debian 12（**glibc 2.36**）。在它里面构建时 pip 会选择
`manylinux_2_28` / `manylinux_2_34` 的 wheel（`asyncmy`、`Pillow`、`greenlet`
目前只发布 `manylinux_2_28` 及以上）。这些产物在麒麟 V10（glibc 2.28）上运行会直接报
`GLIBC_2.34 not found`，**镜像能构建成功但在目标机上起不来**。

`manylinux_2_28_x86_64` 是 PyPA 官方 manylinux 构建镜像，基于 AlmaLinux 8.10，
**glibc 恰好是 2.28**，并内置 CPython 3.10。与目标系统对齐后，pip 只会选中
`manylinux_2_28` 及以下的 wheel。

### 已完成的环境实测

在 `manylinux_2_28_x86_64`（glibc 2.28）中实测，**无需任何源码编译**：

| 验证项 | 结果 |
| --- | --- |
| `pip install -r requirements.txt`（35 项直接依赖 / 148 个包） | 全部安装成功 |
| `sqlglotrs`（Rust 核心） | 0.12.0，导入正常，sqlglot 32 dialects |
| `asyncmy`（MySQL 异步驱动） | 0.2.11，导入正常 |
| `Pillow` / `pandas` / `bcrypt` / `psutil` / `cryptography` / `greenlet` | 均 wheel，导入正常 |
| `create_app()` | 成功，**220 条路由**（与开发环境一致） |
| `ruoyi` CLI 命令 | 已生成，`--help` 正常 |

### 网络拓扑

后端与前端使用 `network_mode: host`，因此：

- 后端经 **`127.0.0.1:3306`** 直连宿主机 MySQL，经 **`127.0.0.1:6379`** 访问 Redis 容器
  （Redis 端口绑定到宿主机回环）。
- 前端 nginx 经 **`127.0.0.1:9099`** 反代后端（见
  `ruoyi-fastapi-frontend/bin/nginx.dockerkylin.conf`），不使用容器服务名。
- 已实测确认：`host` 网络容器可访问宿主机回环服务，`bridge` 网络容器不可访问
  （对照组验证，排除误判）。

---

## 2. 外网机器：构建与导出

```bash
cd /opt/truck-platform

# 1) 生成数据库初始化脚本（13 个，按序）
bash -c 'pwsh -File scripts/prepare-docker-init.ps1'   # 有 pwsh 时
#   无 pwsh 时按 01-base -> 02-truck-init -> 03-m04..m14 手工复制到 deploy/mysql-init/

# 2) 构建镜像（注意：麒麟方案使用 Dockerfile.kylin 与 nginx.dockerkylin.conf）
docker compose -f docker-compose.kylin.yml build

# 3) 导出离线包
docker save -o truck-kylin-images.tar \
  ruoyi-backend-my:kylin ruoyi-frontend:latest redis:7.4.2
gzip -9 truck-kylin-images.tar
sha256sum truck-kylin-images.tar.gz > truck-kylin-images.tar.gz.sha256

# 4) 一并交付
#    docker-compose.kylin.yml
#    deploy/mysql-init/            （13 个 SQL）
#    .env.deploy.example
#    nginx.dockerkylin.conf / -8080.conf（已在仓库内）
```

> **架构检查**：`docker image inspect --format '{{.Os}}/{{.Architecture}}' ruoyi-backend-my:kylin`
> 必须是 `linux/amd64`。

> **基础镜像来源**：`quay.io/pypa/manylinux_2_28_x86_64`。若外网机器也无法访问 quay.io，
> 需从别处获取后 `docker load`，或改用同在 glibc 2.28 基线的
> `almalinux:8` + 自建 Python 3.10（改动更大，不推荐）。

---

## 3. 麒麟机器：导入与启动

### 3.1 前置检查

```bash
# 确认 Docker 与 compose
docker --version && docker compose version

# 确认宿主机 MySQL 在跑，且允许从本机连接
systemctl status mysqld 2>/dev/null | head -3
mysql -uroot -p -e "SELECT VERSION();"      # 期望 8.0.45

# 确认 80 端口是否已被占用（host 网络下 nginx 直接用宿主机 80）
ss -lntp | grep ':80 ' || echo "80 端口空闲"
```

若 80 端口已被占用（麒麟常自带 nginx/httpd），改用 8080 配置：

```bash
sed -i 's#nginx.dockerkylin.conf#nginx.dockerkylin-8080.conf#' docker-compose.kylin.yml
```

### 3.2 导入镜像

```bash
sha256sum -c truck-kylin-images.tar.gz.sha256
gunzip -c truck-kylin-images.tar.gz | docker load
```

### 3.3 配置密钥

```bash
cp .env.deploy.example .env
vi .env
```

需填写：

| 变量 | 说明 |
| --- | --- |
| `DB_PASSWORD` | **宿主机 MySQL 的口令**（与已部署实例一致） |
| `DB_USERNAME` | 默认 `root`，建议改为专用账号 |
| `DB_DATABASE` | 默认 `truck_bank` |
| `JWT_SECRET_KEY` | 随机长字符串：`python3 -c "import secrets;print(secrets.token_urlsafe(48))"` |
| `REDIS_PASSWORD` | 可留空；填写则 Redis 启用密码并要求同值 |

### 3.4 初始化数据库（**关键步骤，不可跳过**）

应用启动只建表结构，**不插入业务数据**。松阳大队与 6 个中队、业务字典、大货车管理菜单、
角色、验收账号、预警规则、GA/T1400 配置全部来自 SQL 脚本。

```bash
# 创建库（如尚未创建）
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS \`truck_bank\` DEFAULT CHARACTER SET utf8mb4;"

# 按序执行 13 个脚本
for f in $(ls deploy/mysql-init/*.sql | sort); do
  echo "==> $f"
  mysql -uroot -p --default-character-set=utf8mb4 truck_bank < "$f" || { echo "失败: $f"; break; }
done
```

> 若目标库是已有数据的实例，请先备份：
> `mysqldump -uroot -p --single-transaction ruoyi-fastapi | gzip > backup-$(date +%F).sql.gz`

### 3.5 启动

```bash
docker compose -f docker-compose.kylin.yml up -d --no-build
docker compose -f docker-compose.kylin.yml ps
docker compose -f docker-compose.kylin.yml logs -f --tail=80 ruoyi-backend-my
```

> **必须带 `--no-build`**：镜像内已装好依赖，而构建过程需要访问 PyPI / npm，
> 内网无法完成。漏掉该参数会触发重新构建并失败。

### 3.6 防火墙

```bash
# 按实际使用的防火墙工具执行其一
firewall-cmd --permanent --add-port=80/tcp && firewall-cmd --reload     # firewalld
ufw allow 80/tcp                                                        # ufw
```

仅需开放前端端口（80 或 8080）。MySQL 与 Redis 均只监听回环，不需开放。

---

## 4. 部署后必须校验

```bash
# 1) 业务数据是否初始化成功
mysql -uroot -p truck_bank -e "
SELECT '组织' n, COUNT(*) v FROM sys_dept WHERE dept_id BETWEEN 9100 AND 9106
UNION ALL SELECT '菜单', COUNT(*) FROM sys_menu WHERE menu_id IN (9000,9002,9003,9004,9044,9047)
UNION ALL SELECT '账号', COUNT(*) FROM sys_user WHERE user_name IN ('admin','xiping_admin','truck_leader')
UNION ALL SELECT '预警规则', COUNT(*) FROM truck_warning_rule
UNION ALL SELECT 'GAT1400', COUNT(*) FROM sys_config WHERE config_key LIKE 'gat1400.%';"
# 期望：组织 7、菜单 6、账号 3、预警规则 1、GAT1400 13

# 2) 后端是否连通 MySQL 与 Redis
docker logs ruoyi-backend-my 2>&1 | tail -30 | grep -iE 'error|fail|exception' || echo "无错误日志"

# 3) 接口连通性（后端直连）
curl -s -o /dev/null -w "  后端 :9099 -> %{http_code}\n" http://127.0.0.1:9099/docker-api/login

# 4) 前端页面
curl -s -o /dev/null -w "  前端 :80   -> %{http_code}\n" http://127.0.0.1/
```

浏览器访问 `http://<麒麟机器IP>/`，用 `admin` 登录（初始口令见 README「验收账号」）。
**登录后立即修改全部初始口令。**

---

## 5. 排障对照

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 后端日志 `GLIBC_2.34 not found` | 用了 `python:3.10` 而非 `Dockerfile.kylin` 构建 | 改用 `docker-compose.kylin.yml` 重新构建并导出 |
| `pip install ... connection timeout` / `npm ERR! network` | 漏了 `--no-build` | 加 `--no-build` |
| 后端连不上 MySQL | MySQL 仅监听 `127.0.0.1` 之外的地址，或口令不对 | 检查 `.env` 的 `DB_PASSWORD`；确认 `ss -lntp \| grep 3306` |
| 后端连不上 Redis | Redis 容器未起或密码不一致 | `docker logs ruoyi-redis`；核对 `REDIS_PASSWORD` |
| 前端 502 | 后端未起，或 nginx 未用 kylin 配置 | 确认 nginx 配置为 `nginx.dockerkylin.conf`（反代 `127.0.0.1:9099`） |
| 页面能开但接口 404 | 前端打包时的 `VITE_APP_BASE_API` 与 nginx 前缀不一致 | 二者都应为 `/docker-api` |
| 80 端口占用 | 宿主机已有 nginx/httpd | 换用 `nginx.dockerkylin-8080.conf` |
| 业务菜单为空 | 数据库脚本未执行 | 重跑 3.4，或确认 `deploy/mysql-init/` 的 13 个脚本都已执行 |

---

## 6. 已确认的兼容性结论

| 风险项 | 结论 |
| --- | --- |
| glibc 版本（最关键） | 基线镜像 glibc **2.28**，与麒麟 V10 一致；全部依赖有兼容 wheel，**无需编译** |
| 原生扩展 | `sqlglotrs` / `asyncmy` / `pillow` / `pandas` / `cryptography` 等均提供 `manylinux_2_17`～`2_28` wheel |
| 架构 | `linux/amd64`，与麒麟 x86_64 一致 |
| 宿主机 MySQL 连通 | `network_mode: host` 下可访问宿主机回环服务，**已用对照组实测确认** |
| 应用可运行性 | glibc 2.28 环境内 `create_app()` 成功，220 条路由，与开发环境一致 |
| **未验证** | 麒麟真机上的镜像构建与容器启动（本机无麒麟环境，且 Docker Hub 不可达） |

> 唯一仍需在真机确认的是「麒麟上 Docker 运行该镜像」这一步。建议先在一台麒麟机器上
> 走通 3.2～3.6，再把流程推广。
