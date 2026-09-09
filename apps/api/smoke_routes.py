"""Manual smoke script — requires a running PostgreSQL. Not part of pytest (run: uv run python smoke_routes.py)."""
import asyncio
from app.main import create_app
from fastapi.testclient import TestClient

app = create_app()
client = TestClient(app)

def test_routes():
    print("Testing routes...")
    routes = [
        "/health",
        "/api/countries",
        "/api/countries/USA",
        "/api/data/sources",
        "/api/indicators",
    ]
    for route in routes:
        try:
            response = client.get(route)
            print(f"{route}: {response.status_code}")
        except Exception as e:
            print(f"{route}: Error {e}")

if __name__ == "__main__":
    test_routes()
