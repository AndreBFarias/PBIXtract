# Guia de Contribuição -- PBIXtract

## Como Contribuir

1. Fork do repositório
2. Branch (`git checkout -b feature/minha-feature`)
3. Commits em PT-BR (Conventional Commits)
4. Pull Request

## Padrão de Commits

```
tipo: descricao imperativa em PT-BR
```

Tipos: `feat`, `fix`, `refactor`, `docs`, `test`, `perf`, `chore`, `style`, `ci`, `build`

### Regras

- Idioma: PT-BR com acentuação correta
- Zero emojis
- Zero menções a ferramentas de IA

## Padrão de Código

- Type hints sempre
- Docstrings nas funções públicas
- `logging` rotacionado
- Error handling explícito
- Limite de 800 linhas por arquivo

## Configuração

```bash
git clone https://github.com/AndreBFarias/PBIXtract.git
cd PBIXtract
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,web]"
```

## Testes

```bash
pytest tests/ -v --cov=pbix_mapper
```

## Processo de Review

1. Abra PR contra `main`
2. CI precisa estar verde
3. Revisão do mantenedor
4. Merge após aprovação
