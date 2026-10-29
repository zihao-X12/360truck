#!/usr/bin/env bash
# 安装 Redis（≥ 6.2），systemd 托管
#
# 适用：银河麒麟 V10 / openEuler（glibc 2.28）。
#       系统自带的 redis 若为 5.x/6.0，缺少 XAUTOCLAIM 命令，会导致日志聚合与
#       GA/T1400 通知消费持续报错，因此需要 6.2+。
#
# 两种模式自动选择：
#   A) 交付包内带了 deploy/redis/bin/redis-server  → 安装随包二进制（推荐）
#   B) 包内没有二进制                              → 检查系统已装 redis 版本并给出结论
#
# 用法（在交付包根目录，需 root）：
#   sudo bash deploy/redis/install-redis.sh
#   sudo bash deploy/redis/install-redis.sh --prefix /opt/truck-bank --port 6379
#
# 完成后验证：
#   systemctl status truck-bank-redis
#   /opt/truck-bank/redis/bin/redis-cli -p 6379 ping          # PONG
#   /opt/truck-bank/redis/bin/redis-cli -p 6379 info server | grep redis_version

set -euo pipefail

PREFIX=/opt/truck-bank
PORT=6379
REDIS_USER=redis
DATA_DIR=/var/lib/truck-bank-redis
MIN_VERSION=6.2

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --port)   PORT="$2";   shift 2 ;;
        -h|--help)
            sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "未知参数: $1" >&2; exit 2 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLED="$SCRIPT_DIR/bin/redis-server"

if [ "$(id -u)" -ne 0 ]; then
    echo "请用 root 运行（sudo bash $0）" >&2
    exit 1
fi

# 版本比较：$1 >= $2 返回 0
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

# ---------------------------------------------------------------- 模式 B
if [ ! -x "$BUNDLED" ]; then
    echo "==> 未发现随包 Redis 二进制（$BUNDLED）"
    if ! command -v redis-server >/dev/null 2>&1; then
        cat >&2 <<'EOF'
未发现随包二进制，系统也未安装 redis-server。

请任选其一：
  1) 从有网机器把 redis-server / redis-cli 二进制放到 deploy/redis/bin/ 后重跑本脚本
  2) 安装系统包并确认版本 >= 6.2：
       dnf install -y redis && redis-server --version
  3) 使用 Docker：
       docker run -d --name truck-redis --restart unless-stopped \
         -p 127.0.0.1:6379:6379 -v truck-redis-data:/data \
         redis:7.4.2 redis-server --appendonly yes
EOF
        exit 1
    fi
    SYS_VER="$(redis-server --version | grep -oE 'v=[0-9]+\.[0-9]+' | head -1 | cut -d= -f2)"
    echo "    系统 redis-server 版本: ${SYS_VER:-未知}"
    if ver_ge "${SYS_VER:-0}" "$MIN_VERSION"; then
        echo "    ✓ 已满足 >= $MIN_VERSION，无需随包二进制"
        systemctl enable --now redis 2>/dev/null || true
        redis-cli -p "$PORT" ping || true
        echo "完成（使用系统 redis）。"
        exit 0
    fi
    cat >&2 <<EOF
    ✗ 系统 redis 版本 ${SYS_VER:-未知} 低于 $MIN_VERSION，缺少 XAUTOCLAIM。
      会导致日志聚合与 GA/T1400 通知消费持续报错。请按上面的选项 1/3 处理。
EOF
    exit 1
fi

# ---------------------------------------------------------------- 模式 A
echo "==> 使用随包二进制：$BUNDLED"
"$BUNDLED" --version

echo "==> 停止可能存在的旧 Redis（避免端口冲突）"
if systemctl is-active --quiet redis 2>/dev/null; then
    echo "    检测到系统 redis 服务，正在停止并禁用（保留软件包，仅停用服务）"
    systemctl stop redis || true
    systemctl disable redis || true
fi

