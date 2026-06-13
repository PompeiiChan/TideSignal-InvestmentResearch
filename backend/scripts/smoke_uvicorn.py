"""Start uvicorn briefly, call /api/health, then exit."""

import asyncio
import sys
from pathlib import Path

import httpx
import uvicorn

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

async def main() -> None:
    """Run a short live-server smoke check."""
    from src.main import app
    from src.settings import get_settings

    settings = get_settings()
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level="warning",
        lifespan="on",
    )
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    while not server.started:
        await asyncio.sleep(0.05)

    async with httpx.AsyncClient(trust_env=False) as client:
        response = await client.get(f"http://{settings.host}:{settings.port}/api/health")
        response.raise_for_status()
        print(response.json())

    server.should_exit = True
    await server_task


if __name__ == "__main__":
    asyncio.run(main())
