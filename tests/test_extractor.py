"""Tests for the extraction engine."""

import pytest

from pbix_mapper.extractor import (
    _classify_query,
    _detect_file_format,
    _extract_local_path,
    _extract_parameter_value,
    _extract_sharepoint_subfolder,
)
from pbix_mapper.models import Source


class TestExtractParameterValue:
    def test_simple_url(self):
        expr = '"https://example.sharepoint.com/" meta [IsParameterQuery=true]'
        assert _extract_parameter_value(expr) == "https://example.sharepoint.com/"

    def test_subfolder(self):
        expr = '"/VENDAS/OLOS/" meta [IsParameterQuery=true, Type="Text"]'
        assert _extract_parameter_value(expr) == "/VENDAS/OLOS/"

    def test_function_not_parameter(self):
        expr = 'let\n    Fonte = (Param) => Excel.Workbook(Param)'
        assert _extract_parameter_value(expr) is None

    def test_empty(self):
        assert _extract_parameter_value("") is None


class TestExtractSharepointSubfolder:
    def test_param_reference(self):
        expr = 'Text.Contains([Folder Path], Path_SubPasta_OLOS)'
        param_map = {"Path_SubPasta_OLOS": "/VENDAS/OLOS/"}
        assert _extract_sharepoint_subfolder(expr, param_map) == "/VENDAS/OLOS/"

    def test_hardcoded_string(self):
        expr = 'Text.Contains([Folder Path], "/DATA/REPORTS/")'
        assert _extract_sharepoint_subfolder(expr, {}) == "/DATA/REPORTS/"

    def test_no_subfolder(self):
        expr = 'SharePoint.Files(Path_Primario, [ApiVersion = 15])'
        assert _extract_sharepoint_subfolder(expr, {}) is None


class TestExtractLocalPath:
    def test_file_contents(self):
        expr = 'Excel.Workbook(File.Contents("C:\\Users\\dev\\file.xlsx"))'
        assert _extract_local_path(expr) == "C:\\Users\\dev\\file.xlsx"

    def test_folder_files(self):
        expr = 'Folder.Files("\\\\server\\share\\data\\")'
        assert _extract_local_path(expr) == "\\\\server\\share\\data\\"

    def test_no_path(self):
        assert _extract_local_path("Table.FromRows(...)") is None


class TestDetectFileFormat:
    def test_csv(self):
        assert _detect_file_format("Csv.Document(content)") == "CSV"

    def test_xlsx(self):
        expr = 'Text.Lower([Extension]) = ".xlsx"'
        assert _detect_file_format(expr) == "Excel (.xlsx)"

    def test_excel_workbook(self):
        assert _detect_file_format("Excel.Workbook(binary)") == "Excel"

    def test_unknown(self):
        assert _detect_file_format("some random code") == "N/A"


class TestClassifyQuery:
    def test_embedded_table(self):
        expr = 'Table.FromRows(Json.Document(Binary.Decompress(...)))'
        src = _classify_query("_medida", expr, {}, None)
        assert not src.is_real_source
        assert src.connection_type == "Embedded/Computed"

    def test_datetime_zone(self):
        expr = "DateTimeZone.SwitchZone(DateTimeZone.LocalNow(), -3)"
        src = _classify_query("DataAtualizacao", expr, {}, None)
        assert not src.is_real_source

    def test_sharepoint_source(self):
        expr = (
            'SharePoint.Files(Path_Primario, [ApiVersion = 15]),'
            'Text.Contains([Folder Path], Path_SubPasta_VENDAS)'
        )
        params = {
            "Path_Primario": "https://sp.example.com/",
            "Path_SubPasta_VENDAS": "/VENDAS/",
        }
        src = _classify_query("fato_vendas", expr, params, "https://sp.example.com/")
        assert src.is_real_source
        assert src.connection_type == "SharePoint"
        assert src.origin == "https://sp.example.com//VENDAS/"
        assert src.subfolder == "/VENDAS/"

    def test_oracle_source(self):
        expr = 'Oracle.Database("dbserver:1521/PROD", [Schema="SALES"])'
        src = _classify_query("dim_client", expr, {}, None)
        assert src.is_real_source
        assert src.connection_type == "Oracle"
        assert src.origin == "dbserver:1521/PROD"

    def test_sql_server_source(self):
        expr = 'Sql.Database("sqlserver.corp", "DW_PROD")'
        src = _classify_query("fato_vendas", expr, {}, None)
        assert src.is_real_source
        assert src.connection_type == "SQL Server"
        assert src.origin == "sqlserver.corp"
        assert src.table_or_query == "Database: DW_PROD"

    def test_local_excel(self):
        expr = 'Excel.Workbook(File.Contents("C:\\data\\report.xlsx"), null, true)'
        src = _classify_query("dados", expr, {}, None)
        assert src.is_real_source
        assert src.connection_type == "Excel (local)"
        assert src.origin == "C:\\data\\report.xlsx"

    def test_folder_source(self):
        expr = 'Folder.Files("\\\\fs-bi\\share\\dumps\\")'
        src = _classify_query("dumps", expr, {}, None)
        assert src.is_real_source
        assert src.connection_type == "Folder"

    def test_web_api(self):
        expr = 'Web.Contents("https://api.example.com/v1/data")'
        src = _classify_query("api_data", expr, {}, None)
        assert src.is_real_source
        assert src.connection_type == "API/Web"
        assert src.origin == "https://api.example.com/v1/data"

    def test_derived_query(self):
        expr = "let\n    Source = other_query,\n    filtered = Table.SelectRows(Source)"
        src = _classify_query("filtered_data", expr, {}, None)
        assert not src.is_real_source
        assert src.connection_type == "Derived/Transform"


# "Teste cedo, teste sempre." — Kent Beck
