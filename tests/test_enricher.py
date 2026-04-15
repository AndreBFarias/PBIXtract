"""Tests for enrichment module."""

import pytest

from pbix_mapper.enricher import fuzzy_match, normalize_text


class TestNormalizeText:
    def test_basic(self):
        assert normalize_text("DUMP_AGENTE_VIRTUAL") == "dump agente virtual"

    def test_accents(self):
        assert normalize_text("Arrecadação TOI") == "arrecadacao toi"

    def test_extensions(self):
        assert normalize_text("Meta_SDR.xlsx") == "meta sdr"

    def test_mixed_separators(self):
        assert normalize_text("LISTA-COBRANCA-D") == "lista cobranca d"

    def test_empty(self):
        assert normalize_text("") == ""

    def test_non_string(self):
        assert normalize_text(None) == ""


class TestFuzzyMatch:
    def test_exact_match(self):
        assert fuzzy_match("VENDAS", ["VENDAS", "COBRANCA"]) == "VENDAS"

    def test_case_insensitive(self):
        assert fuzzy_match("vendas", ["VENDAS", "COBRANCA"]) == "VENDAS"

    def test_containment(self):
        assert fuzzy_match("DUMPS_AG_VIRTUAL", ["DUMP AGENTE VIRTUAL ENERGISA", "OUTRO"]) is None

    def test_no_match(self):
        assert fuzzy_match("XPTO", ["VENDAS", "COBRANCA"]) is None

    def test_high_similarity(self):
        result = fuzzy_match("PAGAMENTOS", ["PAGAMENTO", "VENDAS"])
        assert result == "PAGAMENTO"

    def test_threshold_respected(self):
        result = fuzzy_match("ABC", ["XYZ", "QRS"], threshold=0.9)
        assert result is None

    def test_empty_needle(self):
        assert fuzzy_match("", ["A", "B"]) is None


# "A duvida e o inicio da sabedoria." — Aristoteles
