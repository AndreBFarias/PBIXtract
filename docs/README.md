# pbix-mapper

> *"O mapa nao e o territorio, mas sem mapa voce esta perdido."*

Extract and map all data sources from Power BI (`.pbix`) files. Feed it a PBIX, get a structured de-para of every connection, table, and parameter.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-green.svg)
![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)

---

## Why

Power BI files are opaque binaries. When you need to migrate reports, audit data sources, or understand what a dashboard actually consumes, you're stuck clicking through Power Query editor one table at a time.

**pbix-mapper** cracks open the PBIX, extracts every Power Query M expression, parses the connection patterns, resolves parameters, and gives you a clean, structured mapping of all data sources.

---

## Install

```bash
pip install pbix-mapper
```

Or from source:

```bash
git clone https://github.com/andrefarias/pbix-mapper.git
cd pbix-mapper
pip install -e .
```

---

## Usage

### Terminal table (default)

```bash
pbix-mapper extract report.pbix
```

### CSV output

```bash
pbix-mapper extract report.pbix --format csv --output sources.csv
```

### JSON output

```bash
pbix-mapper extract ./my_reports/ --format json --output sources.json
```

### Real sources only (exclude embedded/derived tables)

```bash
pbix-mapper extract report.pbix --real-only
```

### Verbose mode

```bash
pbix-mapper extract report.pbix -v
```

---

## What it extracts

For each query/table in the PBIX, pbix-mapper identifies:

| Field | Description |
|---|---|
| **report** | Name of the PBIX file |
| **query_name** | Power Query table/query name |
| **connection_type** | SharePoint, Oracle, SQL Server, Excel, Folder, API/Web, OData, ODBC |
| **origin** | Connection string, URL, file path |
| **table_or_query** | Sheet name, SQL query, database name |
| **is_real_source** | `True` for external connectors, `False` for embedded/derived |
| **subfolder** | SharePoint subfolder path (if applicable) |
| **file_format** | Excel, CSV, TXT, etc. |

### Supported connection types

- SharePoint.Files
- Oracle.Database
- Sql.Database
- Folder.Files
- File.Contents / Excel.Workbook
- Csv.Document
- Web.Contents
- OData.Feed
- Odbc.Query

---

## How it works

1. PBIX files are ZIP archives containing a `DataModel` binary (ABF/XPress9 compressed)
2. [pbixray](https://github.com/pbi-tools/pbixray) decompresses and extracts Power Query M expressions
3. pbix-mapper parses the M code with regex to classify each data source
4. Parameters (`Path_*`) are resolved to their actual values
5. Output is structured as flat CSV/JSON or a rich terminal table

---

## Roadmap

- [x] **Sprint 1** — Core extraction + CLI (CSV, JSON, table)
- [ ] **Sprint 2** — Cross-reference with server file trees + Excel enrichment
- [ ] **Sprint 3** — Local web interface (Streamlit)
- [ ] **Sprint 4** — Communication template generator (Teams/email)

---

## License

GPL-3.0-or-later. See [LICENSE](../LICENSE).
