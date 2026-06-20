# TideSignal Demo — backend API (Railway)
FROM python:3.13-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY pycore ./pycore
COPY backend ./backend

# 知识库与 mock 数据随 backend/ 目录一并 COPY（RAG / 问数降级）

RUN pip install --no-cache-dir \
    "fastapi>=0.104.0" \
    "uvicorn[standard]>=0.24.0" \
    "pydantic>=2.4.0" \
    "pydantic-settings>=2.0.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "aiosqlite>=0.19.0" \
    "httpx>=0.25.0" \
    "python-dotenv>=1.0.0" \
    "pyyaml>=6.0.0" \
    "langgraph>=0.2.0" \
    "langchain-core>=0.3.0" \
    "requests>=2.31.0"

ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8080

WORKDIR /app/backend
EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
