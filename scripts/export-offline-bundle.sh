# Export the offline image bundle for air-gapped deployment (Bash, run on a networked host).
#
# Why: the Dockerfiles run `pip install` (pypi.tuna.tsinghua.edu.cn) and `npm install`
# (registry.npmmirror.com) during the build, so an air-gapped host cannot build the images
# even after the base images are imported. Build here, then ship the finished images and
# start them on site with `--no-build`.
#
# Usage:
#   bash scripts/export-offline-bundle.sh                 # MySQL bundle (default)
#   bash scripts/export-offline-bundle.sh --with-pg       # also export the PG bundle
#   bash scripts/export-offline-bundle.sh --with-build-base  # also export build-time base images
#
# Output (under dist/offline-bundle/):
#   truck-mysql-images.tar.gz(.sha256)
#   truck-pg-images.tar.gz(.sha256)              (with --with-pg)
#   truck-build-base-images.tar.gz(.sha256)      (with --with-build-base)
#   image-digests.txt
#   deploy/                                      (database init scripts)
#   docker-compose.*.yml, .env.deploy.example
#   offline-image-bundle.md                      (the runbook)

set -euo pipefail

WITH_PG=0
WITH_BUILD_BASE=0
for arg in "$@"; do
    case "$arg" in
        --with-pg) WITH_PG=1 ;;
        --with-build-base) WITH_BUILD_BASE=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

OUT="$PROJECT_ROOT/dist/offline-bundle"
IMAGES=(
    "ruoyi-backend-my:latest"
    "ruoyi-frontend:latest"
    "mysql:8.0"
    "redis:latest"
)
PG_IMAGES=("ruoyi-backend-pg:latest" "postgres:14")
BUILD_BASE_IMAGES=("python:3.10" "node:18-slim" "nginx:latest")

echo "==> project root: $PROJECT_ROOT"
rm -rf "$OUT"
mkdir -p "$OUT"

# ---------------------------------------------------------------- preconditions
echo "==> checking required images exist locally"
missing=0
for img in "${IMAGES[@]}"; do
    if ! docker image inspect "$img" >/dev/null 2>&1; then
        echo "    MISSING: $img" >&2
        missing=1
    fi
done
if [ "$WITH_PG" = "1" ]; then
    for img in "${PG_IMAGES[@]}"; do
        if ! docker image inspect "$img" >/dev/null 2>&1; then
            echo "    MISSING: $img" >&2
            missing=1
        fi
    done
fi
if [ "$missing" = "1" ]; then
    echo "" >&2
    echo "Build the images first, e.g.:" >&2
    echo "  docker compose -f docker-compose.my.yml build" >&2
    echo "  docker compose -f docker-compose.pg.yml build   # if --with-pg" >&2
    exit 1
fi

# ------------------------------------------------------- architecture guard
echo "==> image architecture"
ARCH_OK=1
for img in "${IMAGES[@]}"; do
    arch="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$img")"
    echo "    $img -> $arch"
    case "$arch" in
        linux/amd64) ;;
        *) ARCH_OK=0 ;;
    esac
done
if [ "$ARCH_OK" = "0" ]; then
    echo "    WARNING: not all images are linux/amd64." >&2
    echo "    An x86_64 target will fail with 'exec format error'." >&2
    echo "    Rebuild with: docker buildx build --platform linux/amd64 ..." >&2
fi

# ------------------------------------------------------------- digests record
echo "==> recording image digests"
{
    echo "# image digests recorded at $(date -Iseconds)"
    echo "# host: $(uname -srm)"
    for img in "${IMAGES[@]}" "${PG_IMAGES[@]}" "${BUILD_BASE_IMAGES[@]}"; do
        if docker image inspect "$img" >/dev/null 2>&1; then
            digest="$(docker image inspect --format '{{if .RepoDigests}}{{index .RepoDigests 0}}{{else}}(no digest; built locally){{end}}' "$img")"
            size="$(docker image inspect --format '{{.Size}}' "$img")"
            arch="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$img")"
            printf '%-32s %-14s %12s  %s\n' "$img" "$arch" "$size" "$digest"
        fi
    done
} > "$OUT/image-digests.txt"
cat "$OUT/image-digests.txt"

# ------------------------------------------------------------------- export
save_and_hash() {
    local name="$1"; shift
    echo "==> exporting $name.tar.gz"
    docker save -o "$OUT/$name.tar" "$@"
    gzip -9 "$OUT/$name.tar"
    ( cd "$OUT" && sha256sum "$name.tar.gz" > "$name.tar.gz.sha256" )
    ls -lh "$OUT/$name.tar.gz" | awk '{print "    "$5"  "$9}'
}

save_and_hash "truck-mysql-images" "${IMAGES[@]}"

if [ "$WITH_PG" = "1" ]; then
    save_and_hash "truck-pg-images" "${PG_IMAGES[@]}"
fi

if [ "$WITH_BUILD_BASE" = "1" ]; then
    save_and_hash "truck-build-base-images" "${BUILD_BASE_IMAGES[@]}"
fi

# --------------------------------------------------- ship the deploy assets
echo "==> copying deployment assets"
mkdir -p "$OUT/deploy"
cp -r deploy/mysql-init "$OUT/deploy/" 2>/dev/null || true
if [ "$WITH_PG" = "1" ]; then
    cp -r deploy/pg-init "$OUT/deploy/" 2>/dev/null || true
fi
cp docker-compose.my.yml "$OUT/" 2>/dev/null || true
if [ "$WITH_PG" = "1" ]; then
    cp docker-compose.pg.yml "$OUT/" 2>/dev/null || true
fi
cp .env.deploy.example "$OUT/" 2>/dev/null || true
cp docs/offline-image-bundle.md "$OUT/" 2>/dev/null || true

# The generated init dirs are gitignored; make sure they are present and complete.
init_count="$(find "$OUT/deploy/mysql-init" -name '*.sql' 2>/dev/null | wc -l)"
echo "    deploy/mysql-init: $init_count sql files"
if [ "$init_count" != "13" ]; then
    echo "    WARNING: expected 13 init scripts; run scripts/prepare-docker-init.ps1 first." >&2
fi

# ------------------------------------------------------------------- summary
echo ""
echo "=============================================================="
echo " bundle ready: $OUT"
echo "=============================================================="
du -sh "$OUT"
echo ""
echo "On the air-gapped host:"
echo "  sha256sum -c truck-mysql-images.tar.gz.sha256"
echo "  gunzip -c truck-mysql-images.tar.gz | docker load"
echo "  cp .env.deploy.example .env && vi .env"
echo "  docker compose -f docker-compose.my.yml up -d --no-build"
echo ""
echo "REMINDER: use --no-build on site; a plain 'up -d' triggers pip/npm and will fail."
