# Changelog

## [0.2.0] - 2026-04-16

### Mudado
- Projeto renomeado de `pbix-mapper` para `PBIXtract` (sprint S16 do portfólio)
- `README.md` movido de `docs/` para raiz (padrão do portfólio)

### Adicionado
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`
- `.mailmap` para unificação de identidade
- `.github/workflows/ci.yml` (pytest + ruff)

## [0.1.0] - 2026-04-14

### Adicionado
- CLI com 6 comandos (extract, crossref, enrich, messages, web, version)
- Extração de fontes via pbixray (DataModel ABF/XPress9)
- 10 tipos de conector Power Query M
- Resolução de parâmetros Path_*
- Cruzamento com tree de servidor
- Fuzzy matching com Excel via difflib
- Gerador de mensagens Jinja2 + YAML
- Interface web Streamlit
- 51 testes unitários
