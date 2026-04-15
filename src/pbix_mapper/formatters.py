"""Output formatters — CSV, JSON, terminal table."""

import csv
import json
import logging
from io import StringIO
from pathlib import Path

from rich.console import Console
from rich.table import Table

from pbix_mapper.models import Report

logger = logging.getLogger(__name__)

FLAT_COLUMNS = [
    "report",
    "query_name",
    "connection_type",
    "origin",
    "table_or_query",
    "is_real_source",
    "subfolder",
    "file_format",
]


def _flatten(reports: list[Report], real_only: bool = False) -> list[dict]:
    rows = []
    for report in reports:
        sources = report.real_sources if real_only else report.sources
        for src in sources:
            row = {"report": report.name, "report_path": report.path}
            row.update(src.to_dict())
            rows.append(row)
    return rows


def to_csv(
    reports: list[Report],
    output: Path | None = None,
    real_only: bool = False,
    bom: bool = True,
) -> str:
    """Export reports to CSV. Returns CSV string and optionally writes to file."""
    rows = _flatten(reports, real_only)
    if not rows:
        return ""

    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    content = buf.getvalue()

    if output:
        encoding = "utf-8-sig" if bom else "utf-8"
        output.write_text(content, encoding=encoding)
        logger.info("CSV written: %s (%d rows)", output, len(rows))

    return content


def to_json(
    reports: list[Report],
    output: Path | None = None,
    real_only: bool = False,
) -> str:
    """Export reports to JSON. Returns JSON string and optionally writes to file."""
    data = []
    for report in reports:
        sources = report.real_sources if real_only else report.sources
        data.append({
            "report": report.name,
            "path": report.path,
            "parameters": report.parameters,
            "sources": [s.to_dict() for s in sources],
        })

    content = json.dumps(data, indent=2, ensure_ascii=False)

    if output:
        output.write_text(content, encoding="utf-8")
        logger.info("JSON written: %s", output)

    return content


def to_table(
    reports: list[Report],
    real_only: bool = False,
) -> None:
    """Print reports as a rich table in the terminal."""
    console = Console()

    for report in reports:
        sources = report.real_sources if real_only else report.sources
        if not sources:
            continue

        table = Table(
            title=f"{report.name} ({len(sources)} sources)",
            show_lines=True,
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Query", style="bold")
        table.add_column("Type")
        table.add_column("Origin", max_width=60)
        table.add_column("Table/Sheet")
        table.add_column("Format")
        table.add_column("Real", justify="center")

        for i, src in enumerate(sources, 1):
            real_mark = "[green]Y[/green]" if src.is_real_source else "[dim]N[/dim]"
            table.add_row(
                str(i),
                src.query_name,
                src.connection_type,
                src.origin[:60] if src.origin else "",
                src.table_or_query,
                src.file_format,
                real_mark,
            )

        console.print(table)
        console.print()


# "Quem controla os dados controla o futuro." — Tim Berners-Lee
