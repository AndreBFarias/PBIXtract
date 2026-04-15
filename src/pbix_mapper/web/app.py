"""Streamlit web interface for pbix-mapper."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from pbix_mapper.extractor import extract_report
from pbix_mapper.cross_ref import crossref_reports, parse_tree
from pbix_mapper.models import Report


st.set_page_config(
    page_title="pbix-mapper",
    page_icon="::bar_chart::",
    layout="wide",
)


def _reports_to_df(reports: list[Report], real_only: bool = False) -> pd.DataFrame:
    rows = []
    for report in reports:
        sources = report.real_sources if real_only else report.sources
        for src in sources:
            rows.append({
                "Report": report.name,
                "Query": src.query_name,
                "Type": src.connection_type,
                "Origin": src.origin,
                "Table/Sheet": src.table_or_query,
                "Format": src.file_format,
                "Subfolder": src.subfolder,
                "Real Source": src.is_real_source,
            })
    return pd.DataFrame(rows)


def _crossref_to_df(crossref_rows: list[dict]) -> pd.DataFrame:
    if not crossref_rows:
        return pd.DataFrame()

    rename = {
        "report": "Report",
        "query_name": "Query",
        "connection_type": "Type",
        "origin": "Origin",
        "server_path": "Server Path",
        "path_found": "Found",
        "is_daily_dump": "Daily Dump",
        "latest_date": "Latest Date",
        "file_count": "File Count",
    }
    df = pd.DataFrame(crossref_rows)
    existing = {k: v for k, v in rename.items() if k in df.columns}
    return df.rename(columns=existing)


def main() -> None:
    st.title("pbix-mapper")
    st.caption("Extract and map data sources from Power BI (.pbix) files")

    st.sidebar.header("Upload")

    uploaded_files = st.sidebar.file_uploader(
        "PBIX files",
        type=["pbix"],
        accept_multiple_files=True,
        help="Upload one or more .pbix files to extract data sources.",
    )

    tree_file = st.sidebar.file_uploader(
        "Server tree (optional)",
        type=["txt"],
        help="Upload a file tree listing (one path per line) to cross-reference.",
    )

    real_only = st.sidebar.checkbox("Real sources only", value=True)

    if not uploaded_files:
        st.info("Upload one or more .pbix files to get started.")
        st.markdown("""
### How it works

1. Upload your `.pbix` files in the sidebar
2. pbix-mapper extracts all Power Query M expressions
3. Each data source is classified (SharePoint, Oracle, SQL Server, Excel, etc.)
4. Optionally cross-reference with a server file tree

### Supported connectors

SharePoint, Oracle, SQL Server, Folder, Excel, CSV, Web/API, OData, ODBC
        """)
        return

    reports: list[Report] = []
    with st.spinner("Extracting data sources..."):
        for uploaded in uploaded_files:
            with tempfile.NamedTemporaryFile(suffix=".pbix", delete=False) as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = Path(tmp.name)

            report = extract_report(tmp_path)
            report.name = uploaded.name.replace(".pbix", "")
            reports.append(report)
            tmp_path.unlink(missing_ok=True)

    total_sources = sum(len(r.sources) for r in reports)
    real_sources = sum(len(r.real_sources) for r in reports)

    col1, col2, col3 = st.columns(3)
    col1.metric("Reports", len(reports))
    col2.metric("Real Sources", real_sources)
    col3.metric("Total Queries", total_sources)

    tab_sources, tab_crossref, tab_export = st.tabs(["Sources", "Cross-Reference", "Export"])

    with tab_sources:
        df = _reports_to_df(reports, real_only=real_only)

        if not df.empty:
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                report_filter = st.multiselect(
                    "Filter by report",
                    options=df["Report"].unique().tolist(),
                    default=df["Report"].unique().tolist(),
                )
            with filter_col2:
                type_filter = st.multiselect(
                    "Filter by type",
                    options=df["Type"].unique().tolist(),
                    default=df["Type"].unique().tolist(),
                )

            filtered = df[
                df["Report"].isin(report_filter) & df["Type"].isin(type_filter)
            ]
            st.dataframe(filtered, use_container_width=True, hide_index=True)
        else:
            st.warning("No sources found.")

    with tab_crossref:
        if tree_file:
            tree_content = tree_file.getvalue().decode("utf-8", errors="replace")
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp:
                tmp.write(tree_content)
                tree_path = Path(tmp.name)

            tree_paths = parse_tree(tree_path)
            tree_path.unlink(missing_ok=True)

            crossref_rows = crossref_reports(reports, tree_paths)
            df_xref = _crossref_to_df(crossref_rows)

            if not df_xref.empty:
                found_count = df_xref["Found"].sum() if "Found" in df_xref.columns else 0
                not_found = len(df_xref) - found_count

                xc1, xc2 = st.columns(2)
                xc1.metric("Paths Found", int(found_count))
                xc2.metric("Not Found", int(not_found))

                st.dataframe(df_xref, use_container_width=True, hide_index=True)
            else:
                st.warning("No cross-reference results.")
        else:
            st.info("Upload a server tree file (.txt) in the sidebar to enable cross-referencing.")

    with tab_export:
        st.subheader("Export Data")

        df_export = _reports_to_df(reports, real_only=real_only)

        if not df_export.empty:
            csv_data = df_export.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name="pbix_sources.csv",
                mime="text/csv",
            )

            json_data = []
            for report in reports:
                sources = report.real_sources if real_only else report.sources
                json_data.append({
                    "report": report.name,
                    "parameters": report.parameters,
                    "sources": [s.to_dict() for s in sources],
                })
            json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
            st.download_button(
                "Download JSON",
                data=json_str.encode("utf-8"),
                file_name="pbix_sources.json",
                mime="application/json",
            )


if __name__ == "__main__":
    main()


# "A informacao quer ser livre." — Stewart Brand
