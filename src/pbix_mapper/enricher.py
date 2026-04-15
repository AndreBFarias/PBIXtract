"""Enrich extracted sources with metadata from Excel spreadsheets."""

import logging
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text for fuzzy comparison: lowercase, no accents, no separators."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"\.(xlsx|xls|csv|txt)$", "", text)
    text = re.sub(r"[\s_\-\.]+", " ", text)
    return text


def fuzzy_match(needle: str, haystack: list[str], threshold: float = 0.7) -> str | None:
    """Find the best fuzzy match for needle in haystack.

    Tries exact match, containment, then SequenceMatcher.
    """
    n_norm = normalize_text(needle)
    if not n_norm:
        return None

    for item in haystack:
        if normalize_text(item) == n_norm:
            return item

    for item in haystack:
        i_norm = normalize_text(item)
        longer = max(len(i_norm), len(n_norm))
        shorter = min(len(i_norm), len(n_norm))
        if shorter > 0 and longer > 0 and shorter / longer >= 0.6:
            if i_norm in n_norm or n_norm in i_norm:
                return item

    best_ratio = 0.0
    best_match = None
    for item in haystack:
        ratio = SequenceMatcher(None, n_norm, normalize_text(item)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = item

    if best_ratio >= threshold:
        return best_match

    return None


def load_enrichment_excel(
    path: Path,
    sheet: str | int = 0,
    header_row: int = 0,
    match_column: str | None = None,
    source_column: str | None = None,
    ffill_column: str | None = None,
) -> pd.DataFrame:
    """Load an Excel file for enrichment.

    Args:
        path: Path to the Excel file.
        sheet: Sheet name or index.
        header_row: Row index to use as header (0-based).
        match_column: Column name to use for matching report names.
        source_column: Column name containing source/table names.
        ffill_column: Column name to forward-fill (for hierarchical structures).
    """
    logger.info("Loading enrichment file: %s (sheet=%s, header=%d)", path.name, sheet, header_row)

    df = pd.read_excel(path, sheet_name=sheet, header=header_row)

    if ffill_column and ffill_column in df.columns:
        df[ffill_column] = df[ffill_column].ffill()

    df = df.dropna(how="all")

    logger.info("  Loaded: %d rows, %d columns", len(df), len(df.columns))
    return df


def enrich_sources(
    source_rows: list[dict],
    enrichment_df: pd.DataFrame,
    match_column: str,
    source_column: str,
    report_key: str = "report",
    source_key: str = "query_name",
    columns_to_add: list[str] | None = None,
    aliases: dict[str, list[str]] | None = None,
) -> list[dict]:
    """Enrich source rows with data from an enrichment DataFrame.

    Args:
        source_rows: List of dicts (from extract or crossref output).
        enrichment_df: DataFrame loaded from enrichment Excel.
        match_column: Column in enrichment_df to match against report names.
        source_column: Column in enrichment_df to match against source names.
        report_key: Key in source_rows dicts for report name.
        source_key: Key in source_rows dicts for source/query name.
        columns_to_add: Which columns from enrichment_df to add. None = all.
        aliases: Manual aliases for report name matching.
    """
    logger.info("Enriching %d sources with %d enrichment rows...", len(source_rows), len(enrichment_df))

    aliases = aliases or {}
    enrich_reports = enrichment_df[match_column].dropna().unique().tolist()

    cols_to_add = columns_to_add or [
        c for c in enrichment_df.columns
        if c not in (match_column, source_column)
    ]

    enriched = []
    matched_count = 0

    for row in source_rows:
        row = dict(row)
        report_name = row.get(report_key, "")

        matched_report = fuzzy_match(report_name, enrich_reports)
        if not matched_report:
            report_aliases = aliases.get(report_name, [])
            for alias in report_aliases:
                matched_report = fuzzy_match(alias, enrich_reports)
                if matched_report:
                    break

        row["enrichment_matched"] = bool(matched_report)

        if not matched_report:
            for col in cols_to_add:
                row[col] = ""
            enriched.append(row)
            continue

        subset = enrichment_df[enrichment_df[match_column] == matched_report]
        source_names = subset[source_column].dropna().tolist()
        query_name = row.get(source_key, "")

        matched_source = fuzzy_match(query_name, source_names)

        if matched_source:
            matched_count += 1
            match_row = subset[subset[source_column] == matched_source].iloc[0]
            for col in cols_to_add:
                val = match_row.get(col, "")
                row[col] = str(val).strip() if pd.notna(val) and str(val).strip() else ""
        else:
            for col in cols_to_add:
                row[col] = ""

        enriched.append(row)

    logger.info("Enrichment done: %d/%d sources matched", matched_count, len(source_rows))
    return enriched


# "Dados sem contexto sao apenas ruido." — Nate Silver
