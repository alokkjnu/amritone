"""Integration tests for authentication flow."""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from main import app
from config.database import create_all_tables, drop_all_tables


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="module")
async def client():
    await create_all_tables()
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    await drop_all_tables()


@pytest.mark.anyio
async def test_register_new_user(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "first_name": "Test",
        "last_name": "User",
        "email": "test.integration@example.com",
        "password": "Test@1234",
        "confirm_password": "Test@1234",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "user_id" in data


@pytest.mark.anyio
async def test_login_with_wrong_password(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "email": "test.integration@example.com",
        "password": "WrongPass",
    })
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_newsletter_subscribe(client: AsyncClient):
    resp = await client.post("/api/newsletter/subscribe", json={"email": "newsletter@test.com"})
    assert resp.status_code == 200
    assert "subscribed" in resp.json()["message"].lower()


@pytest.mark.anyio
async def test_homepage_loads(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert b"Amrit One" in resp.content


@pytest.mark.anyio
async def test_sitemap_returns_xml(client: AsyncClient):
    resp = await client.get("/sitemap.xml")
    assert resp.status_code == 200
    assert "xml" in resp.headers["content-type"]


@pytest.mark.anyio
async def test_robots_txt(client: AsyncClient):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    assert b"User-agent" in resp.content
