"""Generate PRD and ADR index documents from source markdown files.

Usage:
    python scripts/generate_index.py

Outputs:
    docs/_index/PRDS_INDEX.md
    docs/_index/ADRS_INDEX.md
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "docs" / "_index_config.yaml"
NOTICE = "NAO EDITAR MANUALMENTE - gerado por scripts/generate_index.py"
INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
STATUS_PATTERNS = (
    re.compile(r"^\s*[-*]\s*\*\*Status:?\*\*\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\s*\*\s+\*\*Status\*\*:\s*(.+?)\s*$", re.IGNORECASE),
    re.compile(r"^\|\s*\*\*Status\*\*\s*\|\s*(.+?)\s*\|?\s*$", re.IGNORECASE),
)
METADATA_BULLET_RE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*:?\s*(.+?)\s*$")
METADATA_TABLE_RE = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|?\s*$")


@dataclass(frozen=True)
class SectionConfig:
    name: str
    output: Path
    sources: tuple[Path, ...]


@dataclass(frozen=True)
class DocumentSummary:
    source: Path
    title: str
    status: str
    metadata: tuple[tuple[str, str], ...]
    summary_paragraphs: tuple[str, ...]


def _relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_index_config(config_path: Path = CONFIG_PATH) -> tuple[SectionConfig, ...]:
    """Parse the narrow YAML config used by the index generator."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    sections: list[SectionConfig] = []
    current_name: str | None = None
    current_output: Path | None = None
    current_sources: list[Path] = []
    in_sources = False

    for lineno, raw_line in enumerate(_read_text(config_path).splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        if indent == 0 and stripped.endswith(":"):
            if current_name is not None:
                sections.append(
                    _build_section(config_path, current_name, current_output, current_sources)
                )
            current_name = stripped[:-1]
            current_output = None
            current_sources = []
            in_sources = False
            continue

        if current_name is None:
            raise ValueError(f"{config_path}:{lineno}: value without section header")

        if indent == 2 and stripped.startswith("output:"):
            value = stripped.split(":", 1)[1].strip()
            if not value:
                raise ValueError(f"{config_path}:{lineno}: missing output path")
            current_output = PROJECT_ROOT / value
            in_sources = False
            continue

        if indent == 2 and stripped == "sources:":
            in_sources = True
            continue

        if indent == 4 and stripped.startswith("- "):
            if not in_sources:
                raise ValueError(f"{config_path}:{lineno}: source entry outside sources block")
            value = stripped[2:].strip()
            if not value:
                raise ValueError(f"{config_path}:{lineno}: empty source path")
            current_sources.append(PROJECT_ROOT / value)
            continue

        raise ValueError(f"{config_path}:{lineno}: unsupported config line: {raw_line}")

    if current_name is not None:
        sections.append(_build_section(config_path, current_name, current_output, current_sources))

    if not sections:
        raise ValueError(f"{config_path}: no sections found")

    return tuple(sections)


def _build_section(
    config_path: Path,
    name: str,
    output: Path | None,
    sources: list[Path],
) -> SectionConfig:
    if output is None:
        raise ValueError(f"{config_path}: section '{name}' missing output")
    if not sources:
        raise ValueError(f"{config_path}: section '{name}' has no sources")
    return SectionConfig(name=name, output=output, sources=tuple(sources))


def extract_document_summary(path: Path) -> DocumentSummary:
    """Extract title, status, metadata, and the first three prose paragraphs."""
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    text = _read_text(path)
    title = _extract_title(text, path)
    status = _extract_status(text)
    metadata = tuple(_extract_metadata(text))
    paragraphs = tuple(_extract_summary_paragraphs(text, limit=3))
    return DocumentSummary(
        source=path,
        title=title,
        status=status,
        metadata=metadata,
        summary_paragraphs=paragraphs,
    )


def _extract_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    raise ValueError(f"No level-1 title found in {path}")


def _extract_status(text: str) -> str:
    for line in text.splitlines():
        for pattern in STATUS_PATTERNS:
            match = pattern.match(line)
            if match:
                return match.group(1).strip().strip("|").strip().lstrip(":").strip()
    return "Unknown"


def _extract_metadata(text: str) -> list[tuple[str, str]]:
    metadata: list[tuple[str, str]] = []
    for line in _extract_metadata_lines(text):
        bullet_match = METADATA_BULLET_RE.match(line)
        if bullet_match:
            metadata.append(
                (
                    bullet_match.group(1).strip().rstrip(":"),
                    bullet_match.group(2).strip(),
                )
            )
            continue

        table_match = METADATA_TABLE_RE.match(line)
        if table_match:
            key = table_match.group(1).strip().rstrip(":")
            value = table_match.group(2).strip()
            if key.lower() != "status" or value != "---":
                metadata.append((key, value))
    return metadata


def _extract_metadata_lines(text: str) -> list[str]:
    lines = text.splitlines()
    metadata_lines: list[str] = []
    title_seen = False
    metadata_started = False
    in_metadata_section = False

    for raw_line in lines:
        stripped = raw_line.strip()
        if not title_seen:
            if stripped.startswith("# "):
                title_seen = True
            continue

        if stripped.startswith("## ") and "metadata" in stripped.lower():
            in_metadata_section = True
            continue

        bullet_match = METADATA_BULLET_RE.match(raw_line)
        table_match = METADATA_TABLE_RE.match(raw_line)

        if bullet_match or table_match:
            metadata_started = True
            metadata_lines.append(raw_line)
            continue

        if metadata_started and (not stripped or stripped.startswith("## ")):
            break

        if in_metadata_section and metadata_started:
            break

    return metadata_lines


def _extract_summary_paragraphs(text: str, limit: int) -> list[str]:
    paragraphs: list[str] = []
    block: list[str] = []
    in_code_block = False

    def flush_block() -> None:
        nonlocal block
        if not block:
            return
        candidate = " ".join(line.strip() for line in block).strip()
        block = []
        if not candidate:
            return
        if _is_summary_candidate(candidate):
            paragraphs.append(candidate)

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            flush_block()
            continue
        if in_code_block:
            continue

        if not stripped:
            flush_block()
            if len(paragraphs) >= limit:
                break
            continue

        if _is_structural_line(stripped):
            flush_block()
            continue

        block.append(stripped)

    flush_block()
    return paragraphs[:limit]


def _is_structural_line(line: str) -> bool:
    return (
        line.startswith("#")
        or line.startswith("|")
        or line.startswith("- ")
        or line.startswith("* ")
        or re.match(r"^\d+\.\s", line) is not None
    )


def _is_summary_candidate(paragraph: str) -> bool:
    if not paragraph:
        return False
    if paragraph.startswith(("```", "|", "-", "*")):
        return False
    return True


def _normalize_inline_links(text: str, source_path: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2).strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#", "/")):
            return match.group(0)

        normalized_target = target.split("#", 1)[0]
        anchor = ""
        if "#" in target:
            anchor = "#" + target.split("#", 1)[1]

        resolved = (source_path.parent / normalized_target).resolve()
        try:
            project_relative = "/" + _relative(resolved)
        except ValueError:
            return match.group(0)

        return f"[{label}]({project_relative}{anchor})"

    return INLINE_LINK_RE.sub(replace, text)


def render_index(section: SectionConfig, documents: tuple[DocumentSummary, ...]) -> str:
    """Render the generated index markdown for one section."""
    heading = f"{section.name.upper()}_INDEX"
    lines = [
        f"# {heading}",
        "",
        f"> {NOTICE}",
        "",
        f"Total de documentos: {len(documents)}",
        "",
        "## Sumario",
        "",
    ]

    for index, document in enumerate(documents, start=1):
        lines.append(f"{index}. `{document.title}` - `{document.status}` - `{_relative(document.source)}`")

    for document in documents:
        lines.extend(
            [
                "",
                "---",
                "",
                f"## {document.title}",
                "",
                f"- Fonte: `{_relative(document.source)}`",
                f"- Status: `{document.status}`",
            ]
        )

        if document.metadata:
            lines.append("- Metadados:")
            for key, value in document.metadata:
                lines.append(f"  - {key}: {_normalize_inline_links(value, document.source)}")

        lines.append("")
        lines.append("### Resumo")
        lines.append("")
        if document.summary_paragraphs:
            lines.extend(_normalize_inline_links(paragraph, document.source) for paragraph in document.summary_paragraphs)
        else:
            lines.append("Resumo indisponivel: nao foram encontrados tres paragrafos de prosa.")

    lines.append("")
    return "\n".join(lines)


def generate_indexes(config_path: Path = CONFIG_PATH) -> tuple[Path, ...]:
    """Generate every configured index file and return output paths."""
    outputs: list[Path] = []
    for section in parse_index_config(config_path):
        documents = tuple(extract_document_summary(path) for path in section.sources)
        content = render_index(section, documents)
        section.output.parent.mkdir(parents=True, exist_ok=True)
        section.output.write_text(content, encoding="utf-8")
        outputs.append(section.output)
    return tuple(outputs)


def main() -> int:
    """CLI entrypoint."""
    outputs = generate_indexes()
    for output in outputs:
        print(f"generated {_relative(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
