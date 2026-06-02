"""Tests for the markdown index generator."""

from __future__ import annotations

from pathlib import Path

from scripts import generate_index


def test_parse_index_config_reads_sections(tmp_path: Path) -> None:
    config = tmp_path / "_index_config.yaml"
    config.write_text(
        "\n".join(
            [
                "prds:",
                "  output: docs/_index/PRDS_INDEX.md",
                "  sources:",
                "    - docs/prd/example.md",
                "adrs:",
                "  output: docs/_index/ADRS_INDEX.md",
                "  sources:",
                "    - docs/architecture/example.md",
            ]
        ),
        encoding="utf-8",
    )

    sections = generate_index.parse_index_config(config)

    import os
    assert [section.name for section in sections] == ["prds", "adrs"]
    assert str(sections[0].output).endswith(os.path.normpath("docs/_index/PRDS_INDEX.md"))
    assert str(sections[1].sources[0]).endswith(os.path.normpath("docs/architecture/example.md"))


def test_extract_document_summary_handles_prd_format(tmp_path: Path) -> None:
    source = tmp_path / "doc.md"
    source.write_text(
        "\n".join(
            [
                "# Example PRD",
                "",
                "## 1. Metadata",
                "- **PRD ID:** PRD-99",
                "- **Status:** Accepted",
                "- **Owner:** Rafael",
                "",
                "## 2. Executive Summary",
                "Primeiro paragrafo de resumo.",
                "",
                "Segundo paragrafo de resumo.",
                "",
                "Terceiro paragrafo de resumo.",
                "",
                "## 3. Details",
                "- lista que nao entra no resumo",
            ]
        ),
        encoding="utf-8",
    )

    summary = generate_index.extract_document_summary(source)

    assert summary.title == "Example PRD"
    assert summary.status == "Accepted"
    assert ("PRD ID", "PRD-99") in summary.metadata
    assert summary.summary_paragraphs == (
        "Primeiro paragrafo de resumo.",
        "Segundo paragrafo de resumo.",
        "Terceiro paragrafo de resumo.",
    )


def test_generate_indexes_writes_notice_and_document_sections(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    prd_dir = docs_root / "prd"
    adr_dir = docs_root / "architecture"
    prd_dir.mkdir(parents=True)
    adr_dir.mkdir(parents=True)

    prd = prd_dir / "sample_prd.md"
    prd.write_text(
        "\n".join(
            [
                "# Sample PRD",
                "",
                "- **Status:** Accepted",
                "- **Owner:** Rafael",
                "",
                "Primeiro resumo.",
                "",
                "Segundo resumo.",
                "",
                "Terceiro resumo.",
            ]
        ),
        encoding="utf-8",
    )

    adr = adr_dir / "sample_adr.md"
    adr.write_text(
        "\n".join(
            [
                "# Sample ADR",
                "",
                "*   **Status**: Accepted",
                "*   **Date**: 2026-05-22",
                "",
                "Contexto principal.",
                "",
                "Decisao principal.",
                "",
                "Consequencia principal.",
            ]
        ),
        encoding="utf-8",
    )

    config = docs_root / "_index_config.yaml"
    config.write_text(
        "\n".join(
            [
                "prds:",
                "  output: docs/_index/PRDS_INDEX.md",
                "  sources:",
                "    - docs/prd/sample_prd.md",
                "adrs:",
                "  output: docs/_index/ADRS_INDEX.md",
                "  sources:",
                "    - docs/architecture/sample_adr.md",
            ]
        ),
        encoding="utf-8",
    )

    original_root = generate_index.PROJECT_ROOT
    original_config = generate_index.CONFIG_PATH
    try:
        generate_index.PROJECT_ROOT = tmp_path
        generate_index.CONFIG_PATH = config
        outputs = generate_index.generate_indexes(config)
    finally:
        generate_index.PROJECT_ROOT = original_root
        generate_index.CONFIG_PATH = original_config

    prds_output = docs_root / "_index" / "PRDS_INDEX.md"
    adrs_output = docs_root / "_index" / "ADRS_INDEX.md"

    assert outputs == (prds_output, adrs_output)
    prds_text = prds_output.read_text(encoding="utf-8")
    adrs_text = adrs_output.read_text(encoding="utf-8")
    assert "> ⚠️ ARQUIVO AUTO-GERADO - NAO EDITAR MANUALMENTE" in prds_text
    assert "> Gerado por: python scripts/generate_index.py" in prds_text
    assert "> Fonte primaria: ver docs/prd/*.md e docs/architecture/*.md" in prds_text
    assert "> Ultima geracao:" in prds_text
    assert "## Sample PRD" in prds_text
    assert "## Sample ADR" in adrs_text
