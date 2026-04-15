"""Tests for cross-reference module."""

import pytest

from pbix_mapper.cross_ref import (
    _extract_search_names,
    _normalize_folder,
    detect_dump_pattern,
    find_in_tree,
    find_local_path_in_tree,
    parse_tree,
)


SAMPLE_TREE = [
    "Z:\\CALENDARIO",
    "Z:\\COBRANCA",
    "Z:\\DE_PARA",
    "Z:\\VENDAS",
    "Z:\\CALENDARIO\\CALENDARIO.xlsx",
    "Z:\\COBRANCA\\COB_DUMPS_AG_VIRTUAL",
    "Z:\\COBRANCA\\COB_DUMPS_AG_VIRTUAL\\012026",
    "Z:\\COBRANCA\\COB_DUMPS_AG_VIRTUAL\\012026\\Dump_20260101_2200.txt",
    "Z:\\COBRANCA\\COB_DUMPS_AG_VIRTUAL\\012026\\Dump_20260102_2200.txt",
    "Z:\\COBRANCA\\COB_DUMPS_AG_VIRTUAL\\012026\\Dump_20260103_2200.txt",
    "Z:\\COBRANCA\\COB_DUMPS_AG_VIRTUAL\\012026\\Dump_20260104_2200.txt",
    "Z:\\DE_PARA\\DE_PARA.xlsx",
    "Z:\\VENDAS\\OLOS",
    "Z:\\VENDAS\\OLOS\\Dump_TabAuto_20260101_2300.txt",
    "Z:\\VENDAS\\OLOS\\Dump_TabAuto_20260102_2300.txt",
    "Z:\\VENDAS\\OLOS\\Dump_TabAuto_20260103_2300.txt",
]


class TestNormalizeFolder:
    def test_basic(self):
        assert _normalize_folder("COB_DUMPS_AG_VIRTUAL") == "cob_dumps_ag_virtual"

    def test_strips_slashes(self):
        assert _normalize_folder("/VENDAS/OLOS/") == "vendas/olos"


class TestExtractSearchNames:
    def test_single_folder(self):
        assert _extract_search_names("/COB_DUMPS_AG_VIRTUAL/") == ["COB_DUMPS_AG_VIRTUAL"]

    def test_nested(self):
        result = _extract_search_names("/VENDAS/OLOS/")
        assert "OLOS" in result
        assert "VENDAS/OLOS" in result

    def test_empty(self):
        assert _extract_search_names("") == []


class TestFindInTree:
    def test_find_direct_folder(self):
        result = find_in_tree("/CALENDARIO/", SAMPLE_TREE)
        assert result["found"]
        assert "CALENDARIO" in result["tree_path"]

    def test_find_nested_folder(self):
        result = find_in_tree("/COB_DUMPS_AG_VIRTUAL/", SAMPLE_TREE)
        assert result["found"]
        assert "COB_DUMPS_AG_VIRTUAL" in result["tree_path"]
        assert result["file_count"] == 4

    def test_find_with_parent(self):
        result = find_in_tree("/VENDAS/OLOS/", SAMPLE_TREE)
        assert result["found"]
        assert "OLOS" in result["tree_path"]

    def test_not_found(self):
        result = find_in_tree("/NONEXISTENT/", SAMPLE_TREE)
        assert not result["found"]

    def test_dump_detection(self):
        result = find_in_tree("/COB_DUMPS_AG_VIRTUAL/", SAMPLE_TREE)
        assert result["is_daily_dump"]
        assert result["latest_date"] == "20260104"


class TestFindLocalPath:
    def test_find_by_filename(self):
        result = find_local_path_in_tree("C:\\Users\\dev\\CALENDARIO.xlsx", SAMPLE_TREE)
        assert result["found"]
        assert "CALENDARIO.xlsx" in result["tree_path"]

    def test_not_found(self):
        result = find_local_path_in_tree("C:\\Users\\dev\\missing.xlsx", SAMPLE_TREE)
        assert not result["found"]


class TestDetectDumpPattern:
    def test_daily_pattern(self):
        files = [
            "Z:\\data\\Dump_20260101_2200.txt",
            "Z:\\data\\Dump_20260102_2200.txt",
            "Z:\\data\\Dump_20260103_2200.txt",
        ]
        result = detect_dump_pattern(files)
        assert result["is_daily"]
        assert result["latest_date"] == "20260103"

    def test_not_enough_files(self):
        files = ["Z:\\data\\file_20260101.txt"]
        result = detect_dump_pattern(files)
        assert not result["is_daily"]

    def test_no_dates(self):
        files = ["Z:\\data\\readme.txt", "Z:\\data\\config.ini"]
        result = detect_dump_pattern(files)
        assert not result["is_daily"]


# "Quem nao mede, nao gerencia." — Peter Drucker
