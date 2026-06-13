"""Run the local development API server."""

import sys
from pathlib import Path

import uvicorn

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

def main() -> None:
    """Start uvicorn with the project settings."""
    from src.settings import get_settings

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    main()
