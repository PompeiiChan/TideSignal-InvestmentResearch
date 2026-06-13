"""Short health-check smoke test that exits automatically."""

import asyncio
import sys
from pathlib import Path

import httpx

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

async def main() -> None:
    """Call the ASGI app directly and print the health response."""
    from src.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        trust_env=False,
    ) as client:
        response = await client.get("/api/health")
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
