"""Cross-reference extracted sources with a server file tree."""

import logging
import re
from pathlib import Path

from pbix_mapper.models import Report, Source

logger = logging.getLogger(__name__)

DATE_PATTERNS: list[tuple[str, str]] = [
    (r"(\d{8})_\d{2,4}", "YYYYMMDD_HHMM"),
    (r"(\d{2})(\d{2})(\d{4})\.", "DDMMYYYY"),
    (r"(\d{4})(\d{2})(\d{2})\.", "YYYYMMDD"),
    (r"(\d{8})\.", "YYYYMMDD"),
]


def parse_tree(tree_path: Path) -> list[str]:
    """Parse a file tree listing into a list of clean paths.

    Accepts any tree format where each line is a full path.
    Automatically detects and strips the drive prefix (e.g. Z:\\, C:\\).
    """
    lines = tree_path.read_text(encoding="utf-8", errors="replace").splitlines()

    paths: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("fullname") or line.startswith("---"):
            continue
        if len(line) >= 3 and line[1] == ":" and line[2] == "\\":
            paths.append(line)
        elif line.startswith("\\\\") or line.startswith("/"):
            paths.append(line)

    logger.info("Tree loaded: %d paths", len(paths))
    return paths


def _detect_drive_prefix(paths: list[str]) -> str:
    """Detect the common drive prefix (e.g. 'Z:\\')."""
    for p in paths[:20]:
        if len(p) >= 3 and p[1] == ":" and p[2] == "\\":
            return p[:3]
    return ""


def _normalize_folder(name: str) -> str:
    return name.strip().strip("/\\").lower().replace(" ", "_")


def _extract_search_names(subfolder: str) -> list[str]:
    """Extract folder name candidates from a subfolder path."""
    parts = [p for p in subfolder.strip("/").split("/") if p]
    if not parts:
        return []
    candidates = [parts[-1]]
    if len(parts) > 1:
        candidates.append("/".join(parts))
    return candidates


def find_in_tree(subfolder: str, tree_paths: list[str]) -> dict:
    """Search for a subfolder in the tree paths.

    Returns dict with: found, tree_path, files, is_daily_dump, latest_date, file_count.
    """
    result = {
        "found": False,
        "tree_path": "",
        "files": [],
        "is_daily_dump": False,
        "latest_date": "",
        "file_count": 0,
    }

    candidates = _extract_search_names(subfolder)
    if not candidates:
        return result

    matched_prefix = ""
    for candidate in candidates:
        candidate_norm = _normalize_folder(candidate)
        for tree_path in tree_paths:
            drive_prefix = tree_path[:3] if len(tree_path) >= 3 and tree_path[1] == ":" else ""
            path_after_drive = tree_path[len(drive_prefix):].replace("\\", "/") if drive_prefix else tree_path.replace("\\", "/")
            path_norm = path_after_drive.lower().replace(" ", "_")

            if path_norm == candidate_norm or path_norm.startswith(candidate_norm + "/"):
                if not matched_prefix or len(tree_path) < len(matched_prefix):
                    matched_prefix = tree_path
                result["found"] = True

    if not result["found"]:
        for candidate in candidates:
            candidate_norm = _normalize_folder(candidate)
            for tree_path in tree_paths:
                parts = tree_path.replace("\\", "/").split("/")
                for part in parts:
                    if _normalize_folder(part) == candidate_norm:
                        result["found"] = True
                        idx = parts.index(part)
                        sep = "\\" if "\\" in tree_path else "/"
                        matched_prefix = sep.join(parts[: idx + 1])
                        break
                if result["found"]:
                    break

    if not result["found"]:
        return result

    result["tree_path"] = matched_prefix

    sep = "\\" if "\\" in matched_prefix else "/"
    prefix_norm = matched_prefix.rstrip(sep) + sep
    descendants = [p for p in tree_paths if p.startswith(prefix_norm)]
    files_only = [p for p in descendants if "." in p.split(sep)[-1]]

    result["files"] = files_only
    result["file_count"] = len(files_only)

    if files_only:
        dump_info = detect_dump_pattern(files_only)
        result["is_daily_dump"] = dump_info["is_daily"]
        result["latest_date"] = dump_info["latest_date"]

    return result


