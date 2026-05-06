import pytest

from services.chatbot.fastapi_app.routers.mcp import FetchUrlBody, mcp_fetch_url


@pytest.mark.asyncio
async def test_fetch_url_blocks_localhost():
    with pytest.raises(Exception) as exc:
        await mcp_fetch_url(FetchUrlBody(url="http://127.0.0.1/admin"))
    assert "unsafe" in str(exc.value).lower() or "blocked" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_fetch_url_blocks_metadata_ip():
    with pytest.raises(Exception) as exc:
        await mcp_fetch_url(FetchUrlBody(url="http://169.254.169.254/latest/meta-data"))
    assert "unsafe" in str(exc.value).lower() or "blocked" in str(exc.value).lower()
