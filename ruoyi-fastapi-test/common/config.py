import os


class Config:
    frontend_url = os.getenv('TEST_FRONTEND_URL', 'http://localhost:80').rstrip('/')
    backend_url = os.getenv('TEST_BACKEND_URL', 'http://localhost:9099').rstrip('/')
    # 站点标题，与前端 VITE_APP_TITLE 保持一致；其他分支定制标题时可用环境变量覆盖
    app_title = os.getenv('TEST_APP_TITLE', '大货车管理平台')
