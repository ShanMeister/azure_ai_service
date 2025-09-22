import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(scope="module")
def client():
    """
    測試用 FastAPI 同步 TestClient
    使用 pytest fixture 自動啟動 lifespan
    """
    with TestClient(app) as c:
        yield c