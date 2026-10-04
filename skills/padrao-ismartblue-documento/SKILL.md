---
name: padrao-ismartblue-documento
description: Gera documentos PDF no padrão visual da iSmartBlue (logo no canto superior esquerdo, capa com nome do programa e itens construídos, índice clicável na página 2, um objeto por página com seus objetos filhos). Use sempre que o usuário pedir documentação, manual, relatório ou "documento do programa/projeto/app" no padrão iSmartBlue, ou citar "padrao-ismartblue-documento".
---

# Padrão iSmartBlue — Documento PDF

Gera sempre **PDF** com este layout:

1. **Página 1 (capa):** logo iSmartBlue (fundo transparente/branco) no canto superior esquerdo, acima de qualquer título; **nome do programa** (centralizado, fonte média) no meio da página, com o `complemento` numa linha menor logo abaixo; abaixo, a lista de **todos os itens construídos**.
2. **Página 2 (índice):** objetos e seus objetos filhos, com número de página. Pais e filhos são **numerados** (1, 1.1, 1.2, 2, …) na capa, no índice e nos títulos. Cada linha é um **link clicável** que abre na página indicada (também gera os marcadores/bookmarks do leitor de PDF).
3. **Páginas seguintes:** um objeto por página (logo no topo, título, descrição, filhos como subtítulos).

## Como usar

1. Levante o conteúdo do programa/projeto (leia o código e a conversa) e monte um JSON:

```json
{
  "programa": "Nome do programa",
  "complemento": "opcional — 2ª linha da capa, abaixo do nome (ex.: Relatório de Horas)",
  "subtitulo": "opcional",
  "autor": "opcional",
  "data": "opcional, dd/mm/aaaa (padrão: hoje)",
  "itens": [
    {"nome": "Objeto", "descricao": "texto", "bullets": ["opcional"],
     "filhos": [{"nome": "Objeto filho", "descricao": "texto", "bullets": ["opcional"]}]}
  ]
}
```

   `itens` = tudo o que foi construído (aparece na capa e é o nível 1 do índice); `filhos` = nível 2 do índice. Escreva em português, com descrições objetivas e fiéis ao código.

2. Instale a dependência (uma vez) e gere:

```bash
python3 -m pip install reportlab      # se necessário (use um venv se o pip reclamar)
python3 <pasta-da-skill>/scripts/gerar_pdf.py spec.json saida.pdf
```

   `<pasta-da-skill>` é a pasta onde esta skill está instalada (ex.: `~/.claude/skills/padrao-ismartblue-documento`).

3. Confira: o PDF deve ter o índice na página 2 com links funcionando. Entregue o caminho do PDF ao usuário.

## Regras
- Formato de saída: somente PDF.
- Não altere o logo (`assets/logo-ismartblue.png`, fundo transparente); ele vai sempre no canto superior esquerdo, acima dos títulos.
- Cores da marca: azul escuro `#1F3F7F` (títulos) e azul `#3D9BE9` (subtítulos).