echo "==> 创建运行用户 $REDIS_USER（已存在则跳过）"
if ! id "$REDIS_USER" >/dev/null 2>&1; then
    useradd -r -s /sbin/nologin -d "$DATA_DIR" "$REDIS_USER"
    echo "    已创建"
else
    echo "    已存在"
fi

echo "==> 安装文件到 $PREFIX/redis"
mkdir -p "$PREFIX/redis/bin"
install -m 0755 "$BUNDLED" "$PREFIX/redis/bin/redis-server"
[ -x "$SCRIPT_DIR/bin/redis-cli" ] && install -m 0755 "$SCRIPT_DIR/bin/redis-cli" "$PREFIX/redis/bin/redis-cli"

sed "s/^port .*/port $PORT/" "$SCRIPT_DIR/redis.conf" > "$PREFIX/redis/redis.conf"
sed -i "s#^dir .*#dir $DATA_DIR#" "$PREFIX/redis/redis.conf"
chown -R root:root "$PREFIX/redis"
chmod 0640 "$PREFIX/redis/redis.conf"

echo "==> 准备数据目录 $DATA_DIR"
mkdir -p "$DATA_DIR"
chown -R "$REDIS_USER:$REDIS_USER" "$DATA_DIR"
chmod 0750 "$DATA_DIR"

# SELinux（麒麟可能启用）：放行非标准端口的绑定
if command -v getenforce >/dev/null 2>&1 && [ "$(getenforce)" != "Disabled" ]; then
    echo "==> 检测到 SELinux，尝试放行端口 $PORT 与数据目录"
    command -v semanage >/dev/null 2>&1 && \
        { semanage port -a -t redis_port_t -p tcp "$PORT" 2>/dev/null || \
          semanage port -m -t redis_port_t -p tcp "$PORT" 2>/dev/null || true; }
    command -v semanage >/dev/null 2>&1 && \
        { semanage fcontext -a -t redis_var_lib_t "$DATA_DIR(/.*)?" 2>/dev/null || true; restorecon -Rv "$DATA_DIR" >/dev/null 2>&1 || true; }
fi

echo "==> 安装 systemd 单元"
install -m 0644 "$SCRIPT_DIR/truck-bank-redis.service" /etc/systemd/system/truck-bank-redis.service
sed -i "s#/opt/truck-bank#$PREFIX#g" /etc/systemd/system/truck-bank-redis.service
systemctl daemon-reload
systemctl enable --now truck-bank-redis

echo "==> 等待就绪"
for i in $(seq 1 20); do
    if "$PREFIX/redis/bin/redis-cli" -p "$PORT" ping 2>/dev/null | grep -q PONG; then
        break
    fi
    sleep 1
done

echo "==> 校验"
"$PREFIX/redis/bin/redis-cli" -p "$PORT" ping
"$PREFIX/redis/bin/redis-cli" -p "$PORT" info server | grep -E 'redis_version|os:' || true

VER="$("$PREFIX/redis/bin/redis-cli" -p "$PORT" info server | grep -oE 'redis_version:[0-9.]+' | cut -d: -f2)"
echo "    版本: ${VER:-未知}"
case "${VER:-0}" in
    7.*|8.*|6.[2-9]*) echo "    ✓ 满足 >= 6.2（支持 XAUTOCLAIM）" ;;
    *) echo "    ⚠ 版本低于 6.2，日志聚合与 GA/T1400 通知消费会报 XAUTOCLAIM 错误" ;;
esac

cat <<EOF

安装完成。
  服务名    : truck-bank-redis
  配置      : $PREFIX/redis/redis.conf
  数据目录  : $DATA_DIR
  监听      : 127.0.0.1:$PORT

后续步骤：
  1) 若在 .env 中设置了 REDIS_PASSWORD，请在 redis.conf 中取消 requirepass 注释并设为同一口令，
     然后 systemctl restart truck-bank-redis
  2) 启动后端：docker compose -f docker-compose.backend-only.yml up -d --no-build
EOF
