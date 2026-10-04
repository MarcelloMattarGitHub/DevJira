# RelatorioJira

App macOS (Jira.app) em Python/PySide6 que lista as pessoas com acesso ao Jira e mostra as horas
trabalhadas (worklogs) por dia, semana, mês ou ano.

## Executar
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```
Na primeira abertura, use "Configurar conexão…" e informe URL, e-mail e API token
(https://id.atlassian.com/manage-profile/security/api-tokens). As credenciais ficam em
`~/Library/Application Support/Jira/config.json`, fora do repositório.

## Gerar o Jira.app
```bash
./build_app.sh   # resultado em dist/Jira.app
```

## Documentação
`docs/Jira_App_Documentacao.pdf`, gerado pela skill `skills/padrao-ismartblue-documento`
(copiar a pasta para `~/.claude/skills/` ou enviar o `.zip` ao claude.ai).
