"""Data models for pbix-mapper."""

from dataclasses import dataclass, field


@dataclass
class Source:
    """A single data source extracted from a Power BI report."""

    query_name: str
    connection_type: str
    origin: str
    table_or_query: str
    is_real_source: bool
    subfolder: str = ""
    file_format: str = "N/A"

    def to_dict(self) -> dict:
        return {
            "query_name": self.query_name,
            "connection_type": self.connection_type,
            "origin": self.origin,
            "table_or_query": self.table_or_query,
            "is_real_source": self.is_real_source,
            "subfolder": self.subfolder,
            "file_format": self.file_format,
        }


@dataclass
class Report:
    """A Power BI report with its extracted data sources."""

    name: str
    path: str
    sources: list[Source] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)

    @property
    def real_sources(self) -> list[Source]:
        return [s for s in self.sources if s.is_real_source]

    @property
    def derived_sources(self) -> list[Source]:
        return [s for s in self.sources if not s.is_real_source]

    def to_flat_dicts(self) -> list[dict]:
        """Flatten report + sources into list of dicts (one per source)."""
        rows = []
        for src in self.sources:
            row = {"report": self.name, "report_path": self.path}
            row.update(src.to_dict())
            rows.append(row)
        return rows


# "A perfeicao e alcancada nao quando nao ha mais nada a acrescentar, mas quando nao ha mais nada a retirar." — Antoine de Saint-Exupery
