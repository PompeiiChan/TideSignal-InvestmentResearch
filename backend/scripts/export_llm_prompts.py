#!/usr/bin/env python3
"""Export docs/agent/llm-system-prompts.md back to Python prompt modules."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MD_PATH = ROOT / "docs/agent/llm-system-prompts.md"
PROMPTS_DIR = ROOT / "backend/src/integrations/llm/prompts"

def _extract_fenced_block(text: str, start: int, fence: str) -> tuple[str, int] | None:
    """Read a fenced block; nested ``` lines must be indented (not column-0 closers)."""
    opener = f"```{fence}\n"
    if not text.startswith(opener, start):
        return None
    cursor = start + len(opener)
    lines: list[str] = []
    while cursor < len(text):
        line_end = text.find("\n", cursor)
        if line_end == -1:
            line_end = len(text)
        line = text[cursor:line_end]
        if line == "```":
            return "\n".join(lines), line_end + 1
        lines.append(line)
        cursor = line_end + 1 if line_end < len(text) else len(text)
    return None


def parse_sections(text: str) -> list[dict[str, str | bool]]:
    sections: list[dict[str, str | bool]] = []
    cursor = 0
    while True:
        yaml_start = text.find("```yaml\n", cursor)
        if yaml_start == -1:
            break
        yaml_result = _extract_fenced_block(text, yaml_start, "yaml")
        if yaml_result is None:
            break
        yaml_block, after_yaml = yaml_result
        prompt_marker = text.find("```prompt\n", after_yaml)
        if prompt_marker == -1:
            cursor = after_yaml
            continue
        if text[after_yaml:prompt_marker].strip():
            cursor = after_yaml
            continue
        prompt_result = _extract_fenced_block(text, prompt_marker, "prompt")
        if prompt_result is None:
            cursor = after_yaml
            continue
        prompt_block, cursor = prompt_result
        if "variable:" not in yaml_block:
            continue
        if yaml_block.strip().startswith("id: shared_system_time"):
            continue
        meta: dict[str, str | bool] = {}
        for line in yaml_block.strip().splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.lower() in {"true", "false"}:
                meta[key] = value.lower() == "true"
            else:
                meta[key] = value
        if meta.get("editable") is False:
            continue
        variable = str(meta.get("variable", "")).strip()
        if not variable or not prompt_block:
            continue
        sections.append(
            {
                **meta,
                "variable": variable,
                "prompt": normalize_prompt(prompt_block),
            }
        )
    return sections


