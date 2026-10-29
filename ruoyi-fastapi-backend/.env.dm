## 达梦数据库验证配置（仅供 scripts/dm_*.py 方言与 DDL 体检使用）
## 不参与生产部署；生产达梦连接信息请配置到 .env.prod。
## 本机验证：可用 docker 起达梦容器后，在运行脚本时用 DM_HOST/DM_PORT/DM_PASSWORD 环境变量覆盖。
DB_TYPE = 'dm'
DB_HOST = '127.0.0.1'
DB_PORT = 5236
DB_USERNAME = 'SYSDBA'
DB_PASSWORD = ''
DB_DATABASE = ''
DB_ECHO = false
DM_COMPATIBLE_MODE = 'DM'
DM_PARSE_TYPE = ''
