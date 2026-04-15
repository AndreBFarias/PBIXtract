# pbix-mapper

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0-150458?style=flat-square&logo=pandas&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Interface_Web-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/Licenca-GPL--3.0-blue?style=flat-square)

Ferramenta CLI + interface web para **extrair e mapear todas as fontes de dados de arquivos Power BI (.pbix)**. Joga um PBIX, sai o de-para estruturado de cada conexao, tabela e parametro.

Projeto real de engenharia de dados aplicada ao ciclo de **migracao de relatorios Power BI**: **extracao de fontes -> cruzamento com servidor -> enriquecimento -> comunicacao**.

---

## Quick Start

```bash
git clone https://github.com/andrefarias/pbix-mapper.git
cd pbix-mapper
pip install -e .

# Extrair fontes de um PBIX
pbix-mapper extract relatorio.pbix

# Extrair de um diretorio inteiro, salvar em CSV
pbix-mapper extract ./relatorios/ --format csv --real-only -o fontes.csv

# Abrir interface web
pip install -e ".[web]"
pbix-mapper web
```

---

## CLI -- 6 Comandos

```
pbix-mapper extract    Extrair fontes de dados de arquivos .pbix
pbix-mapper crossref   Cruzar fontes com tree de servidor de arquivos
pbix-mapper enrich     Enriquecer com metadados de planilha Excel
pbix-mapper messages   Gerar mensagens Teams/email via template YAML
pbix-mapper web        Abrir interface web local (Streamlit)
pbix-mapper version    Versao
```

### Pipeline tipico

```
pbix-mapper extract ./relatorios/ -f csv --real-only -o fontes.csv
pbix-mapper crossref fontes.csv --tree server_tree.txt -o cruzado.csv
pbix-mapper enrich cruzado.csv -e planilha.xlsx -m "Dashboard" -s "Fonte" -o final.csv
pbix-mapper messages final.csv --config grupos.yaml -o mensagens.md
```

---

## Interface Web

```
+------------------------------------------------------------------+
| pbix-mapper                                                       |
+------------------------------------------------------------------+
| [SIDEBAR]              | [SOURCES]  [CROSS-REF]  [EXPORT]        |
|                        |                                          |
| Upload PBIX            | +------+--------+--------+--------+     |
| [arquivo.pbix]    [x]  | |Report|Query   |Type    |Origin  |     |
| [vendas.pbix]     [x]  | |------|--------|--------|--------|     |
|                        | |Vendas|D_PARA  |SharePt.|https://|     |
| Server Tree (opcional) | |Vendas|Metas   |SharePt.|https://|     |
| [tree.txt]        [x]  | |Funil |FactCon.|Excel   |C:\Us...|     |
|                        | +------+--------+--------+--------+     |
| [x] Real sources only  |                                          |
|                        | +--------+ +--------+ +--------+        |
|                        | |Reports | |Real    | |Total   |        |
|                        | |   4    | |  30    | |  42    |        |
|                        | +--------+ +--------+ +--------+        |
+------------------------------------------------------------------+
```

- Upload de PBIX (multiplos arquivos)
- Tabela interativa com filtros por relatorio e tipo de conexao
- Cross-reference com tree de servidor (upload opcional)
- Export: CSV e JSON

---

## Destaques Tecnicos

O que este projeto demonstra:

- **Extracao de PBIX** -- abre o binario DataModel (ABF/XPress9) via pbixray, extrai codigo Power Query M e classifica cada conector
- **10 tipos de conexao** -- SharePoint, Oracle, SQL Server, Folder, Excel, CSV, Web/API, OData, ODBC, File local
- **Resolucao de parametros** -- parametros Path_* sao resolvidos para seus valores reais, reconstruindo a origem completa
- **Cruzamento com servidor** -- valida se os caminhos extraidos existem no file system corporativo, detecta padrao de dump diario
- **Fuzzy matching** -- enriquecimento com planilhas Excel usando correspondencia aproximada (difflib.SequenceMatcher)
- **Gerador de mensagens** -- templates Jinja2 configuraveis via YAML para comunicacao Teams/email com tabelas de de-para
- **Interface web** -- Streamlit com upload, filtros interativos e export
- **CLI composavel** -- cada comando aceita entrada do anterior via CSV, permitindo pipelines flexiveis
- **51 testes unitarios** -- cobertura das funcoes de parsing, classificacao, cruzamento e matching
- **Zero dependencia de GUI** -- funciona 100% no terminal, interface web e opcional

---

## Tecnologias

| Camada | Stack |
|--------|-------|
| Extracao | Python, pbixray (decompressao XPress9) |
| Parsing | Regex sobre codigo Power Query M |
| Cruzamento | Busca em file tree com deteccao de dump diario |
| Enriquecimento | Pandas, difflib (fuzzy matching) |
| Mensagens | Jinja2, PyYAML |
| Interface Web | Streamlit |
| CLI | Typer, Rich (tabelas formatadas) |
| Testes | pytest |

---

## Arquitetura

```
              Arquivo .pbix (ZIP -> DataModel -> ABF/XPress9)
                        |
                  [pbixray.PBIXRay]
                  decompressao + extracao de M code
                        |
                  [extractor.py]
                  regex parsing dos conectores
                  resolucao de parametros Path_*
                  classificacao: real vs embutido
                        |
          +-------------+-------------+
          |             |             |
    [formatters.py] [cross_ref.py] [enricher.py]
    CSV / JSON /    cruzamento     fuzzy match
    tabela Rich     com tree.txt   com Excel
          |             |             |
          +-------> CSV enriquecido --+
                        |
              +---------+---------+
              |                   |
        [Streamlit]         [messenger.py]
        interface web       Jinja2 + YAML
        upload + filtros    mensagens Teams
```

---

## Conectores Suportados

| Padrao no Power Query M | Tipo |
|-------------------------|------|
| `SharePoint.Files(url)` | SharePoint |
| `Oracle.Database(server)` | Oracle |
| `Sql.Database(server, db)` | SQL Server |
| `Folder.Files(path)` | Pasta de rede |
| `Excel.Workbook(File.Contents(path))` | Excel local |
| `Csv.Document(File.Contents(path))` | CSV local |
| `File.Contents(path)` | Arquivo local |
| `Web.Contents(url)` | API / Web |
| `OData.Feed(url)` | OData |
| `Odbc.Query(dsn, query)` | ODBC |

---

## Estrutura do Projeto

```
pbix-mapper/
  src/
    pbix_mapper/
      __init__.py            # Versao
      cli.py                 # 6 comandos Typer
      extractor.py           # Core: parsing de Power Query M
      models.py              # Dataclasses Source e Report
      formatters.py          # Saida CSV, JSON, tabela Rich
      cross_ref.py           # Cruzamento com file tree
      enricher.py            # Fuzzy matching com Excel
      messenger.py           # Gerador de mensagens Jinja2
      templates/
        message.md.j2        # Template de mensagem
        example_config.yaml  # Config YAML de exemplo
      web/
        app.py               # Interface Streamlit
  tests/
    test_extractor.py        # 23 testes do parser
    test_cross_ref.py        # 15 testes do cruzamento
    test_enricher.py         # 13 testes do matching
  docs/
    README.md
  pyproject.toml
  LICENSE                    # GPL-3.0
```

---

## Licenca

GPL-3.0-or-later

---

*"O mapa nao e o territorio, mas sem mapa voce esta perdido."*