def normalize_prompt(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("    "):
            lines.append(line[4:])
        else:
            lines.append(line)
    return "\n".join(lines).strip("\n")


def py_string_literal(content: str) -> str:
    if '"""' in content:
        raise ValueError("Prompt contains triple double quotes; escape manually.")
    return f'"""{content}"""'


def render_assignment(variable: str, content: str, *, wrap_markdown: bool) -> str:
    literal = py_string_literal(content)
    if wrap_markdown:
        return f"{variable} = append_response_markdown_format({literal})"
    return f"{variable} = {literal}"


FILE_HEADERS: dict[str, str] = {
    "backend/src/integrations/llm/prompts/intent.py": '''"""Intent recognition prompts for LangGraph orchestration."""

from __future__ import annotations

from ....services.system_time import SystemTimeContext
from ._shared import with_system_time

''',
    "backend/src/integrations/llm/prompts/slots.py": '''"""Slot extraction prompts for LangGraph orchestration."""

from __future__ import annotations

from ....services.system_time import SystemTimeContext
from ._shared import with_system_time

''',
    "backend/src/integrations/llm/prompts/clarification.py": '''"""Clarification response prompts for LangGraph orchestration."""

from __future__ import annotations

from ....services.system_time import SystemTimeContext
from ._shared import append_response_markdown_format, with_system_time

''',
    "backend/src/integrations/llm/prompts/fallback.py": '''"""Fallback response prompts for LangGraph orchestration."""

from __future__ import annotations

from ....services.system_time import SystemTimeContext
from ._shared import append_response_markdown_format, with_system_time

''',
    "backend/src/integrations/llm/prompts/agents/stock_analysis.py": '''"""Stock analysis agent prompts."""

from __future__ import annotations

from .....services.system_time import SystemTimeContext
from .._shared import with_system_time

''',
    "backend/src/integrations/llm/prompts/agents/data_query.py": '''"""Data query agent prompts."""

from __future__ import annotations

from .....services.system_time import SystemTimeContext
from .._shared import with_system_time

''',
    "backend/src/integrations/llm/prompts/agents/hotspot.py": '''"""Hotspot analysis agent prompts."""

from __future__ import annotations

from .....services.system_time import SystemTimeContext
from .._shared import with_system_time

''',
    "backend/src/integrations/llm/prompts/agents/document_qa.py": '''"""Document QA agent prompts."""

from __future__ import annotations

from .....services.system_time import SystemTimeContext
from .._shared import with_system_time

''',
}

FILE_FOOTERS: dict[str, str] = {
    "backend/src/integrations/llm/prompts/intent.py": '''

def intent_system_prompt(ctx: SystemTimeContext) -> str:
    """Build the LangGraph intent recognition system prompt."""
    return with_system_time(INTENT_SYSTEM_PROMPT_BASE, ctx)
''',
    "backend/src/integrations/llm/prompts/slots.py": '''

def slots_system_prompt(ctx: SystemTimeContext) -> str:
    """Build the LangGraph slot extraction system prompt."""
    return with_system_time(SLOTS_SYSTEM_PROMPT_BASE, ctx)
''',
    "backend/src/integrations/llm/prompts/clarification.py": '''

def clarification_system_prompt(ctx: SystemTimeContext) -> str:
    """Build the LangGraph clarification response system prompt."""
    return with_system_time(CLARIFICATION_SYSTEM_PROMPT_BASE, ctx)
''',
    "backend/src/integrations/llm/prompts/fallback.py": '''

def fallback_system_prompt(ctx: SystemTimeContext) -> str:
    return with_system_time(FALLBACK_SYSTEM_PROMPT_BASE, ctx)
''',
    "backend/src/integrations/llm/prompts/agents/stock_analysis.py": '''

def stock_analysis_agent_prompt(ctx: SystemTimeContext) -> str:
    return with_system_time(STOCK_ANALYSIS_AGENT_PROMPT_BASE, ctx)
''',
    "backend/src/integrations/llm/prompts/agents/data_query.py": '''

def data_query_agent_prompt(ctx: SystemTimeContext) -> str:
    return with_system_time(DATA_QUERY_AGENT_PROMPT_BASE, ctx)
''',
    "backend/src/integrations/llm/prompts/agents/hotspot.py": '''

def hotspot_agent_prompt(ctx: SystemTimeContext) -> str:
    return with_system_time(HOTSPOT_AGENT_PROMPT_BASE, ctx)
''',
    "backend/src/integrations/llm/prompts/agents/document_qa.py": '''

def document_qa_agent_prompt(ctx: SystemTimeContext) -> str:
    return with_system_time(DOCUMENT_QA_AGENT_PROMPT_BASE, ctx)
''',
}


def render_shared(sections: list[dict[str, str | bool]]) -> str:
    by_var = {str(s["variable"]): s for s in sections}
    parts = [
        '"""Shared prompt helpers and non-intent templates."""',
        "",
        "from __future__ import annotations",
        "",
        "from ....services.system_time import SystemTimeContext",
        "",
    ]
    legacy = by_var["LEGACY_INTENT_SYSTEM_PROMPT_BASE"]
    parts.append(
        render_assignment(
            "LEGACY_INTENT_SYSTEM_PROMPT_BASE",
            str(legacy["prompt"]),
            wrap_markdown=False,
        )
    )
    parts.append("")

    markdown_rules = by_var["RESPONSE_MARKDOWN_FORMAT_RULES"]
    parts.append(
        render_assignment(
            "RESPONSE_MARKDOWN_FORMAT_RULES",
            str(markdown_rules["prompt"]),
            wrap_markdown=False,
        )
    )
    parts.extend(
        [
            "",
            "",
            "def append_response_markdown_format(base: str) -> str:",
            '    """Append shared client-facing Markdown layout rules to a system prompt."""',
            '    return f"{base.rstrip()}\\n\\n---\\n\\n{RESPONSE_MARKDOWN_FORMAT_RULES}"',
            "",
        ]
    )

    for variable in [
        "ANSWER_STREAM_SYSTEM_PROMPT_BASE",
        "ANSWER_SYSTEM_PROMPT_BASE",
    ]:
        section = by_var[variable]
        parts.append(
            render_assignment(variable, str(section["prompt"]), wrap_markdown=True)
        )
        parts.append("")

    quality = by_var["QUALITY_SYSTEM_PROMPT_BASE"]
    parts.append(
        render_assignment(
            "QUALITY_SYSTEM_PROMPT_BASE",
            str(quality["prompt"]),
            wrap_markdown=False,
        )
    )
    parts.append("")

    parts.extend(
        [
            "def with_system_time(base: str, ctx: SystemTimeContext) -> str:",
            '    return f"{ctx.prompt_block()}\\n\\n{base}"',
            "",
            "",
            "def legacy_intent_system_prompt(ctx: SystemTimeContext) -> str:",
            "    return with_system_time(LEGACY_INTENT_SYSTEM_PROMPT_BASE, ctx)",
            "",
            "",
            "def answer_stream_system_prompt(ctx: SystemTimeContext) -> str:",
            "    return with_system_time(ANSWER_STREAM_SYSTEM_PROMPT_BASE, ctx)",
            "",
            "",
            "def answer_system_prompt(ctx: SystemTimeContext) -> str:",
            "    return with_system_time(ANSWER_SYSTEM_PROMPT_BASE, ctx)",
            "",
            "",
            "def quality_system_prompt(ctx: SystemTimeContext) -> str:",
            "    return with_system_time(QUALITY_SYSTEM_PROMPT_BASE, ctx)",
            "",
        ]
    )
    return "\n".join(parts)


def render_assembly(sections: list[dict[str, str | bool]]) -> str:
    by_var = {str(s["variable"]): s for s in sections}
    parts = [
        '"""Response assembly prompts for LangGraph orchestration."""',
        "",
        "from __future__ import annotations",
        "",
        "from ....services.system_time import SystemTimeContext",
        "from ._shared import append_response_markdown_format, with_system_time",
        "",
    ]

    default = by_var["ASSEMBLY_SYSTEM_PROMPT_BASE"]
    parts.append(
        render_assignment(
            "ASSEMBLY_SYSTEM_PROMPT_BASE",
            str(default["prompt"]),
            wrap_markdown=bool(default.get("appends_markdown_rules")),
        )
    )
    parts.append("")

    for variable in [
        "ASSEMBLY_STOCK_PROMPT_BASE",
        "ASSEMBLY_DATA_PROMPT_BASE",
        "ASSEMBLY_HOTSPOT_PROMPT_BASE",
    ]:
        section = by_var[variable]
        parts.append(render_assignment(variable, str(section["prompt"]), wrap_markdown=False))
        parts.append("")
        parts.append(
            f"{variable} = append_response_markdown_format({variable})"
        )
        parts.append("")

    parts.extend(
        [
            "",
            "def assembly_system_prompt(",
            "    ctx: SystemTimeContext,",
            "    *,",
            '    response_kind: str = "data",',
            ") -> str:",
            '    """Build response assembly system prompt by response kind."""',
            '    if response_kind == "stock":',
            "        return with_system_time(ASSEMBLY_STOCK_PROMPT_BASE, ctx)",
            '    if response_kind == "hotspot":',
            "        return with_system_time(ASSEMBLY_HOTSPOT_PROMPT_BASE, ctx)",
            '    if response_kind in {"data", "calculator"}:',
            "        return with_system_time(ASSEMBLY_DATA_PROMPT_BASE, ctx)",
            "    return with_system_time(ASSEMBLY_SYSTEM_PROMPT_BASE, ctx)",
            "",
        ]
    )
    return "\n".join(parts)


def main() -> None:
    text = MD_PATH.read_text(encoding="utf-8")
    sections = parse_sections(text)
    if len(sections) < 16:
        raise SystemExit(f"Expected at least 16 prompt sections, got {len(sections)}")

    by_file: dict[str, list[dict[str, str | bool]]] = {}
    for section in sections:
        source = str(section["source_file"])
        by_file.setdefault(source, []).append(section)

    for rel_path, file_sections in by_file.items():
        target = ROOT / rel_path
        if rel_path.endswith("_shared.py"):
            content = render_shared(file_sections)
        elif rel_path.endswith("assembly.py"):
            content = render_assembly(file_sections)
        else:
            if len(file_sections) != 1:
                raise SystemExit(f"{rel_path} expected 1 section, got {len(file_sections)}")
            section = file_sections[0]
            variable = str(section["variable"])
            header = FILE_HEADERS[rel_path]
            footer = FILE_FOOTERS[rel_path]
            assignment = render_assignment(
                variable,
                str(section["prompt"]),
                wrap_markdown=bool(section.get("appends_markdown_rules")),
            )
            content = header + assignment + footer

        target.write_text(content, encoding="utf-8")
        print(f"wrote {target.relative_to(ROOT)}")

    print(f"exported {len(sections)} prompts")


if __name__ == "__main__":
    main()
