import os


class Config:
    frontend_url = os.getenv('TEST_FRONTEND_URL', 'http://localhost:80').rstrip('/')
    backend_url = os.getenv('TEST_BACKEND_URL', 'http://localhost:9099').rstrip('/')
