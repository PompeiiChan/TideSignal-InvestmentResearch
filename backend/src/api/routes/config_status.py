"""Data source and configuration status API routes."""

from typing import cast

from fastapi.responses import JSONResponse

from pycore.api import APIRouter
from pycore.api.responses import APIResponse, success_response

from ...models.config_status import ConfigStatusRead, DataSourceStatusRead
from ...services.config_status_service import ConfigStatusService

data_sources_router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])
config_router = APIRouter(prefix="/api/config", tags=["config"])


def _error(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": message, "data": None},
    )


@data_sources_router.get("/status", response_model=APIResponse[DataSourceStatusRead])
async def get_data_sources_status() -> APIResponse[DataSourceStatusRead] | JSONResponse:
    """Return local data source and RAG status."""
    try:
        data = ConfigStatusService().get_data_sources_status()
    except Exception:
        return _error("数据源状态读取失败", 500)
    return cast(APIResponse[DataSourceStatusRead], success_response(data=data.model_dump()))


@config_router.get("/status", response_model=APIResponse[ConfigStatusRead])
async def get_config_status() -> APIResponse[ConfigStatusRead] | JSONResponse:
    """Return model, prompt, and compliance status without exposing secrets."""
    try:
        data = ConfigStatusService().get_config_status()
    except Exception:
        return _error("配置状态读取失败", 500)
    return cast(APIResponse[ConfigStatusRead], success_response(data=data.model_dump()))
