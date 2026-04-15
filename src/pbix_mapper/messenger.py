"""Generate communication messages from extracted sources + YAML config."""

import logging
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_config(config_path: Path) -> dict:
    """Load YAML configuration for message generation."""
    content = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(content)
    logger.info("Config loaded: %d groups", len(config.get("groups", [])))
    return config


def match_sources_to_groups(
    config: dict,
    source_rows: list[dict],
    report_key: str = "report",
) -> dict:
    """Attach matching source rows to each group in the config.

    Each group has a 'report' field that is matched against the report_key
    in source_rows (case-insensitive containment).
    """
    for group in config.get("groups", []):
        group_report = group.get("report", "").lower()
        matched = []
        for row in source_rows:
            row_report = str(row.get(report_key, "")).lower()
            if group_report and (group_report in row_report or row_report in group_report):
                matched.append(row)
        group["sources"] = matched
        logger.info(
            "  Group '%s': %d sources matched",
            group.get("name", "?"),
            len(matched),
        )

    return config


def render_messages(
    config: dict,
    template_name: str = "message.md.j2",
    template_dir: Path | None = None,
) -> str:
    """Render messages using Jinja2 template + config."""
    tpl_dir = template_dir or TEMPLATES_DIR
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)

    rendered = template.render(
        groups=config.get("groups", []),
        greeting=config.get("greeting", "Hi,"),
        intro_template=config.get("intro_template", "Data source mapping for **{report}**:"),
        questions=config.get("questions", []),
        closing=config.get("closing", "Thanks."),
    )

    return rendered


def generate_messages(
    config_path: Path,
    source_rows: list[dict],
    output_path: Path | None = None,
    template_dir: Path | None = None,
) -> str:
    """Full pipeline: load config, match sources, render, optionally save."""
    config = load_config(config_path)
    config = match_sources_to_groups(config, source_rows)
    rendered = render_messages(config, template_dir=template_dir)

    if output_path:
        output_path.write_text(rendered, encoding="utf-8")
        logger.info("Messages written: %s", output_path)

    return rendered


# "A palavra e metade de quem a pronuncia, metade de quem a ouve." — Michel de Montaigne
