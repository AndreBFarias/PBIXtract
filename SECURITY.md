# Política de Segurança -- PBIXtract

## Versões Suportadas

| Versão | Suportada |
| ------ | --------- |
| 0.1.x  | sim       |

## Reportando

1. **Não** abra issue pública
2. Envie email ao mantenedor
3. Inclua: descrição, passos, impacto

## Tempo de Resposta

- Recebimento: 48h
- Avaliação: 7 dias
- Correção: 30 dias

## Dados Sensíveis

PBIXtract extrai informações de arquivos Power BI que podem conter:

- Credenciais em conectores (senhas hardcoded, tokens)
- Caminhos de servidores internos
- Nomes de databases corporativos

Nunca commite `.pbix` de produção no repositório. Use apenas fixtures anonimizadas em `tests/`.

## Escopo

- `src/pbix_mapper/`
- CI/CD
- Dependências diretas

## Fora do Escopo

- Vulnerabilidades em `pbixray`, `pandas`, `streamlit` (reporte upstream)
- Bugs no próprio Power BI Desktop
