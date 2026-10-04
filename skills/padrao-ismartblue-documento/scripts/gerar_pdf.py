#!/usr/bin/env python3
"""Gera o PDF padrão iSmartBlue a partir de um JSON.

Uso:  python gerar_pdf.py spec.json saida.pdf
Dependência:  pip install reportlab

Formato do JSON:
{
  "programa": "Nome do programa",
  "complemento": "opcional, 2ª linha da capa",
  "subtitulo": "opcional",
  "autor": "opcional", "data": "opcional (padrão: hoje)",
  "itens": [
    {"nome": "Objeto", "descricao": "texto", "filhos": [
        {"nome": "Filho", "descricao": "texto", "bullets": ["a", "b"]}
    ], "bullets": ["opcional"]}
  ]
}
"""
import json
import sys
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, ListFlowable,
                                ListItem, PageBreak, PageTemplate, Paragraph, Spacer)
from reportlab.platypus.tableofcontents import TableOfContents
from xml.sax.saxutils import escape

LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo-ismartblue.png"
AZUL_ESCURO = colors.HexColor("#1F3F7F")   # cor do texto "iSmart" no logo
AZUL = colors.HexColor("#3D9BE9")          # azul do ícone
CINZA = colors.HexColor("#555555")
MARGEM = 2.2 * cm

S = {
    "capa_titulo": ParagraphStyle("capa_titulo", fontName="Helvetica-Bold", fontSize=26, leading=30,
                                  textColor=AZUL_ESCURO, alignment=TA_CENTER),
    "capa_compl": ParagraphStyle("capa_compl", fontName="Helvetica", fontSize=17, leading=22,
                                 spaceBefore=4, textColor=AZUL, alignment=TA_CENTER),
    "capa_sub": ParagraphStyle("capa_sub", fontName="Helvetica", fontSize=12, leading=16, textColor=CINZA),
    "capa_sub_c": ParagraphStyle("capa_sub_c", fontName="Helvetica", fontSize=12, leading=16,
                                 spaceBefore=10, textColor=CINZA, alignment=TA_CENTER),
    "capa_h": ParagraphStyle("capa_h", fontName="Helvetica-Bold", fontSize=13, leading=16,
                             textColor=AZUL, spaceBefore=26, spaceAfter=8),
    "capa_item": ParagraphStyle("capa_item", fontName="Helvetica", fontSize=12, leading=17),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24,
                         textColor=AZUL_ESCURO, spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, leading=18,
                         textColor=AZUL, spaceBefore=14, spaceAfter=4),
    "corpo": ParagraphStyle("corpo", fontName="Helvetica", fontSize=10.5, leading=15),
    "indice_t": ParagraphStyle("indice_t", fontName="Helvetica-Bold", fontSize=22, leading=26,
                               textColor=AZUL_ESCURO, spaceAfter=14),
    "toc0": ParagraphStyle("toc0", fontName="Helvetica-Bold", fontSize=11.5, leading=20,
                           textColor=AZUL_ESCURO),
    "toc1": ParagraphStyle("toc1", fontName="Helvetica", fontSize=10.5, leading=16,
                           leftIndent=18, textColor=colors.black),
}


def logo_flowable(largura=5.2 * cm) -> Image:
    from reportlab.lib.utils import ImageReader
    w, h = ImageReader(str(LOGO)).getSize()
    img = Image(str(LOGO), width=largura, height=largura * h / w)
    img.hAlign = "LEFT"
    return img


class Ancora(Flowable):
    """Flowable invisível que cria o destino do link e a entrada do índice/bookmark."""
    def __init__(self, texto, nivel, chave):
        super().__init__()
        self.texto, self.nivel, self.chave = texto, nivel, chave
        self.width = self.height = 0

    def draw(self):
        c = self.canv
        c.bookmarkPage(self.chave)
        c.addOutlineEntry(self.texto, self.chave, level=self.nivel, closed=False)


class Doc(BaseDocTemplate):
    def __init__(self, destino, programa, autor):
        super().__init__(destino, pagesize=A4, leftMargin=MARGEM, rightMargin=MARGEM,
                         topMargin=MARGEM, bottomMargin=2 * cm,
                         title=programa, author=autor or "iSmartBlue")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=self._rodape)])

    def _rodape(self, canv, doc):
        canv.saveState()
        canv.setFont("Helvetica", 8.5)
        canv.setFillColor(CINZA)
        canv.drawString(MARGEM, 1.1 * cm, "iSmartBlue")
        canv.drawRightString(A4[0] - MARGEM, 1.1 * cm, str(doc.page))
        canv.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Ancora):
            self.notify("TOCEntry", (fl.nivel, fl.texto, self.page, fl.chave))


def _bullets(itens):
    if not itens:
        return []
    return [ListFlowable([ListItem(Paragraph(escape(b), S["corpo"])) for b in itens],
                         bulletType="bullet", start="•", leftIndent=14)]


def montar(spec: dict, destino: str):
    programa = spec["programa"]
    itens = spec.get("itens", [])
    doc = Doc(destino, programa, spec.get("autor"))
    story = []

    # Página 1 — capa: logo no canto superior esquerdo, nome no meio, itens abaixo
    story += [logo_flowable(), Spacer(1, 5.5 * cm), Paragraph(escape(programa), S["capa_titulo"])]
    if spec.get("complemento"):  # 2ª linha, menor, abaixo do nome (ex.: "Relatório de Horas")
        story.append(Paragraph(escape(spec["complemento"]), S["capa_compl"]))
    if spec.get("subtitulo"):
        story.append(Paragraph(escape(spec["subtitulo"]), S["capa_sub_c"]))
    story.append(Paragraph("Itens construídos", S["capa_h"]))
    for n, it in enumerate(itens, 1):
        story.append(Paragraph(f"{n}.&nbsp;&nbsp;{escape(it['nome'])}", S["capa_item"]))
    data = spec.get("data") or date.today().strftime("%d/%m/%Y")
    rodape_capa = "  ·  ".join(x for x in (spec.get("autor"), data) if x)
    story += [Spacer(1, 1 * cm), Paragraph(escape(rodape_capa), S["capa_sub"]), PageBreak()]

    # Página 2 — índice clicável (objetos e filhos)
    toc = TableOfContents()
    toc.dotsMinLevel = 0
    toc.levelStyles = [S["toc0"], S["toc1"]]
    story += [logo_flowable(3.6 * cm), Spacer(1, 0.6 * cm), Paragraph("Índice", S["indice_t"]), toc, PageBreak()]

    # Conteúdo — um objeto por página
    for i, it in enumerate(itens):
        titulo = f"{i + 1}. {it['nome']}"
        story += [logo_flowable(3.6 * cm), Spacer(1, 0.5 * cm),
                  Ancora(titulo, 0, f"o{i}"), Paragraph(escape(titulo), S["h1"])]
        if it.get("descricao"):
            story.append(Paragraph(escape(it["descricao"]), S["corpo"]))
        story += _bullets(it.get("bullets"))
        for j, f in enumerate(it.get("filhos", [])):
            sub = f"{i + 1}.{j + 1} {f['nome']}"
            story += [Ancora(sub, 1, f"o{i}f{j}"), Paragraph(escape(sub), S["h2"])]
            if f.get("descricao"):
                story.append(Paragraph(escape(f["descricao"]), S["corpo"]))
            story += _bullets(f.get("bullets"))
        if i < len(itens) - 1:
            story.append(PageBreak())

    doc.multiBuild(story)  # 2 passadas: resolve os números de página do índice


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    montar(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2])
    print("PDF gerado:", sys.argv[2])
