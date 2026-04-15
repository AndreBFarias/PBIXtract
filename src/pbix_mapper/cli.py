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
def version() -> None:
    """Show version."""
    from pbix_mapper import __version__
    typer.echo(f"pbix-mapper {__version__}")


# "A liberdade e o reconhecimento da necessidade." — Friedrich Engels