def find_local_path_in_tree(local_path: str, tree_paths: list[str]) -> dict:
    """Search for a local file path in the tree by filename."""
    result = {"found": False, "tree_path": ""}

    if not local_path:
        return result

    sep = "\\" if "\\" in local_path else "/"
    filename = local_path.split(sep)[-1]
    if not filename:
        parts = local_path.strip(sep).split(sep)
        filename = parts[-1] if parts else ""

    if not filename:
        return result

    filename_lower = filename.lower()

    for tree_path in tree_paths:
        tree_sep = "\\" if "\\" in tree_path else "/"
        tree_filename = tree_path.split(tree_sep)[-1]
        if tree_filename.lower() == filename_lower:
            result["found"] = True
            result["tree_path"] = tree_path
            return result

    return result


def detect_dump_pattern(file_paths: list[str]) -> dict:
    """Detect daily dump patterns in filenames by looking for date patterns."""
    result = {"is_daily": False, "pattern": "", "latest_date": ""}

    dates_found: list[str] = []
    for fp in file_paths:
        sep = "\\" if "\\" in fp else "/"
        filename = fp.split(sep)[-1]

        for pattern, fmt in DATE_PATTERNS:
            match = re.search(pattern, filename)
            if match:
                if fmt in ("YYYYMMDD_HHMM", "YYYYMMDD"):
                    date_str = match.group(1)
                    if len(date_str) == 8:
                        year = int(date_str[:4])
                        if 2020 <= year <= 2030:
                            dates_found.append(date_str)
                            break
                elif fmt == "DDMMYYYY":
                    dd, mm, yyyy = match.group(1), match.group(2), match.group(3)
                    if 2020 <= int(yyyy) <= 2030:
                        dates_found.append(f"{yyyy}{mm}{dd}")
                        break

    if len(dates_found) >= 3:
        result["is_daily"] = True
        result["pattern"] = "Daily dump"
        dates_sorted = sorted(dates_found, reverse=True)
        result["latest_date"] = dates_sorted[0]

    return result


def crossref_reports(
    reports: list[Report], tree_paths: list[str]
) -> list[dict]:
    """Cross-reference reports with a file tree.

    Returns list of dicts with original source data + cross-reference columns.
    """
    logger.info("Cross-referencing %d reports with tree (%d paths)...", len(reports), len(tree_paths))

    rows: list[dict] = []
    found_count = 0
    not_found_count = 0

    for report in reports:
        for src in report.real_sources:
            row = {"report": report.name}
            row.update(src.to_dict())

            tree_result: dict
            if src.connection_type == "SharePoint" and src.subfolder:
                tree_result = find_in_tree(src.subfolder, tree_paths)
            elif src.connection_type in ("Folder", "Excel (local)", "CSV (local)", "File (local)"):
                tree_result = find_local_path_in_tree(src.origin, tree_paths)
                tree_result.setdefault("is_daily_dump", False)
                tree_result.setdefault("latest_date", "")
                tree_result.setdefault("file_count", 0)
            else:
                tree_result = {"found": False, "tree_path": "", "is_daily_dump": False, "latest_date": "", "file_count": 0}

            row["server_path"] = tree_result.get("tree_path", "")
            row["path_found"] = tree_result["found"]
            row["is_daily_dump"] = tree_result.get("is_daily_dump", False)
            row["latest_date"] = tree_result.get("latest_date", "")
            row["file_count"] = tree_result.get("file_count", 0)

            if tree_result["found"]:
                found_count += 1
            else:
                not_found_count += 1

            rows.append(row)

    logger.info("Cross-reference done: %d found, %d not found", found_count, not_found_count)
    return rows


# "Confia, mas verifica." — Proverbio russo
