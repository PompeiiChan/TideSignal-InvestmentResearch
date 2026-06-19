# T-024 知识库财报扩容入库报告

- 生成时间（UTC）：2026-06-19T14:06:56.746330+00:00
- 模式：refresh
- 随机种子：20260612
- 处理数量：50
- 成功：50
- 失败：0

## 期数抽样

- `300007` 汉威科技: sections=4 annual=3 interim=1 periods=20260331,20251231,20241231,20231231
- `300014` 亿纬锂能: sections=4 annual=3 interim=1 periods=20260331,20251231,20241231,20231231
- `300015` 爱尔眼科: sections=4 annual=3 interim=1 periods=20260331,20251231,20241231,20231231
- `300019` 硅宝科技: sections=4 annual=3 interim=1 periods=20260331,20251231,20241231,20231231
- `300023` 宝德退: sections=4 annual=3 interim=1 periods=20250630,20251231,20241231,20231231
- `300030` 阳普医疗: sections=4 annual=3 interim=1 periods=20260331,20251231,20241231,20231231
- `300033` 同花顺: sections=4 annual=3 interim=1 periods=20260331,20251231,20241231,20231231
- `300048` 合康新能: sections=4 annual=3 interim=1 periods=20260331,20251231,20241231,20231231

## 样本 doc_id

- `300007` 汉威科技: q1_300007_2026, ann_300007_2025, ann_300007_2024, ann_300007_2023
- `300014` 亿纬锂能: q1_300014_2026, ann_300014_2025, ann_300014_2024, ann_300014_2023
- `300015` 爱尔眼科: q1_300015_2026, ann_300015_2025, ann_300015_2024, ann_300015_2023
- `300019` 硅宝科技: q1_300019_2026, ann_300019_2025, ann_300019_2024, ann_300019_2023
- `300023` 宝德退: q_300023_20250630, ann_300023_2025, ann_300023_2024, ann_300023_2023

## 检索冒烟 / pytest

............ssssss......                                                 [100%]
=============================== warnings summary ===============================
pycore/core/schema.py:13
  /Users/pompeiichan/Desktop/Workplace_investment_research/Projects_Repo/smart-investment-research/pycore/core/schema.py:13: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class Result(BaseModel, Generic[T]):

pycore/core/schema.py:79
  /Users/pompeiichan/Desktop/Workplace_investment_research/Projects_Repo/smart-investment-research/pycore/core/schema.py:79: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class Message(BaseModel):

pycore/core/config.py:20
  /Users/pompeiichan/Desktop/Workplace_investment_research/Projects_Repo/smart-investment-research/pycore/core/config.py:20: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class BaseSettings(BaseModel):

backend/tests/test_rag_service.py::test_count_markdown_files_matches_repository
  /Users/pompeiichan/Desktop/Workplace_investment_research/Projects_Repo/smart-investment-research/pycore/integrations/llm/base.py:175: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class LLMConfig(BaseModel):

backend/tests/test_rag_service.py::test_count_markdown_files_matches_repository
  /Users/pompeiichan/Desktop/Workplace_investment_research/Projects_Repo/smart-investment-research/pycore/integrations/db/base.py:11: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class DatabaseConfig(BaseModel):

backend/tests/test_rag_service.py::test_count_markdown_files_matches_repository
  /Users/pompeiichan/Desktop/Workplace_investment_research/Projects_Repo/smart-investment-research/pycore/integrations/cache/base.py:11: PydanticDeprecatedSince20: Support for class-based `config` is deprecated, use ConfigDict instead. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.13/migration/
    class CacheConfig(BaseModel):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
18 passed, 6 skipped, 6 warnings in 31.31s
