"""CLI interface for pbix-mapper."""

import logging
from pathlib import Path

import typer

from pbix_mapper.extractor import extract_all
from pbix_mapper.formatters import to_csv, to_json, to_table

app = typer.Typer(
    name="pbix-mapper",
    help="Extract and map data sources from Power BI (.pbix) files.",
    no_args_is_help=True,
)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(name)s — %(message)s",
    )


@app.command()
def extract(
    target: Path = typer.Argument(
        ...,
        help="Path to a .pbix file or directory containing .pbix files.",
        exists=True,
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: table, csv, json.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (for csv/json). Prints to stdout if omitted.",
    ),
    real_only: bool = typer.Option(
        False,
        "--real-only",
        "-r",
        help="Show only real data sources (exclude embedded/derived).",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose logging output.",
    ),
) -> None:
    """Extract data sources from Power BI (.pbix) files."""
    _setup_logging(verbose)

    reports = extract_all(target)
    if not reports:
        typer.echo("No reports found.", err=True)
        raise typer.Exit(code=1)

    total = sum(len(r.sources) for r in reports)
    real = sum(len(r.real_sources) for r in reports)

    if format == "table":
        to_table(reports, real_only=real_only)
        typer.echo(f"{len(reports)} reports, {real} real sources ({total} total)")

    elif format == "csv":
        content = to_csv(reports, output=output, real_only=real_only)
        if not output:
            typer.echo(content)

    elif format == "json":
        content = to_json(reports, output=output, real_only=real_only)
        if not output:
            typer.echo(content)

    else:
        typer.echo(f"Unknown format: {format}. Use: table, csv, json.", err=True)
        raise typer.Exit(code=1)


@app.command()
def crossref(
    sources_csv: Path = typer.Argument(
        ...,
        help="CSV file from 'extract --format csv' output.",
        exists=True,
    ),
    tree: Path = typer.Option(
        ...,
        "--tree",
        "-t",
        help="Path to server file tree listing (one path per line).",
        exists=True,
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output CSV path. Prints to stdout if omitted.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Cross-reference extracted sources with a server file tree."""
    import csv as csv_mod
    from io import StringIO

    import pandas as pd

    from pbix_mapper.cross_ref import crossref_reports, parse_tree
    from pbix_mapper.models import Report, Source

    _setup_logging(verbose)

    df = pd.read_csv(sources_csv, encoding="utf-8-sig")
    reports_map: dict[str, Report] = {}
    for _, row in df.iterrows():
        rname = str(row.get("report", ""))
        if rname not in reports_map:
            reports_map[rname] = Report(name=rname, path=str(row.get("report_path", "")))
        reports_map[rname].sources.append(Source(
            query_name=str(row.get("query_name", "")),
            connection_type=str(row.get("connection_type", "")),
            origin=str(row.get("origin", "")),
            table_or_query=str(row.get("table_or_query", "")),
            is_real_source=str(row.get("is_real_source", "")).lower() == "true",
            subfolder=str(row.get("subfolder", "")),
            file_format=str(row.get("file_format", "")),
        ))

    tree_paths = parse_tree(tree)
    results = crossref_reports(list(reports_map.values()), tree_paths)

    if not results:
        typer.echo("No results.", err=True)
        raise typer.Exit(code=1)

    buf = StringIO()
    writer = csv_mod.DictWriter(buf, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)
    content = buf.getvalue()

    if output:
        output.write_text(content, encoding="utf-8-sig")
        typer.echo(f"Cross-reference written: {output} ({len(results)} rows)")
    else:
        typer.echo(content)


@app.command()
def enrich(
    sources_csv: Path = typer.Argument(
        ...,
        help="CSV file with extracted sources.",
        exists=True,
    ),
    excel: Path = typer.Option(
        ...,
        "--excel",
        "-e",
        help="Excel file with enrichment data.",
        exists=True,
    ),
    match_column: str = typer.Option(
        ...,
        "--match-column",
        "-m",
        help="Column in Excel to match against report names.",
    ),
    source_column: str = typer.Option(
        ...,
        "--source-column",
        "-s",
        help="Column in Excel with source/table names.",
    ),
    sheet: str = typer.Option("0", "--sheet", help="Sheet name or index (default: 0)."),
    header_row: int = typer.Option(0, "--header-row", help="Header row index (0-based)."),
    ffill: str | None = typer.Option(None, "--ffill", help="Column to forward-fill."),
    output: Path | None = typer.Option(None, "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Enrich extracted sources with metadata from an Excel file."""
    import csv as csv_mod
    from io import StringIO

    import pandas as pd

    from pbix_mapper.enricher import enrich_sources, load_enrichment_excel

    _setup_logging(verbose)

    df_sources = pd.read_csv(sources_csv, encoding="utf-8-sig")
    source_rows = df_sources.to_dict("records")

    sheet_val: str | int = int(sheet) if sheet.isdigit() else sheet
    enrich_df = load_enrichment_excel(
        excel,
        sheet=sheet_val,
        header_row=header_row,
        ffill_column=ffill,
    )

    enriched = enrich_sources(
        source_rows,
        enrich_df,
        match_column=match_column,
        source_column=source_column,
    )

    if not enriched:
        typer.echo("No results.", err=True)
        raise typer.Exit(code=1)

    buf = StringIO()
    writer = csv_mod.DictWriter(buf, fieldnames=enriched[0].keys())
    writer.writeheader()
    writer.writerows(enriched)
    content = buf.getvalue()

    if output:
        output.write_text(content, encoding="utf-8-sig")
        typer.echo(f"Enriched output written: {output} ({len(enriched)} rows)")
    else:
        typer.echo(content)


@app.command()
def messages(
    sources_csv: Path = typer.Argument(
        ...,
        help="CSV file with extracted sources (from extract or crossref).",
        exists=True,
    ),
    config: Path = typer.Option(
        ...,
        "--config",
        "-c",
        help="YAML config file with groups, members, and message template.",
        exists=True,
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output markdown file. Prints to stdout if omitted.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Generate communication messages from a YAML config + extracted sources."""
    import pandas as pd

    from pbix_mapper.messenger import generate_messages

    _setup_logging(verbose)

    df = pd.read_csv(sources_csv, encoding="utf-8-sig")
    source_rows = df.to_dict("records")

    rendered = generate_messages(config, source_rows, output_path=output)

    if not output:
        typer.echo(rendered)


@app.command()
def web(
    port: int = typer.Option(8501, "--port", "-p", help="Port for the web server."),
) -> None:
    """Launch the web interface (Streamlit)."""
    import subprocess
    import sys

    app_path = Path(__file__).parent / "web" / "app.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port)],
        check=True,
    )


@app.command()
def version() -> None:
    """Show version."""
    from pbix_mapper import __version__
    typer.echo(f"pbix-mapper {__version__}")


# "A liberdade e o reconhecimento da necessidade." — Friedrich Engels
