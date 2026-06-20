"""Tests for the backend health check infrastructure."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.src.main import app


@pytest.mark.asyncio
async def test_health_check_uses_unified_response() -> None:
    """GET /api/health returns the contract-aligned PyCore response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        trust_env=False,
    ) as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["message"] == "success"
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "smart-investment-research-api"
    assert isinstance(body["data"]["timestamp"], str)


@pytest.mark.asyncio
async def test_cors_allows_agent_and_user_gate_ports() -> None:
    """CORS permits both automated validation and user-gate frontend ports."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        trust_env=False,
    ) as client:
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5199",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5199"


@pytest.mark.asyncio
async def test_data_sources_status_contract() -> None:
    """GET /api/data-sources/status returns local fallback data source status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        trust_env=False,
    ) as client:
        response = await client.get("/api/data-sources/status")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    source_types = {item["type"] for item in data["mock_data"]}
    assert {"market", "financial", "announcement", "report", "knowledge"}.issubset(source_types)
    assert {"financial_live", "consensus_live", "report_live", "announcement_live"}.issubset(source_types)
    assert all(item["path"] for item in data["mock_data"])
    assert all(item["sample_count"] >= 0 for item in data["mock_data"])
    assert {item["status"] for item in data["mock_data"]}.issubset({"ready", "mocked", "missing"})
    assert data["rag"]["embedding_provider"]
    assert data["rag"]["rerank_provider"]
    assert data["rag"]["mode"] in {"mock", "semantic"}
    assert data["rag"]["status"] in {"mocked", "ready"}
    knowledge = next(item for item in data["mock_data"] if item["type"] == "knowledge")
    assert knowledge["path"]
    assert knowledge["sample_count"] >= 0


@pytest.mark.asyncio
async def test_config_status_contract_without_secret_values() -> None:
    """GET /api/config/status returns field names and missing status only."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        trust_env=False,
    ) as client:
        response = await client.get("/api/config/status")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    data = body["data"]
    assert len(data["models"]) == 4
    intent_llm = data["models"][0]
    output_llm = data["models"][1]
    assert intent_llm["name"] == "硅基流动 LLM / 意图识别"
    assert intent_llm["fields"] == ["LLM_INTENT_API_KEY", "LLM_INTENT_BASE_URL", "LLM_INTENT_MODEL"]
    assert output_llm["name"] == "硅基流动 LLM / 主输出"
    assert output_llm["fields"] == ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]
    for llm in (intent_llm, output_llm):
        assert llm["status"] in {"mocked", "ready"}
        if llm["status"] == "mocked":
            assert llm["missing_fields"]
        else:
            assert llm["missing_fields"] == []
    assert {prompt["agent"] for prompt in data["prompts"]} == {
        "master_agent",
        "hotspot_agent",
        "data_agent",
        "stock_agent",
        "quality_check",
    }
    assert data["compliance_rules"]["risk_tip_required"] is True
    assert data["compliance_rules"]["citation_required"] is True
    orchestration = data["orchestration"]
    assert orchestration["name"] == "langgraph"
    assert orchestration["status"] in {"ready", "blocked"}
    assert isinstance(orchestration["env"], str)
    assert isinstance(orchestration["missing_requirements"], list)
    rendered = str(data)
    assert "sk-" not in rendered
    assert "Bearer " not in rendered
