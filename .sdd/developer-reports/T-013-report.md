# T-013 Developer 交付摘要

> **任务**：V1.1 全链路真实 AI 回归  
> **日期**：2026-06-16

## 变更

| 文件 | 说明 |
|------|------|
| `docs/startup.md` | V1.1 真实 AI 状态、外部服务 ready 表、T-009～T-013 报告索引；更新「未完成联调」清单 |
| `frontend/e2e/regression.mjs` | 真实 LLM 超时 180s（可 `E2E_ASSISTANT_TIMEOUT_MS` 覆盖）；composer 就绪等待；移动端窄屏走 data/settings 路径 |

## 质量门禁

- ruff / mypy / pytest：255 passed  
- frontend type-check / lint / build：通过  
- API 四类回归 + E2E 双视口：见 `test-T-013.md`
