"""Core extraction engine — parse Power Query M from PBIX files."""

import logging
import re
from pathlib import Path

from pbixray import PBIXRay

from pbix_mapper.models import Report, Source

logger = logging.getLogger(__name__)

SOURCE_PATTERNS: list[tuple[str, str]] = [
    (r"SharePoint\.Files\(", "SharePoint"),
    (r"Oracle\.Database\(", "Oracle"),
    (r"Sql\.Database\(", "SQL Server"),
    (r"Odbc\.Query\(", "ODBC"),
    (r"OData\.Feed\(", "OData"),
    (r"Web\.Contents\(", "API/Web"),
    (r"Folder\.Files\(", "Folder"),
    (r"Excel\.Workbook\(File\.Contents\(", "Excel (local)"),
    (r"Csv\.Document\(File\.Contents\(", "CSV (local)"),
    (r"File\.Contents\(", "File (local)"),
]

NOT_REAL_SOURCE_PATTERNS: list[str] = [
    r"Table\.FromRows\(Json\.Document\(Binary",
    r"DateTimeZone\.(SwitchZone|LocalNow|UtcNow)",
    r"#table\(\d+,\s*\{\{",
]


def _extract_parameter_value(expression: str) -> str | None:
    match = re.search(r'^"([^"]+)"', expression.strip())
    return match.group(1) if match else None


def _extract_sharepoint_subfolder(
    expression: str, param_map: dict[str, str]
) -> str | None:
    match = re.search(
        r"Text\.Contains\(\[Folder Path\],\s*(Path_SubPasta_\w+)", expression
    )
    if match:
        return param_map.get(match.group(1))

    match = re.search(
        r'Text\.Contains\(\[Folder Path\],\s*"([^"]+)"', expression
    )
    return match.group(1) if match else None


def _extract_local_path(expression: str) -> str | None:
    for pattern in [r'File\.Contents\("([^"]+)"\)', r'Folder\.Files\("([^"]+)"\)']:
        match = re.search(pattern, expression)
        if match:
            return match.group(1)
    return None


def _detect_file_format(expression: str) -> str:
    checks = [
        (r"Csv\.Document\(", "CSV"),
        (r'Text\.Lower\(\[Extension\]\)\s*=\s*"\.xlsx"', "Excel (.xlsx)"),
        (r'Text\.EndsWith\(Text\.Lower\(\[Name\]\),\s*"\.xls"', "Excel (.xls)"),
        (r'Text\.EndsWith\(Text\.Lower\(\[Name\]\),\s*"\.csv"', "CSV"),
        (r'Text\.EndsWith\(Text\.Lower\(\[Name\]\),\s*"\.txt"', "TXT"),
        (r"Excel\.Workbook\(", "Excel"),
    ]
    for pattern, fmt in checks:
        if re.search(pattern, expression):
            return fmt
    return "N/A"


def _classify_query(
    table_name: str,
    expression: str,
    param_map: dict[str, str],
    sharepoint_base: str | None,
) -> Source:
    for pattern in NOT_REAL_SOURCE_PATTERNS:
        if re.search(pattern, expression):
            return Source(
                query_name=table_name,
                connection_type="Embedded/Computed",
                origin="",
                table_or_query="",
                is_real_source=False,
            )

    conn_type = "Derived/Transform"
    is_real = False

    for pattern, tipo in SOURCE_PATTERNS:
        if re.search(pattern, expression):
            conn_type = tipo
            is_real = True
            break
    else:
        return Source(
            query_name=table_name,
            connection_type=conn_type,
            origin="",
            table_or_query="",
            is_real_source=False,
        )

    origin = ""
    table_or_query = ""
    subfolder = ""
    file_format = "N/A"

    if conn_type == "SharePoint":
        subfolder = _extract_sharepoint_subfolder(expression, param_map) or ""
        if sharepoint_base and subfolder:
            origin = sharepoint_base + subfolder
        elif sharepoint_base:
            origin = sharepoint_base
        file_format = _detect_file_format(expression)

        sheet_match = re.search(r'NomeSheet\s*=\s*"([^"]+)"', expression)
        if sheet_match:
            table_or_query = f"Sheet: {sheet_match.group(1)}"

    elif conn_type in ("Folder", "Excel (local)", "CSV (local)", "File (local)"):
        origin = _extract_local_path(expression) or ""
        file_format = _detect_file_format(expression)

    elif conn_type == "Oracle":
        match = re.search(r'Oracle\.Database\("([^"]+)"', expression)
        if match:
            origin = match.group(1)
        schema_match = re.search(
            r'Oracle\.Database\("[^"]+",\s*[^,]*Schema\s*=\s*"([^"]+)"', expression
        )
        if schema_match:
            table_or_query = f"Schema: {schema_match.group(1)}"

    elif conn_type == "SQL Server":
        match = re.search(r'Sql\.Database\("([^"]+)",\s*"([^"]+)"', expression)
        if match:
            origin = match.group(1)
            table_or_query = f"Database: {match.group(2)}"

    elif conn_type in ("API/Web", "OData"):
        match = re.search(r'(?:Web\.Contents|OData\.Feed)\("([^"]+)"', expression)
        if match:
            origin = match.group(1)

    return Source(
        query_name=table_name,
        connection_type=conn_type,
        origin=origin,
        table_or_query=table_or_query,
        is_real_source=is_real,
        subfolder=subfolder,
        file_format=file_format,
    )


def extract_report(pbix_path: Path) -> Report:
    """Extract all data sources from a single PBIX file."""
    report_name = pbix_path.stem
    logger.info("Processing: %s", report_name)

    model = PBIXRay(str(pbix_path))

    param_map: dict[str, str] = {}
    sharepoint_base: str | None = None

    m_params = model.m_parameters
    if m_params is not None and len(m_params) > 0:
        for _, row in m_params.iterrows():
            name = row["ParameterName"]
            expr = str(row["Expression"])
            value = _extract_parameter_value(expr)
            if value and name.startswith("Path_"):
                param_map[name] = value
                if name == "Path_Primario":
                    sharepoint_base = value

    power_query = model.power_query
    if power_query is None or len(power_query) == 0:
        logger.warning("  No queries found in %s", report_name)
        return Report(name=report_name, path=str(pbix_path), parameters=param_map)

    for _, row in power_query.iterrows():
        table_name = row["TableName"]
        expression = str(row["Expression"])
        if table_name.startswith("Path_"):
            value = _extract_parameter_value(expression)
            if value:
                param_map[table_name] = value
                if table_name == "Path_Primario":
                    sharepoint_base = value

    logger.info("  Path parameters: %s", list(param_map.keys()))

    sources: list[Source] = []
    for _, row in power_query.iterrows():
        table_name = row["TableName"]
        expression = str(row["Expression"])

        if table_name.startswith("Path_"):
            continue

        if expression.strip().startswith("(") and "=>" in expression.split("\n")[0]:
            if table_name.startswith("Fx") or table_name.startswith("Func"):
                continue

        source = _classify_query(table_name, expression, param_map, sharepoint_base)
        sources.append(source)

    real_count = sum(1 for s in sources if s.is_real_source)
    logger.info(
        "  Queries: %d total, %d real sources, %d derived/embedded",
        len(sources),
        real_count,
        len(sources) - real_count,
    )

    return Report(
        name=report_name,
        path=str(pbix_path),
        sources=sources,
        parameters=param_map,
    )


def extract_all(target: Path) -> list[Report]:
    """Extract data sources from one or more PBIX files.

    Args:
        target: Path to a single .pbix file or a directory containing them.
    """
    if target.is_file() and target.suffix.lower() == ".pbix":
        return [extract_report(target)]

    if target.is_dir():
        pbix_files = sorted(target.glob("*.pbix"))
        if not pbix_files:
            logger.error("No .pbix files found in %s", target)
            return []
        logger.info("Found %d PBIX files", len(pbix_files))
        return [extract_report(p) for p in pbix_files]

    logger.error("Target is not a .pbix file or directory: %s", target)
    return []


# "O mapa nao e o territorio." — Alfred Korzybski
